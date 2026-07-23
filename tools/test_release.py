"""Tests for tools/release.py -- the filtered public-mirror release builder.

Hermetic and network-free: every "remote" used here is a local bare git
repo created in a temp directory, never the real `origin` or a real public
mirror. Fixtures build small synthetic git repos rather than depending on
this checkout's actual HEAD, so tests are independent of what's currently
committed in D:\\forge.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import release  # noqa: E402


def _git(args, cwd, check=True):
    result = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def _make_repo(tmp_path, extra_files=None, commit=True):
    """Build a small synthetic git repo with the shape release.py expects:
    .claude-plugin/plugin.json, tools/release-denylist.txt, LICENSE,
    README.md, memory/, .forge/, docs/audits/. extra_files merges in
    additional {relpath: content} entries. Returns the repo root."""
    repo = pathlib.Path(tmp_path) / "repo"
    repo.mkdir()
    _git(["init", "-q"], cwd=repo)
    _git(["config", "user.email", "t@t.local"], cwd=repo)
    _git(["config", "user.name", "T"], cwd=repo)

    files = {
        ".claude-plugin/plugin.json": json.dumps({"name": "forge", "version": "1.2.3"}),
        "tools/release-denylist.txt": "# comment\n\n.forge\ndocs/audits\n",
        "LICENSE": "MIT\n",
        "README.md": "# Forge\n",
        "memory/mem-0001.md": "# a craft memory fact\n",
        ".forge/queue/tasks/fg-x.md": "queue state\n",
        ".forge/forge.md": "kernel config\n",
        "docs/audits/report.md": "audit output\n",
        "docs/conventions.md": "conventions\n",
    }
    if extra_files:
        files.update(extra_files)

    for relpath, content in files.items():
        p = repo / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    if commit:
        _git(["add", "-A"], cwd=repo)
        _git(["-c", "user.email=t@t.local", "-c", "user.name=T", "commit", "-q", "-m", "init"], cwd=repo)

    return repo


def _make_bare_remote(tmp_path, name="remote.git"):
    bare = pathlib.Path(tmp_path) / name
    _git(["init", "-q", "--bare", str(bare)], cwd=tmp_path)
    return bare


class TestReadVersion(unittest.TestCase):
    def test_parses_version_from_plugin_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_json = pathlib.Path(tmp) / "plugin.json"
            plugin_json.write_text(json.dumps({"name": "forge", "version": "0.10.0"}), encoding="utf-8")
            self.assertEqual(release.read_version(plugin_json), "0.10.0")

    def test_missing_version_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_json = pathlib.Path(tmp) / "plugin.json"
            plugin_json.write_text(json.dumps({"name": "forge"}), encoding="utf-8")
            with self.assertRaises(release.ReleaseError):
                release.read_version(plugin_json)

    def test_malformed_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_json = pathlib.Path(tmp) / "plugin.json"
            plugin_json.write_text("{not json", encoding="utf-8")
            with self.assertRaises(release.ReleaseError):
                release.read_version(plugin_json)


class TestDenylist(unittest.TestCase):
    def test_real_denylist_pins_forge_and_audits(self):
        """Pins the two load-bearing denylist entries the acceptance
        criteria name explicitly: .forge/ and docs/audits/."""
        denylist = release.load_denylist(REPO_ROOT / "tools" / "release-denylist.txt")
        self.assertIn(".forge", denylist)
        self.assertIn("docs/audits", denylist)

    def test_real_denylist_pins_internal_docs_dirs(self):
        """fg-a10921 security audit F2: drills/plans/diagnostics are internal
        dev-history (local machine topology, private repo names) and must
        never ship in a public release."""
        denylist = release.load_denylist(REPO_ROOT / "tools" / "release-denylist.txt")
        self.assertIn("docs/drills", denylist)
        self.assertIn("docs/plans", denylist)
        self.assertIn("docs/diagnostics", denylist)
        # Delta re-audit P2: the original design doc discloses an unreleased
        # product + raw decision-log narrative -- internal history class.
        self.assertIn("docs/specs", denylist)

    def test_load_denylist_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "denylist.txt"
            path.write_text("# comment\n\n  .forge  \ndocs/audits/\n", encoding="utf-8")
            self.assertEqual(release.load_denylist(path), [".forge", "docs/audits"])

    def test_is_denied_matches_exact_and_nested(self):
        denylist = [".forge", "docs/audits"]
        self.assertTrue(release.is_denied(".forge", denylist))
        self.assertTrue(release.is_denied(".forge/queue/tasks/x.md", denylist))
        self.assertTrue(release.is_denied("docs/audits/report.md", denylist))

    def test_is_denied_is_boundary_safe(self):
        """"docs/audits" must not falsely deny a sibling like
        "docs/audits-old" that merely shares a prefix string."""
        denylist = ["docs/audits"]
        self.assertFalse(release.is_denied("docs/audits-old/report.md", denylist))
        self.assertFalse(release.is_denied("docs/conventions.md", denylist))
        self.assertFalse(release.is_denied("README.md", denylist))


class TestLeakScan(unittest.TestCase):
    def test_clean_tree_has_no_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = pathlib.Path(tmp) / "export"
            (export_dir / "memory").mkdir(parents=True)
            (export_dir / "memory" / "mem-1.md").write_text("x", encoding="utf-8")
            (export_dir / "README.md").write_text("x", encoding="utf-8")
            self.assertEqual(release.scan_for_leaks(export_dir, [".forge", "docs/audits"]), [])

    def test_planted_denylisted_path_is_caught(self):
        """A denylisted path that ends up in the export tree by some other
        means (e.g. a bug in the extraction filter) must still be caught by
        the independent post-build scan."""
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = pathlib.Path(tmp) / "export"
            (export_dir / ".forge" / "queue" / "tasks").mkdir(parents=True)
            (export_dir / ".forge" / "queue" / "tasks" / "fg-x.md").write_text("leak", encoding="utf-8")
            (export_dir / "docs" / "audits").mkdir(parents=True)
            (export_dir / "docs" / "audits" / "report.md").write_text("leak", encoding="utf-8")
            (export_dir / "README.md").write_text("fine", encoding="utf-8")

            leaks = release.scan_for_leaks(export_dir, [".forge", "docs/audits"])

            self.assertIn(".forge/queue/tasks/fg-x.md", leaks)
            self.assertIn("docs/audits/report.md", leaks)
            self.assertNotIn("README.md", leaks)


class TestBuildExport(unittest.TestCase):
    def test_export_excludes_denylist_includes_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            denylist = release.load_denylist(repo / "tools" / "release-denylist.txt")
            export_dir = pathlib.Path(tmp) / "export"

            manifest = release.build_export(repo, export_dir, denylist)

            self.assertIn("LICENSE", manifest)
            self.assertIn("README.md", manifest)
            self.assertIn("memory/mem-0001.md", manifest)
            self.assertIn("docs/conventions.md", manifest)
            self.assertFalse(any(f.startswith(".forge/") for f in manifest))
            self.assertFalse(any(f.startswith("docs/audits/") for f in manifest))
            self.assertEqual(release.scan_for_leaks(export_dir, denylist), [])

    def test_export_reads_committed_state_not_working_tree(self):
        """build_export must archive `ref` (HEAD by default), never the
        dirty working tree -- an uncommitted file must not appear."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            (repo / "uncommitted.md").write_text("not committed", encoding="utf-8")
            denylist = release.load_denylist(repo / "tools" / "release-denylist.txt")
            export_dir = pathlib.Path(tmp) / "export"

            manifest = release.build_export(repo, export_dir, denylist)

            self.assertNotIn("uncommitted.md", manifest)


