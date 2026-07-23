"""Deterministic, propose-only worktree sweep (fg-b0403). Zero dependencies.

Joins `git worktree list --porcelain` against `.forge/queue/tasks/*.md`
claims (claimed-by + claim-staleness-hours from forge.md) and classifies
every Forge-managed worktree (one whose branch matches `wt-<suffix>`,
joined to task `fg-<suffix>`, mirroring the `fg-<id>` / `wt-<id>` naming
convention used throughout docs/conventions/dispatch-and-routing.md) as:

  ACTIVE            -- the joined task holds a live (non-stale) claim
  ORPHAN-CANDIDATE  -- no live claim, but the worktree has uncommitted
                       changes -- a human must decide what to do with it
  CLEAN-REMOVABLE   -- no live claim and the worktree is clean -- a safe
                       `git worktree remove` candidate

This script NEVER DELETES ANYTHING -- it only proposes, matching the
kernel's SYNC sweep's human-approved-cleanup rule (this script makes that
rule testable and deterministic instead of prose-driven; forge-scout
finding 2026-07-19). See .forge/map/subsystems/kernel.md for how this
relates to the harness-native worktree cleanup layer underneath it.

Reuses tools/status.py's task loading (which itself reuses
validate_task.py's frontmatter parsing, per fg-b0403's boundary: "reuse
existing frontmatter helpers from validate_task.py rather than
re-parsing") and status.py's claim-staleness math (_CLAIMED_BY_TS_RE /
_iso_to_dt / load_claim_staleness_hours) for the same reason.

Subprocess calls (`git worktree list --porcelain`, `git status
--porcelain`) happen ONLY inside main() and its two small `_git_*` helpers
-- every other function accepts already-collected text/data so tests never
need to shell out or touch a real git repo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys

_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import status

CLASS_ACTIVE = "ACTIVE"
CLASS_ORPHAN = "ORPHAN-CANDIDATE"
CLASS_CLEAN = "CLEAN-REMOVABLE"

# Forge worktree branches are named `wt-<suffix>` for task `fg-<suffix>`
# (see D:\forge-wt-b0403 itself: branch `wt-b0403` / task `fg-b0403`).
_BRANCH_RE = re.compile(r"^refs/heads/wt-(.+)$")


# ---------------------------------------------------------------------------
# `git worktree list --porcelain` parsing
# ---------------------------------------------------------------------------

def _finalize_entry(current):
    """Turn an in-progress porcelain block into an entry dict, or None if
    it never saw a `worktree <path>` header (malformed/stray lines)."""
    if current and current.get("path"):
        return {
            "path": current["path"],
            "branch": current.get("branch"),
            "detached": current.get("detached", False),
            "bare": current.get("bare", False),
        }
    return None


def parse_worktree_porcelain(text):
    """Parse `git worktree list --porcelain` output into a list of dicts:
    {"path": str, "branch": str|None, "detached": bool, "bare": bool}.

    Tolerant of malformed/unexpected input: entries without a leading
    `worktree <path>` line are dropped, unrecognized lines within an entry
    are ignored, and non-string/empty/garbage input yields []. Never
    raises.
    """
    if not isinstance(text, str):
        return []

    entries = []
    current = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            e = _finalize_entry(current)
            if e:
                entries.append(e)
            current = {}
            continue
        if line.startswith("worktree "):
            e = _finalize_entry(current)
            if e:
                entries.append(e)
            current = {"path": line[len("worktree "):].strip()}
            continue
        if not current:
            # Stray line before any `worktree` header -- ignore.
            continue
        if line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip()
        elif stripped == "detached":
            current["detached"] = True
        elif stripped == "bare":
            current["bare"] = True
        # HEAD/locked/prunable and anything else: not needed for
        # classification, ignored rather than erroring.

    e = _finalize_entry(current)
    if e:
        entries.append(e)
    return entries


def task_id_for_branch(branch):
    """Map a worktree branch (e.g. 'refs/heads/wt-b0403') to the Forge task
    id it belongs to ('fg-b0403'), or None if the branch isn't a
    Forge-managed worktree branch (main, detached, an unrelated feature
    branch, or a malformed/empty `wt-` suffix)."""
    if not branch:
        return None
    m = _BRANCH_RE.match(branch)
    if not m or not m.group(1):
        return None
    return "fg-" + m.group(1)


# ---------------------------------------------------------------------------
# Claim liveness -- reuses status.py's own stale-claim math so this script
# and `/forge:status`'s "Stale claims" section can never silently disagree.
# ---------------------------------------------------------------------------

def is_live_claim(task, now, claim_staleness_hours):
    """True if `task` (a status.load_tasks()-shaped record, or None) holds
    a live claim right now: state == "active", a well-formed claimed-by,
    and age <= claim_staleness_hours.

    The boundary matches status.py's build_stale_claims_section exactly
    (which flags `age_hours > claim_staleness_hours` as stale) -- a claim
    exactly AT the threshold is still live here, not stale.
    """
    if task is None or task.get("state") != "active":
        return False
    claimed = task.get("claimed_by")
    if not claimed or claimed == "null":
        return False
    m = status._CLAIMED_BY_TS_RE.match(claimed)
    if not m:
        return False
    claimed_dt = status._iso_to_dt(m.group(1))
    if claimed_dt is None:
        return False
    age_hours = (now - claimed_dt).total_seconds() / 3600.0
    return age_hours <= claim_staleness_hours


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_worktrees(worktree_entries, tasks, now, claim_staleness_hours,
                        dirty_by_path):
    """Classify every Forge-managed worktree entry (branch matches
    `wt-<suffix>`, per task_id_for_branch). Entries with no matching branch
    (main, detached, an unrelated branch) are not Forge task worktrees and
    are skipped entirely -- this script only proposes cleanup for
    worktrees it can attribute to a queue task.

    `dirty_by_path` maps a worktree's path -> bool (True = dirty / has
    uncommitted changes) for entries that need a tree-cleanliness check
    (i.e. every entry without a live claim). A path missing from
    `dirty_by_path` is treated as dirty -- fail safe: unknown status never
    downgrades to a removal proposal.

    Returns a list of dicts {"path", "branch", "task_id", "classification"}
    sorted by path for deterministic output.
    """
    results = []
    for entry in worktree_entries:
        task_id = task_id_for_branch(entry.get("branch"))
        if task_id is None:
            continue
        task = tasks.get(task_id) if tasks else None
        if is_live_claim(task, now, claim_staleness_hours):
            classification = CLASS_ACTIVE
        else:
            dirty = dirty_by_path.get(entry["path"], True)
            classification = CLASS_ORPHAN if dirty else CLASS_CLEAN
        results.append({
            "path": entry["path"],
            "branch": entry.get("branch"),
            "task_id": task_id,
            "classification": classification,
        })
    results.sort(key=lambda r: r["path"])
    return results


# ---------------------------------------------------------------------------
# CLI -- the only place subprocess is invoked.
# ---------------------------------------------------------------------------

def _git_worktree_list_porcelain(root):
    """Returns (stdout_text, error_or_None). Never raises."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return "", (proc.stderr.strip() or f"exit {proc.returncode}")
        return proc.stdout, None
    except (OSError, subprocess.SubprocessError) as e:
        return "", str(e)


