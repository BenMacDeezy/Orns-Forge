"""Tests for tools/status.py (fg-a10214): the script-only /forge:status fast
path. Renders the canonical board defined in
skills/queue/references/status-board.md without any LLM/skill involvement.

Board-parity tests run against the static fixture queue checked in at
tools/fixtures/status/basic/ (--root points the script's importable
functions at it directly, per the task contract's "temp-copy or point the
script at a --root"). Every board test passes an explicit `now` so results
never depend on wall-clock time, even though the fixture's own dates are
fixed calendar dates.

Version-skew / malformed-frontmatter / empty-queue edge cases build their
own throwaway temp dirs, since those scenarios are either time-relative or
need a shape the shared fixture doesn't cover.
"""
import datetime as dt
import json
import pathlib
import tempfile
import unittest

import status

FIXTURE_ROOT = pathlib.Path(__file__).resolve().parent / "fixtures" / "status" / "basic"
FIXTURE_TASK_DIR = FIXTURE_ROOT / ".forge" / "queue" / "tasks"
FIXTURE_FORGE_MD = FIXTURE_ROOT / ".forge" / "forge.md"

NOW = dt.datetime(2026, 7, 19, 0, 0, 0, tzinfo=dt.timezone.utc)


class BlockedFirstTests(unittest.TestCase):
    def setUp(self):
        self.tasks, self.skipped = status.load_tasks(FIXTURE_TASK_DIR)

    def test_blocked_state_task_shows_with_outcome_note(self):
        lines = status.build_blocked_section(self.tasks)
        joined = "\n".join(lines)
        self.assertIn("fg-b100", joined)
        self.assertIn(
            "Waiting on partner API credentials from vendor.", joined
        )

    def test_ready_task_blocked_by_dropped_id_is_flagged(self):
        lines = status.build_blocked_section(self.tasks)
        joined = "\n".join(lines)
        self.assertIn("fg-a001", joined)
        self.assertIn("fg-b1c1", joined)
        self.assertIn("dropped", joined)

    def test_ready_task_blocked_by_missing_id_is_flagged(self):
        lines = status.build_blocked_section(self.tasks)
        joined = "\n".join(lines)
        self.assertIn("fg-a002", joined)
        self.assertIn("fg-dead", joined)
        self.assertIn("missing", joined)

    def test_ready_task_blocked_by_normal_ready_task_is_not_flagged(self):
        lines = status.build_blocked_section(self.tasks)
        joined = "\n".join(lines)
        self.assertNotIn("fg-a003", joined)

    def test_normal_ready_task_never_appears_in_blocked_section(self):
        lines = status.build_blocked_section(self.tasks)
        joined = "\n".join(lines)
        self.assertNotIn("fg-a005", joined)


class BoardScopeTests(unittest.TestCase):
    def setUp(self):
        self.tasks, self.skipped = status.load_tasks(FIXTURE_TASK_DIR)

    @staticmethod
    def _row_ids(lines):
        """Row ids only -- the leading `| fg-xxxx |` cell of each table row.
        Deliberately NOT a substring check over the whole joined text: a
        dropped task's id legitimately appears in another row's blocked-by
        cell (e.g. fg-a001 is blocked-by the dropped fg-b1c1), which must
        not be confused with the dropped task having its own row."""
        return [l.split("|")[1].strip() for l in lines if l.startswith("| fg-")]

    def test_default_scope_excludes_done_and_dropped_and_caps_at_15(self):
        lines = status.build_board_section(self.tasks, None)
        joined = "\n".join(lines)
        row_ids = self._row_ids(lines)
        self.assertEqual(len(row_ids), 15)
        self.assertNotIn("fg-d001", row_ids)
        self.assertNotIn("fg-d002", row_ids)
        self.assertNotIn("fg-b1c1", row_ids)  # the fixture's one dropped task
        self.assertIn(
            "2 more not shown — run `/forge:status all` to see everything "
            "(or `/forge:status <state>` to filter).",
            joined,
        )

    def test_all_scope_is_uncapped_and_excludes_done_and_dropped(self):
        lines = status.build_board_section(self.tasks, "all")
        joined = "\n".join(lines)
        row_ids = self._row_ids(lines)
        self.assertEqual(len(row_ids), 17)
        self.assertNotIn("fg-d001", row_ids)
        self.assertNotIn("fg-d002", row_ids)
        self.assertNotIn("fg-b1c1", row_ids)  # dropped stays hidden under `all` too
        self.assertNotIn("more not shown", joined)

    def test_state_scope_shows_only_that_state_including_done(self):
        lines = status.build_board_section(self.tasks, "done")
        joined = "\n".join(lines)
        self.assertIn("fg-d001", joined)
        self.assertIn("fg-d002", joined)
        row_lines = [l for l in lines if l.startswith("| fg-")]
        self.assertEqual(len(row_lines), 2)
        self.assertNotIn("more not shown", joined)

    def test_state_scope_dropped_is_the_only_way_to_see_it(self):
        lines = status.build_board_section(self.tasks, "dropped")
        joined = "\n".join(lines)
        self.assertIn("fg-b1c1", joined)
        row_lines = [l for l in lines if l.startswith("| fg-")]
        self.assertEqual(len(row_lines), 1)
        self.assertNotIn("more not shown", joined)

    def test_state_scope_backlog_shows_all_six_backlog_tasks(self):
        lines = status.build_board_section(self.tasks, "backlog")
        row_lines = [l for l in lines if l.startswith("| fg-")]
        self.assertEqual(len(row_lines), 6)

    def test_state_scope_with_no_matches_says_so_not_empty_table(self):
        lines = status.build_board_section(self.tasks, "dropped")
        # fg-b1c1 is the only dropped task in the fixture -- pick a state
        # that genuinely has zero rows instead.
        empty_tasks = {
            k: v for k, v in self.tasks.items() if v["state"] != "dropped"
        }
        lines = status.build_board_section(empty_tasks, "dropped")
        joined = "\n".join(lines)
        self.assertNotIn("| fg-", joined)
        self.assertIn("No tasks in state `dropped`", joined)


