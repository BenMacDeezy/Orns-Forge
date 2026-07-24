"""Tests for tools/worktree_sweep.py (fg-b0403): deterministic, propose-only
classification of git worktrees against live Forge queue claims.

Per the task's boundary note ("Accept injected porcelain text in tests
(subprocess only in main())"), every test below drives the pure functions
(parse_worktree_porcelain / task_id_for_branch / is_live_claim /
classify_worktrees) with injected text/data, or -- for the CLI-wiring
tests -- monkeypatches worktree_sweep's two `_git_*` subprocess wrappers
directly, so no test ever shells out to a real `git` process.
"""
import datetime as dt
import pathlib
import tempfile
import unittest

import worktree_sweep as ws

NOW = dt.datetime(2026, 7, 20, 12, 0, 0, tzinfo=dt.timezone.utc)


def _task(state, claimed_by=None):
    return {"state": state, "claimed_by": claimed_by or "null"}


def _claimed_by(offset_hours):
    ts = NOW - dt.timedelta(hours=offset_hours)
    return f"sess-ab12 @ {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}"


# ---------------------------------------------------------------------------
# parse_worktree_porcelain
# ---------------------------------------------------------------------------

class ParsePorcelainTests(unittest.TestCase):
    def test_well_formed_multi_entry_porcelain(self):
        text = (
            "worktree D:/forge\n"
            "HEAD c1f2058f842f07eb128b6692ea46fbf9ba437fc1\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree D:/forge-wt-b0403\n"
            "HEAD c1f2058f842f07eb128b6692ea46fbf9ba437fc1\n"
            "branch refs/heads/wt-b0403\n"
        )
        entries = ws.parse_worktree_porcelain(text)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["path"], "D:/forge")
        self.assertEqual(entries[0]["branch"], "refs/heads/main")
        self.assertEqual(entries[1]["path"], "D:/forge-wt-b0403")
        self.assertEqual(entries[1]["branch"], "refs/heads/wt-b0403")

    def test_detached_worktree_has_no_branch(self):
        text = (
            "worktree D:/forge-detached\n"
            "HEAD c1f2058f842f07eb128b6692ea46fbf9ba437fc1\n"
            "detached\n"
        )
        entries = ws.parse_worktree_porcelain(text)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]["branch"])
        self.assertTrue(entries[0]["detached"])

    def test_bare_repo_entry(self):
        text = "worktree D:/forge.git\nbare\n"
        entries = ws.parse_worktree_porcelain(text)
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["bare"])

    def test_empty_string_yields_no_entries(self):
        self.assertEqual(ws.parse_worktree_porcelain(""), [])

    def test_none_input_does_not_raise(self):
        self.assertEqual(ws.parse_worktree_porcelain(None), [])

    def test_garbage_lines_before_any_header_are_ignored(self):
        text = (
            "not a worktree line\n"
            "branch refs/heads/wt-orphan\n"
            "\n"
            "worktree D:/forge-wt-real\n"
            "branch refs/heads/wt-real\n"
        )
        entries = ws.parse_worktree_porcelain(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["path"], "D:/forge-wt-real")

    def test_totally_malformed_text_does_not_raise(self):
        text = "\x00\x01garbage\n===\n---\nworktree\n"
        # Should not raise; a "worktree" line with no path text after the
        # marker+space just produces no usable path and is dropped.
        entries = ws.parse_worktree_porcelain(text)
        self.assertIsInstance(entries, list)


# ---------------------------------------------------------------------------
# task_id_for_branch
# ---------------------------------------------------------------------------

class TaskIdForBranchTests(unittest.TestCase):
    def test_wt_branch_maps_to_fg_task_id(self):
        self.assertEqual(
            ws.task_id_for_branch("refs/heads/wt-b0403"), "fg-b0403"
        )

    def test_main_branch_is_not_a_task_worktree(self):
        self.assertIsNone(ws.task_id_for_branch("refs/heads/main"))

    def test_none_branch(self):
        self.assertIsNone(ws.task_id_for_branch(None))

    def test_empty_suffix_is_not_a_task_worktree(self):
        self.assertIsNone(ws.task_id_for_branch("refs/heads/wt-"))

    def test_unrelated_feature_branch(self):
        self.assertIsNone(ws.task_id_for_branch("refs/heads/feature/foo"))


# ---------------------------------------------------------------------------
# is_live_claim -- stale-vs-live boundary at exactly claim-staleness-hours
# ---------------------------------------------------------------------------