def _git_status_porcelain(path):
    """Returns the `git status --porcelain` stdout for `path`, or None if
    the command could not be run/failed (e.g. the worktree was already
    removed on disk). Never raises."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv=None):
    # See validate_task.py's/status.py's main() for why: em dashes in this
    # module's own output would otherwise crash under a legacy Windows OEM
    # codepage.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="worktree_sweep.py",
        description="Propose-only classification of git worktrees against "
                     "live Forge queue claims. Never deletes anything.",
    )
    parser.add_argument("--root", default=".",
                         help="project root containing .forge/ and the git "
                              "repo (default: cwd)")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root)
    task_dir = root / ".forge" / "queue" / "tasks"
    forge_md = root / ".forge" / "forge.md"

    porcelain_text, err = _git_worktree_list_porcelain(root)
    if err is not None:
        print(f"worktree_sweep: could not run `git worktree list`: {err}",
              file=sys.stderr)
        return 1

    entries = parse_worktree_porcelain(porcelain_text)
    tasks, _skipped = status.load_tasks(task_dir)
    claim_staleness_hours = status.load_claim_staleness_hours(forge_md)
    now = dt.datetime.now(dt.timezone.utc)

    # Only entries that could end up ORPHAN/CLEAN need a dirty check --
    # skip the subprocess call entirely for ACTIVE ones and for
    # non-Forge branches (main, detached, foreign branches).
    dirty_by_path = {}
    for entry in entries:
        task_id = task_id_for_branch(entry.get("branch"))
        if task_id is None:
            continue
        task = tasks.get(task_id)
        if is_live_claim(task, now, claim_staleness_hours):
            continue
        status_text = _git_status_porcelain(entry["path"])
        dirty_by_path[entry["path"]] = (
            True if status_text is None else bool(status_text)
        )

    results = classify_worktrees(
        entries, tasks, now, claim_staleness_hours, dirty_by_path
    )

    if not results:
        print("worktree_sweep: no Forge-managed worktrees found "
              "(nothing to sweep).")
        return 0

    print("PROPOSE-ONLY -- this script never deletes anything. "
          "ORPHAN-CANDIDATE needs a human decision; CLEAN-REMOVABLE is a "
          "safe `git worktree remove` candidate.")
    print()
    for r in results:
        note = ""
        if r["classification"] == CLASS_ORPHAN:
            note = " (dirty tree)"
        elif r["classification"] == CLASS_CLEAN:
            note = " (clean tree)"
        print(f"{r['classification']:<18} {r['task_id']:<10} "
              f"{r['path']}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
