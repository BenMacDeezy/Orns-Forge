"""Project scope guard (project-scope-guard task, 2026-07-20).

Deterministic accelerator for deciding whether a `.forge/` directory about
to be read or written actually belongs to the CURRENT project, or whether
the session has silently resolved to a DIFFERENT repo's `.forge/` (wrong
cwd at launch, a subdirectory whose git toplevel is a different repo, a
moved/OneDrive-synced folder with the old location still present).

This is an accelerator, not the source of truth: the guard's rule is
defined in prose at `skills/kernel/references/scope-guard.md` (NORMATIVE)
and cited from `skills/kernel/SKILL.md` (SYNC) and `skills/queue/SKILL.md`
(Auto-init, the shared choke point for every queue write). This module
gives both a mechanically-checkable way to compute the same decision
instead of eyeballing paths. If Python is unavailable, check manually:
resolve `git -C <project dir> rev-parse --show-toplevel`, then compare the
canonical `.forge/` path against `<that toplevel>/.forge`. Zero third-party
dependencies, stdlib only.

The rule: resolve `project_dir` (CLAUDE_PROJECT_DIR env var if set and
non-empty, else cwd) and its git toplevel. The `.forge/` being operated on
MUST be `<that toplevel>/.forge`. Any different path is a MISMATCH: the
caller must stop and ask a human, never auto-pick. This includes a nested
same-repo `.forge/` and a nonexistent `.forge/` aimed at the wrong
location: auto-init there would create state in the wrong scope. If
`project_dir` is not inside a git repo at all, this guard is inert
(`no-git`) -- the existing cwd-fallback behavior applies unchanged. Any
other error resolving the project's git toplevel is `git-error`, which
must stop kernel/queue work and warn on read-only status surfaces.
"""
import collections
import os
import pathlib
import subprocess
import sys

ScopeResult = collections.namedtuple(
    "ScopeResult", ["match", "reason", "expected", "actual"]
)


class GitToplevelError(RuntimeError):
    """Git could not reliably decide the project's toplevel."""


def resolve_project_dir(env=None, cwd=None):
    """CLAUDE_PROJECT_DIR if set and non-empty, else cwd (or the given
    `cwd` override for testing)."""
    env = env if env is not None else os.environ
    value = env.get("CLAUDE_PROJECT_DIR")
    if value:
        return value
    return cwd if cwd is not None else os.getcwd()


def git_toplevel(path):
    """Resolved absolute git toplevel for `path`.

    Returns None only when git says the path is genuinely outside a work
    tree. Raises GitToplevelError for all other failures so callers cannot
    silently treat git/unreadable/dubious-ownership errors as `no-git`.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitToplevelError(str(exc)) from exc
    if result.returncode != 0:
        error = (result.stderr or "").strip()
        if "not a git repository" in error.lower():
            return None
        raise GitToplevelError(error or f"git exited {result.returncode}")
    out = result.stdout.strip()
    if not out:
        raise GitToplevelError("git returned an empty toplevel")
    return _canonical_path(out)


def _canonical_path(path):
    """Canonical absolute path, including for a nonexistent leaf."""
    try:
        return str(pathlib.Path(path).resolve(strict=False))
    except (OSError, RuntimeError):
        # Preserve fail-closed behavior on unusual/unreadable path shapes:
        # lexical absolute normalization still gives us a comparable path.
        return os.path.abspath(os.path.normpath(os.fspath(path)))


def _comparison_key(path):
    """Normalized comparison key (case-insensitive on Windows)."""
    normalized = os.path.normpath(path)
    if sys.platform == "win32":
        normalized = normalized.casefold()
    return normalized


def _same_canonical_path(expected, actual):
    """Compare canonical paths, using filesystem identity when available."""
    try:
        if os.path.exists(expected) and os.path.exists(actual):
            return os.path.samefile(expected, actual)
    except OSError:
        pass
    return _comparison_key(expected) == _comparison_key(actual)


def check_scope(forge_dir, project_dir=None, env=None, cwd=None):
    """Check whether `forge_dir` (the `.forge/` about to be read or
    written) is the current project's root-level `.forge/` path.

    Returns a ScopeResult(match, reason, expected, actual):
      - reason "no-git": `project_dir` is genuinely outside a git repo;
        the existing cwd-fallback rule applies elsewhere, match=True.
      - reason "git-error": git failed while resolving the project's
        toplevel for any other reason. Callers must stop/warn, match=False.
      - reason "match": canonical `forge_dir` equals canonical
        `<project toplevel>/.forge`, match=True. `project_dir` itself may
        be nested anywhere inside that repo.
      - reason "mismatch": those canonical paths differ, including a
        nested same-repo `.forge/` or a nonexistent wrong target.
        `expected`/`actual` are populated for the human.
    """
    if project_dir is None:
        project_dir = resolve_project_dir(env=env, cwd=cwd)

    try:
        project_toplevel = git_toplevel(project_dir)
    except (GitToplevelError, OSError, subprocess.SubprocessError):
        return ScopeResult(
            False, "git-error", None, _canonical_path(forge_dir)
        )
    if project_toplevel is None:
        return ScopeResult(True, "no-git", None, None)

    expected = _canonical_path(pathlib.Path(project_toplevel) / ".forge")
    actual = _canonical_path(forge_dir)

    if _same_canonical_path(expected, actual):
        return ScopeResult(True, "match", expected, actual)
    return ScopeResult(False, "mismatch", expected, actual)


def main(argv):
    forge_dir = argv[0] if argv else ".forge"
    project_dir = None
    if "--project-dir" in argv:
        idx = argv.index("--project-dir")
        if idx + 1 < len(argv):
            project_dir = argv[idx + 1]

    result = check_scope(forge_dir, project_dir=project_dir)
    if result.match:
        print(result.reason)
        return 0
    if result.reason == "git-error":
        unresolved = project_dir or resolve_project_dir()
        print(
            "git-error: could not resolve project toplevel for "
            f"{unresolved}"
        )
        return 1
    print(f"mismatch: expected {result.expected} actual {result.actual}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
