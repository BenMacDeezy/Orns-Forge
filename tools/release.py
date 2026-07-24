"""Filtered public-mirror release builder. Stdlib only; shells out to `git`.

The private working repo (`BenMacDeezy/forge-staging`) keeps full `.forge/` project
state -- queue, specs, project memory. The public mirror ships only the
plugin: a filtered export of HEAD's tree, minus `.forge/`, `docs/audits/`,
and anything listed in `tools/release-denylist.txt`, pushed as a single
squashed commit tagged `v<version>` (version read from
`.claude-plugin/plugin.json`).

Fail-safe by construction:
  - Refuses to run against a dirty working tree (releases come from
    committed state, never uncommitted edits).
  - Never creates the public repo or touches git remotes itself -- if the
    `public` remote isn't configured, it prints exact one-time setup
    instructions and exits nonzero with zero side effects.
  - An explicit post-build leak scan re-walks the export tree and fails the
    release (no push) if any denylisted path made it through, independent
    of whatever filtered the export in the first place.
  - Refuses to overwrite an existing release: if `v<version>` already
    exists on the public remote, it exits nonzero without pushing.
  - `--dry-run` builds the export, runs the leak scan, and prints the file
    manifest -- everything the real run does except touch the network.

See docs/releasing.md for the full flow.
"""
import argparse
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC_REMOTE = "public"
RELEASE_BRANCH = "main"

NO_REMOTE_MESSAGE = """\
No public mirror remote is configured (or it isn't reachable).

One-time setup:
  1. Create a public GitHub repo for the mirror, e.g.
       https://github.com/<you>/forge-public
  2. Add it as a remote named 'public' in this checkout:
       git remote add public https://github.com/<you>/forge-public.git
  3. Re-run this script.

This script never creates repos or changes remotes itself -- do both by hand.
"""


class ReleaseError(Exception):
    """Raised for any fail-safe abort. main() prints the message and exits
    nonzero; every raise site here happens before (or instead of) a push, so
    raising this always means the release had zero side effects."""


def read_version(plugin_json_path):
    """Read the `version` field out of `.claude-plugin/plugin.json`."""
    plugin_json_path = pathlib.Path(plugin_json_path)
    try:
        data = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReleaseError(f"cannot read {plugin_json_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"{plugin_json_path} is not valid JSON: {exc}") from exc
    version = data.get("version")
    if not version or not isinstance(version, str):
        raise ReleaseError(f"{plugin_json_path} has no string 'version' field")
    return version


def load_denylist(denylist_path):
    """Parse `tools/release-denylist.txt`: one path prefix per line, `#`
    comments and blank lines ignored. Trailing slashes are stripped so
    entries compare uniformly against extracted paths."""
    denylist_path = pathlib.Path(denylist_path)
    entries = []
    for line in denylist_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line.rstrip("/"))
    return entries


def is_denied(relpath, denylist):
    """True iff relpath (POSIX-style, relative to export root) is exactly a
    denylisted prefix or falls under one. Boundary-safe: "docs/audits"
    denies "docs/audits/x" but not "docs/audits-old/x"."""
    relpath = relpath.strip("/")
    for entry in denylist:
        if relpath == entry or relpath.startswith(entry + "/"):
            return True
    return False


def _run_git(args, cwd, check=True):
    result = subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise ReleaseError(
            f"git {' '.join(args)} (in {cwd}) failed: {result.stderr.strip()}"
        )
    return result


def working_tree_is_dirty(repo_root):
    result = _run_git(["status", "--porcelain"], cwd=repo_root)
    return bool(result.stdout.strip())