class TestRunReleaseDryRun(unittest.TestCase):
    def test_dry_run_prints_manifest_without_remote_configured(self):
        """--dry-run must work even with no public remote configured (it
        does everything except push) and must never attempt to push."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            out = _StrOut()

            release.run_release(repo, dry_run=True, out=out)

            text = out.getvalue()
            self.assertIn("v1.2.3", text)
            self.assertIn("README.md", text)
            self.assertNotIn(".forge/", text)

    def test_dry_run_refuses_dirty_working_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            (repo / "README.md").write_text("dirty edit", encoding="utf-8")

            with self.assertRaises(release.ReleaseError) as ctx:
                release.run_release(repo, dry_run=True, out=_StrOut())
            self.assertIn("dirty", str(ctx.exception).lower())

    def test_dry_run_makes_no_pushes(self):
        """Point 'public' at a bare repo, run --dry-run, and assert the
        bare repo gained no refs at all -- proves dry-run never pushes."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            bare = _make_bare_remote(tmp)
            _git(["remote", "add", "public", str(bare)], cwd=repo)

            release.run_release(repo, dry_run=True, out=_StrOut())

            refs = _git(["for-each-ref"], cwd=bare).stdout.strip()
            self.assertEqual(refs, "", "dry-run must not push any ref to the remote")