class OrderingTests(unittest.TestCase):
    def test_priority_ascending_then_created_ascending(self):
        tasks, _ = status.load_tasks(FIXTURE_TASK_DIR)
        lines = status.build_board_section(tasks, "all")
        row_ids = [l.split("|")[1].strip() for l in lines if l.startswith("| fg-")]
        pos_0e03 = row_ids.index("fg-0e03")  # priority 1, created 07-02
        pos_0e02 = row_ids.index("fg-0e02")  # priority 1, created 07-15
        pos_0e01 = row_ids.index("fg-0e01")  # priority 2, created 07-01
        self.assertLess(pos_0e03, pos_0e02)
        self.assertLess(pos_0e02, pos_0e01)


class BacklogNeedsInfoTests(unittest.TestCase):
    def setUp(self):
        self.tasks, _ = status.load_tasks(FIXTURE_TASK_DIR)

    def test_outcome_note_shown_verbatim(self):
        lines = status.build_backlog_section(self.tasks, NOW)
        joined = "\n".join(lines)
        self.assertIn("fg-bac1", joined)
        self.assertIn(
            "Needs decision on rate-limit budget before scoping.", joined
        )

    def test_attempt_log_fallback_when_outcome_is_pending(self):
        lines = status.build_backlog_section(self.tasks, NOW)
        joined = "\n".join(lines)
        self.assertIn("fg-bac2", joined)
        self.assertIn(
            "Blocked on stakeholder answer re: retention window.", joined
        )

    def test_stale_backlog_flagged_without_note(self):
        lines = status.build_backlog_section(self.tasks, NOW)
        joined = "\n".join(lines)
        self.assertIn("fg-bac3", joined)
        self.assertIn("[stale-backlog]", joined)

    def test_stale_and_needs_info_both_shown(self):
        lines = status.build_backlog_section(self.tasks, NOW)
        bac4_line = next(l for l in lines if "fg-bac4" in l)
        self.assertIn("[stale-backlog]", bac4_line)
        self.assertIn("Needs pricing confirmation from vendor.", bac4_line)

    def test_task_with_no_note_and_not_stale_is_omitted(self):
        lines = status.build_backlog_section(self.tasks, NOW)
        joined = "\n".join(lines)
        self.assertNotIn("fg-bac5", joined)

    def test_none_marker_attempt_log_is_a_placeholder_not_a_note(self):
        """fg-bac6's Attempt log is literally '(none)' -- the real-world
        empty-Attempt-log marker used by 5 live task files in this repo's
        own queue (and by tools/telemetry.py). It must be treated as a
        placeholder, exactly like '(pending)', not surfaced as a real
        needs-info note."""
        lines = status.build_backlog_section(self.tasks, NOW)
        joined = "\n".join(lines)
        self.assertNotIn("fg-bac6", joined)
        self.assertNotIn("(none)", joined)


class StaleClaimsTests(unittest.TestCase):
    def setUp(self):
        self.tasks, _ = status.load_tasks(FIXTURE_TASK_DIR)
        self.threshold = status.load_claim_staleness_hours(FIXTURE_FORGE_MD)

    def test_claim_staleness_hours_read_from_forge_md(self):
        self.assertEqual(self.threshold, 0.5)

    def test_old_claim_flagged_stale(self):
        lines = status.build_stale_claims_section(self.tasks, NOW, self.threshold)
        joined = "\n".join(lines)
        self.assertIn("fg-ac71", joined)

    def test_fresh_claim_not_flagged(self):
        lines = status.build_stale_claims_section(self.tasks, NOW, self.threshold)
        joined = "\n".join(lines)
        self.assertNotIn("fg-ac72", joined)