def get_public_remote_url(repo_root):
    """Return the configured `public` remote's URL, or raise ReleaseError
    with one-time setup instructions if it isn't configured. Purely local
    (`git remote get-url` never touches the network)."""
    result = _run_git(["remote", "get-url", PUBLIC_REMOTE], cwd=repo_root, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise ReleaseError(NO_REMOTE_MESSAGE)
    return result.stdout.strip()


def remote_tag_exists(remote_url, tag, repo_root):
    """Network check: does `tag` already exist on the public remote? Any
    failure to reach the remote is treated the same as "not configured" --
    the release cannot proceed safely either way."""
    result = _run_git(
        ["ls-remote", "--tags", remote_url, f"refs/tags/{tag}"],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError(
            f"could not reach the public remote to check for tag {tag}: "
            f"{result.stderr.strip()}\n\n{NO_REMOTE_MESSAGE}"
        )
    return bool(result.stdout.strip())


def build_export(repo_root, dest_dir, denylist, ref="HEAD"):
    """Export `ref`'s committed tree (never the working tree) into dest_dir
    via `git archive`, dropping any entry `is_denied` against `denylist`.
    Returns the sorted list of POSIX-style relative file paths that made it
    into the export."""
    repo_root = pathlib.Path(repo_root)
    dest_dir = pathlib.Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        ["git", "archive", "--format=tar", ref],
        cwd=str(repo_root),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise ReleaseError(
            f"git archive {ref} failed: {proc.stderr.decode(errors='replace').strip()}"
        )

    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        members = [m for m in tar.getmembers() if not is_denied(m.name.rstrip("/"), denylist)]
        tar.extractall(path=dest_dir, members=members, filter="data")

    return sorted(
        p.relative_to(dest_dir).as_posix() for p in dest_dir.rglob("*") if p.is_file()
    )


def scan_for_leaks(export_dir, denylist):
    """Post-build leak scan: independently re-walk export_dir (whatever
    tree ended up on disk, regardless of how it got there) and report every
    path that matches the denylist. Empty list == clean. This is the last
    line of defense against a bug in build_export's own filtering, so it
    must not share that filtering's blind spots -- it just walks what's
    actually on disk."""
    export_dir = pathlib.Path(export_dir)
    leaks = []
    for p in export_dir.rglob("*"):
        rel = p.relative_to(export_dir).as_posix()
        if is_denied(rel, denylist):
            leaks.append(rel)
    return sorted(leaks)


def load_contributors(path):
    """Parse CONTRIBUTORS.md for `- Name <email>` lines. Returns a list of
    "Name <email>" strings for Co-authored-by trailers. Missing file or no
    matching lines -> empty list (releases never fail over credit lines)."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        m = re.match(r"^-\s+(\S[^<]*?)\s+<([^<>@\s]+@[^<>\s]+)>\s*$", line)
        if m:
            out.append(f"{m.group(1)} <{m.group(2)}>")
    return out


def commit_and_push(export_dir, remote_url, tag, contributors=()):
    """Turn export_dir into a fresh single-commit repo and force-push it to
    the public remote's release branch, then push the version tag. The
    public branch always holds exactly one commit per release -- history
    lives in the tags, not in accumulated commits, hence "squashed".
    Contributors are credited as Co-authored-by trailers so the public
    mirror's contributors graph reflects the people behind the project."""
    message = f"Release {tag}"
    if contributors:
        message += "\n\n" + "\n".join(
            f"Co-authored-by: {c}" for c in contributors
        )
    _run_git(["init", "-q"], cwd=export_dir)
    _run_git(["add", "-A"], cwd=export_dir)
    _run_git(
        [
            "-c", "user.email=release@forge.local",
            "-c", "user.name=Forge Release",
            "commit", "-q", "-m", message,
        ],
        cwd=export_dir,
    )
    _run_git(["tag", tag], cwd=export_dir)
    _run_git(["push", "--force", remote_url, f"HEAD:{RELEASE_BRANCH}"], cwd=export_dir)
    _run_git(["push", remote_url, tag], cwd=export_dir)


def run_release(repo_root, dry_run, out=sys.stdout):
    """Full release flow. Raises ReleaseError on any fail-safe abort --
    every abort path runs before commit_and_push, so nothing is ever
    partially pushed. dry_run builds the export and runs the leak scan
    (everything real releases do except touch the network) and prints the
    manifest instead of pushing; it does not require the public remote to
    be configured."""
    repo_root = pathlib.Path(repo_root)

    if working_tree_is_dirty(repo_root):
        raise ReleaseError(
            "Working tree is dirty. Releases are cut from committed state -- "
            "commit or stash your changes first."
        )

    version = read_version(repo_root / ".claude-plugin" / "plugin.json")
    tag = f"v{version}"
    denylist = load_denylist(repo_root / "tools" / "release-denylist.txt")

    with tempfile.TemporaryDirectory(prefix="forge-release-") as tmp:
        export_dir = pathlib.Path(tmp) / "export"
        manifest = build_export(repo_root, export_dir, denylist)

        leaks = scan_for_leaks(export_dir, denylist)
        if leaks:
            raise ReleaseError(
                "Leak scan failed -- denylisted paths present in export tree:\n  "
                + "\n  ".join(leaks)
                + "\nRelease aborted; nothing was pushed."
            )

        if dry_run:
            print(f"Dry run: release {tag} would export {len(manifest)} files:", file=out)
            for f in manifest:
                print(f"  {f}", file=out)
            return

        remote_url = get_public_remote_url(repo_root)
        if remote_tag_exists(remote_url, tag, repo_root):
            raise ReleaseError(
                f"Tag {tag} already exists on the public remote. Refusing to "
                "overwrite an existing release."
            )

        commit_and_push(
            export_dir,
            remote_url,
            tag,
            contributors=load_contributors(
                pathlib.Path(repo_root) / "CONTRIBUTORS.md"
            ),
        )
        print(f"Released {tag} to public mirror ({len(manifest)} files).", file=out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a filtered export of HEAD and push it to the public mirror as a squashed, tagged release."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build the export and print its manifest without pushing.",
    )
    parser.add_argument(
        "--repo-root", default=str(REPO_ROOT),
        help="Repo root to release from (default: this checkout).",
    )
    args = parser.parse_args(argv)

    try:
        run_release(pathlib.Path(args.repo_root).resolve(), dry_run=args.dry_run)
    except ReleaseError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