class TestRunReleaseRemoteHandling(unittest.TestCase):
    def test_missing_remote_prints_instructions_and_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)  # no 'public' remote configured

            with self.assertRaises(release.ReleaseError) as ctx:
                release.run_release(repo, dry_run=False, out=_StrOut())

            msg = str(ctx.exception)
            self.assertIn("git remote add public", msg)

    def test_tag_already_on_remote_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            bare = _make_bare_remote(tmp)
            _git(["remote", "add", "public", str(bare)], cwd=repo)

            release.run_release(repo, dry_run=False, out=_StrOut())  # first release succeeds

            with self.assertRaises(release.ReleaseError) as ctx:
                release.run_release(repo, dry_run=False, out=_StrOut())  # same version again
            self.assertIn("v1.2.3", str(ctx.exception))
            self.assertIn("already exists", str(ctx.exception).lower())

    def test_successful_release_pushes_single_tagged_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            bare = _make_bare_remote(tmp)
            _git(["remote", "add", "public", str(bare)], cwd=repo)

            release.run_release(repo, dry_run=False, out=_StrOut())

            tags = _git(["tag"], cwd=bare).stdout.split()
            self.assertIn("v1.2.3", tags)

            log = _git(["log", "--format=%H", "refs/heads/main"], cwd=bare).stdout.split()
            self.assertEqual(len(log), 1, "public branch must hold exactly one squashed commit")

            ls = _git(["ls-tree", "-r", "--name-only", "refs/heads/main"], cwd=bare).stdout.splitlines()
            self.assertIn("LICENSE", ls)
            self.assertIn("memory/mem-0001.md", ls)
            self.assertFalse(any(f.startswith(".forge/") for f in ls))
            self.assertFalse(any(f.startswith("docs/audits/") for f in ls))


class TestRunReleaseLeakScanGate(unittest.TestCase):
    def test_leak_scan_failure_blocks_push(self):
        """Simulate a bug in build_export's own filtering (it plants a
        denylisted file into the export tree despite a correct denylist)
        and confirm run_release's independent post-build scan still catches
        it and blocks the push -- the scan must not share build_export's
        blind spots."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            bare = _make_bare_remote(tmp)
            _git(["remote", "add", "public", str(bare)], cwd=repo)

            real_build_export = release.build_export

            def leaky_build_export(repo_root, dest_dir, denylist, ref="HEAD"):
                manifest = real_build_export(repo_root, dest_dir, denylist, ref)
                leak_path = pathlib.Path(dest_dir) / ".forge" / "leaked.md"
                leak_path.parent.mkdir(parents=True, exist_ok=True)
                leak_path.write_text("leak", encoding="utf-8")
                return manifest

            with mock.patch.object(release, "build_export", side_effect=leaky_build_export):
                with self.assertRaises(release.ReleaseError) as ctx:
                    release.run_release(repo, dry_run=False, out=_StrOut())
            self.assertIn("leak", str(ctx.exception).lower())

            refs = _git(["for-each-ref"], cwd=bare).stdout.strip()
            self.assertEqual(refs, "", "leak-scan failure must block the push entirely")


class TestMainCLI(unittest.TestCase):
    def test_main_dry_run_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            code = release.main(["--dry-run", "--repo-root", str(repo)])
            self.assertEqual(code, 0)

    def test_main_missing_remote_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp)
            code = release.main(["--repo-root", str(repo)])
            self.assertEqual(code, 1)


class _StrOut:
    """Minimal io.StringIO stand-in usable with print(..., file=out)."""

    def __init__(self):
        self._parts = []

    def write(self, s):
        self._parts.append(s)

    def getvalue(self):
        return "".join(self._parts)


if __name__ == "__main__":
    unittest.main()


class TestContributorCredit(unittest.TestCase):
    """fg-a10921 follow-on: public contributor credit via Co-authored-by
    trailers on the squashed release commit (the mirror's fresh-history
    model means trailer credit IS the contributors graph)."""

    def test_load_contributors_parses_entry_lines_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "CONTRIBUTORS.md"
            p.write_text(
                "# Contributors\n\nProse about the format <not@an.entry> here.\n"
                "- BenMacDeezy <216523260+BenMacDeezy@users.noreply.github.com>\n"
                "- dbcoup <261831342+dbcoup@users.noreply.github.com>\n"
                "- malformed line without email\n",
                encoding="utf-8",
            )
            got = release.load_contributors(p)
        self.assertEqual(got, [
            "BenMacDeezy <216523260+BenMacDeezy@users.noreply.github.com>",
            "dbcoup <261831342+dbcoup@users.noreply.github.com>",
        ])

    def test_load_contributors_missing_file_is_empty_never_raises(self):
        self.assertEqual(
            release.load_contributors(pathlib.Path("does/not/exist.md")), [])

    def test_real_contributors_file_lists_both_maintainers(self):
        got = release.load_contributors(REPO_ROOT / "CONTRIBUTORS.md")
        names = [c.split(" <")[0] for c in got]
        self.assertIn("BenMacDeezy", names)
        self.assertIn("dbcoup", names)

    def test_release_commit_carries_coauthor_trailers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            bare = base / "remote.git"
            subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
            export = base / "export"
            export.mkdir()
            (export / "README.md").write_text("hi\n", encoding="utf-8")
            release.commit_and_push(
                export, str(bare), "v9.9.9",
                contributors=["dbcoup <261831342+dbcoup@users.noreply.github.com>"],
            )
            msg = subprocess.run(
                ["git", "log", "-1", "--format=%B", "main"],
                cwd=bare, capture_output=True, text=True, check=True,
            ).stdout
        self.assertIn(
            "Co-authored-by: dbcoup <261831342+dbcoup@users.noreply.github.com>",
            msg,
        )