class MalformedFrontmatterTests(unittest.TestCase):
    def test_malformed_files_are_skipped_not_crashed(self):
        tasks, skipped = status.load_tasks(FIXTURE_TASK_DIR)
        self.assertNotIn("fg-bad1", tasks)
        self.assertEqual(len(skipped), 2)

    def test_render_board_never_raises_and_notes_skip_count(self):
        text = status.render_board(FIXTURE_TASK_DIR, FIXTURE_FORGE_MD, scope="all", now=NOW)
        self.assertIn("2", text)  # 2 malformed files skipped, noted somewhere


class MissingOrEmptyQueueTests(unittest.TestCase):
    def test_missing_task_dir_is_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_dir = pathlib.Path(tmp) / ".forge" / "queue" / "tasks"
            text = status.render_board(missing_dir, pathlib.Path(tmp) / ".forge" / "forge.md",
                                        scope=None, now=NOW)
            self.assertEqual(len(text.strip().splitlines()), 1)

    def test_empty_task_dir_is_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_dir = pathlib.Path(tmp) / ".forge" / "queue" / "tasks"
            empty_dir.mkdir(parents=True)
            text = status.render_board(empty_dir, pathlib.Path(tmp) / ".forge" / "forge.md",
                                        scope=None, now=NOW)
            self.assertEqual(len(text.strip().splitlines()), 1)


class VersionSkewResolutionTests(unittest.TestCase):
    def _write_installed_plugins(self, tmp, plugins):
        path = pathlib.Path(tmp) / "installed_plugins.json"
        path.write_text(json.dumps({"version": 2, "plugins": plugins}), encoding="utf-8")
        return path

    def test_prefers_forge_at_orns_forge_over_other_forge_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "forge@some-other-marketplace": [
                    {"installPath": "C:\\x\\forge\\9.9.9", "version": "9.9.9"}
                ],
                "forge@orns-forge": [
                    {"installPath": "C:\\x\\forge\\1.2.3", "version": "1.2.3"}
                ],
            })
            version = status.resolve_installed_version(path)
            self.assertEqual(version, (1, 2, 3))

    def test_falls_back_to_any_forge_prefixed_key_when_orns_forge_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "forge@forge-local": [
                    {"installPath": "C:\\x\\forge\\2.0.0", "version": "2.0.0"}
                ],
            })
            version = status.resolve_installed_version(path)
            self.assertEqual(version, (2, 0, 0))

    def test_no_forge_key_at_all_resolves_to_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "vercel@claude-plugins-official": [
                    {"installPath": "C:\\x\\vercel\\1.0.0", "version": "1.0.0"}
                ],
            })
            version = status.resolve_installed_version(path)
            self.assertIsNone(version)

    def test_dev_path_plugin_root_has_no_version_segment_stays_silent(self):
        loaded = status.resolve_loaded_version("D:\\forge")
        self.assertIsNone(loaded)

    def test_nudge_emitted_when_installed_newer_than_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "forge@orns-forge": [
                    {"installPath": "C:\\x\\forge\\0.13.0", "version": "0.13.0"}
                ],
            })
            nudge = status.version_skew_nudge(
                "C:\\x\\forge\\0.12.0", path
            )
            self.assertIsNotNone(nudge)
            self.assertIn("0.13.0", nudge)
            self.assertIn("0.12.0", nudge)

    def test_no_nudge_when_versions_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "forge@orns-forge": [
                    {"installPath": "C:\\x\\forge\\0.12.0", "version": "0.12.0"}
                ],
            })
            nudge = status.version_skew_nudge("C:\\x\\forge\\0.12.0", path)
            self.assertIsNone(nudge)

    def test_no_nudge_for_dev_path_even_if_installed_is_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_installed_plugins(tmp, {
                "forge@orns-forge": [
                    {"installPath": "C:\\x\\forge\\9.9.9", "version": "9.9.9"}
                ],
            })
            nudge = status.version_skew_nudge("D:\\forge", path)
            self.assertIsNone(nudge)

    def test_unreadable_installed_plugins_file_is_silent(self):
        nudge = status.version_skew_nudge(
            "C:\\x\\forge\\0.12.0", "C:\\does\\not\\exist.json"
        )
        self.assertIsNone(nudge)


class TimingTests(unittest.TestCase):
    def test_render_board_is_fast_on_real_repo_queue(self):
        import time
        real_root = pathlib.Path(__file__).resolve().parents[1]
        real_task_dir = real_root / ".forge" / "queue" / "tasks"
        real_forge_md = real_root / ".forge" / "forge.md"
        if not real_task_dir.is_dir():
            self.skipTest("no real .forge/queue/tasks present")
        start = time.monotonic()
        status.render_board(real_task_dir, real_forge_md, scope="all")
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