class IsLiveClaimTests(unittest.TestCase):
    def test_fresh_claim_is_live(self):
        task = _task("active", _claimed_by(0.0))
        self.assertTrue(ws.is_live_claim(task, NOW, 0.5))

    def test_claim_exactly_at_boundary_is_still_live(self):
        task = _task("active", _claimed_by(0.5))
        self.assertTrue(ws.is_live_claim(task, NOW, 0.5))

    def test_claim_just_past_boundary_is_stale(self):
        task = _task("active", _claimed_by(0.5001))
        self.assertFalse(ws.is_live_claim(task, NOW, 0.5))

    def test_claim_far_past_boundary_is_stale(self):
        task = _task("active", _claimed_by(5.0))
        self.assertFalse(ws.is_live_claim(task, NOW, 0.5))

    def test_non_active_state_is_not_live(self):
        task = _task("ready", _claimed_by(0.0))
        self.assertFalse(ws.is_live_claim(task, NOW, 0.5))

    def test_null_claimed_by_is_not_live(self):
        task = _task("active", None)
        self.assertFalse(ws.is_live_claim(task, NOW, 0.5))

    def test_malformed_claimed_by_is_not_live(self):
        task = {"state": "active", "claimed_by": "bob"}
        self.assertFalse(ws.is_live_claim(task, NOW, 0.5))

    def test_missing_task_is_not_live(self):
        self.assertFalse(ws.is_live_claim(None, NOW, 0.5))


# ---------------------------------------------------------------------------
# classify_worktrees -- the three classifications, joined
# ---------------------------------------------------------------------------

class ClassifyWorktreesTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"path": "D:/forge", "branch": "refs/heads/main"},
            {"path": "D:/forge-wt-active", "branch": "refs/heads/wt-active"},
            {"path": "D:/forge-wt-orphan", "branch": "refs/heads/wt-orphan"},
            {"path": "D:/forge-wt-clean", "branch": "refs/heads/wt-clean"},
            {"path": "D:/forge-wt-unknowndirty",
             "branch": "refs/heads/wt-unknowndirty"},
        ]
        self.tasks = {
            "fg-active": _task("active", _claimed_by(0.0)),
            "fg-orphan": _task("ready", None),
            # fg-clean and fg-unknowndirty deliberately absent (no task
            # file at all) -- classification must still work when the
            # queue task was already deleted/dropped.
        }

    def test_main_branch_is_skipped_entirely(self):
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, {}
        )
        paths = [r["path"] for r in results]
        self.assertNotIn("D:/forge", paths)

    def test_live_claim_classifies_active(self):
        dirty = {"D:/forge-wt-active": True}
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, dirty
        )
        row = next(r for r in results if r["task_id"] == "fg-active")
        self.assertEqual(row["classification"], ws.CLASS_ACTIVE)

    def test_no_live_claim_and_dirty_tree_classifies_orphan_candidate(self):
        dirty = {"D:/forge-wt-orphan": True}
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, dirty
        )
        row = next(r for r in results if r["task_id"] == "fg-orphan")
        self.assertEqual(row["classification"], ws.CLASS_ORPHAN)

    def test_no_live_claim_and_clean_tree_classifies_clean_removable(self):
        dirty = {"D:/forge-wt-clean": False}
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, dirty
        )
        row = next(r for r in results if r["task_id"] == "fg-clean")
        self.assertEqual(row["classification"], ws.CLASS_CLEAN)

    def test_unknown_dirty_status_fails_safe_to_orphan_candidate(self):
        # D:/forge-wt-unknowndirty is intentionally absent from the dirty
        # map -- unknown status must never be treated as "safe to remove".
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, {}
        )
        row = next(r for r in results if r["task_id"] == "fg-unknowndirty")
        self.assertEqual(row["classification"], ws.CLASS_ORPHAN)

    def test_results_sorted_by_path(self):
        dirty = {
            "D:/forge-wt-active": False,
            "D:/forge-wt-orphan": True,
            "D:/forge-wt-clean": False,
            "D:/forge-wt-unknowndirty": True,
        }
        results = ws.classify_worktrees(
            self.entries, self.tasks, NOW, 0.5, dirty
        )
        paths = [r["path"] for r in results]
        self.assertEqual(paths, sorted(paths))


# ---------------------------------------------------------------------------
# Malformed porcelain tolerance, end to end (parse -> classify)
# ---------------------------------------------------------------------------

class MalformedPorcelainToleranceTests(unittest.TestCase):
    def test_garbage_porcelain_classifies_to_empty_list_without_raising(self):
        garbage = "this is\nnot valid porcelain output at all\n\x00\x01"
        entries = ws.parse_worktree_porcelain(garbage)
        results = ws.classify_worktrees(entries, {}, NOW, 0.5, {})
        self.assertEqual(results, [])

    def test_mixed_valid_and_malformed_entries(self):
        text = (
            "garbage-preamble\n"
            "worktree D:/forge-wt-good\n"
            "branch refs/heads/wt-good\n"
            "stray unrecognized line\n"
            "\n"
            "worktree\n"  # header with no path text -- must be dropped
            "branch refs/heads/wt-bad\n"
        )
        entries = ws.parse_worktree_porcelain(text)
        # Only the well-formed "wt-good" entry should survive; the
        # path-less "worktree" header must not crash or fabricate a task.
        paths = [e["path"] for e in entries]
        self.assertIn("D:/forge-wt-good", paths)
        results = ws.classify_worktrees(
            entries, {}, NOW, 0.5, {"D:/forge-wt-good": False}
        )
        task_ids = [r["task_id"] for r in results]
        self.assertIn("fg-good", task_ids)


# ---------------------------------------------------------------------------
# main() CLI wiring -- subprocess wrappers are monkeypatched, never real git
# ---------------------------------------------------------------------------

class MainCliTests(unittest.TestCase):
    def _make_root(self, forge_md_extra=""):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        task_dir = root / ".forge" / "queue" / "tasks"
        task_dir.mkdir(parents=True)
        forge_md = root / ".forge" / "forge.md"
        forge_md.write_text(
            "# Forge config\n\n## Queue\n"
            "- claim-staleness-hours: 0.5\n" + forge_md_extra,
            encoding="utf-8",
        )
        return root, task_dir

    def _write_task(self, task_dir, task_id, state, claimed_by="null"):
        text = (
            "---\n"
            f"id: {task_id}\n"
            "title: \"t\"\n"
            f"state: {state}\n"
            "tier: standard\n"
            "priority: 2\n"
            "spec: null\n"
            "blocks: []\n"
            "blocked-by: []\n"
            f"claimed-by: {claimed_by}\n"
            "parallel-safe: true\n"
            "created: 2026-07-19T14:30:00Z\n"
            "updated: 2026-07-19T14:30:00Z\n"
            "schema-version: 1\n"
            "---\n\n"
            "## Acceptance criteria\nx\n\n## Execution plan\nx\n\n"
            "## Routing record\n(pending)\n\n## Attempt log\n(pending)\n\n"
            "## Outcome\n(pending)\n"
        )
        (task_dir / f"{task_id}.md").write_text(text, encoding="utf-8")

    def test_repo_without_worktrees_exits_zero(self):
        root, task_dir = self._make_root()
        # Only the main worktree, on branch main -- no Forge task branches.
        porcelain = "worktree {}\nbranch refs/heads/main\n".format(root)

        orig_list = ws._git_worktree_list_porcelain
        orig_status = ws._git_status_porcelain
        ws._git_worktree_list_porcelain = lambda r: (porcelain, None)
        ws._git_status_porcelain = lambda p: ""
        try:
            rc = ws.main(["--root", str(root)])
        finally:
            ws._git_worktree_list_porcelain = orig_list
            ws._git_status_porcelain = orig_status
        self.assertEqual(rc, 0)

    def test_main_classifies_active_and_clean_worktrees(self):
        root, task_dir = self._make_root()
        self._write_task(task_dir, "fg-live", "active",
                          _claimed_by(0.0))
        porcelain = (
            f"worktree {root}\nbranch refs/heads/main\n\n"
            f"worktree {root}-wt-live\nbranch refs/heads/wt-live\n\n"
            f"worktree {root}-wt-gone\nbranch refs/heads/wt-gone\n"
        )
        ws._git_worktree_list_porcelain_orig = ws._git_worktree_list_porcelain
        ws._git_status_porcelain_orig = ws._git_status_porcelain
        ws._git_worktree_list_porcelain = lambda r: (porcelain, None)
        ws._git_status_porcelain = lambda p: ""  # clean
        try:
            rc = ws.main(["--root", str(root)])
        finally:
            ws._git_worktree_list_porcelain = ws._git_worktree_list_porcelain_orig
            ws._git_status_porcelain = ws._git_status_porcelain_orig
            del ws._git_worktree_list_porcelain_orig
            del ws._git_status_porcelain_orig
        self.assertEqual(rc, 0)

    def test_git_worktree_list_failure_returns_nonzero(self):
        root, task_dir = self._make_root()
        orig_list = ws._git_worktree_list_porcelain
        ws._git_worktree_list_porcelain = lambda r: ("", "not a git repo")
        try:
            rc = ws.main(["--root", str(root)])
        finally:
            ws._git_worktree_list_porcelain = orig_list
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
