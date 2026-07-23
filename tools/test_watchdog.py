"""Tests for tools/watchdog.py (fg-a10211): script-only, zero-token-when-
healthy detection of hung workers, runaway agents, stale claims, duplicate
tasks, and attempt-cap breaches, plus --check-report's mechanical
worker-report verification.

Every test builds its own throwaway fixture task dir (tempfile.TemporaryDirectory)
with fake transcript files under controlled mtimes/sizes, and passes an
explicit `now` so results never depend on wall-clock time. One test class per
flag class (HUNG, RUNAWAY x2, STALE-CLAIM, DUPLICATE-TASK, ATTEMPT-CAP), plus
report-mismatch true/false cases and the healthy-run-prints-nothing pin.
"""
import contextlib
import io
import os
import pathlib
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

import watchdog

NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
NOW_ISO = "2026-07-20T12:00:00Z"


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_task(tasks_dir, task_id, title, state="active", claimed_by="null",
                 attempt_log="(pending)"):
    text = (
        "---\n"
        f"id: {task_id}\n"
        f"title: \"{title}\"\n"
        f"state: {state}\n"
        "tier: standard\n"
        "priority: 2\n"
        "spec: null\n"
        "blocks: []\n"
        "blocked-by: []\n"
        f"claimed-by: {claimed_by}\n"
        "parallel-safe: false\n"
        "created: 2026-07-18T11:00:00Z\n"
        "updated: 2026-07-18T11:00:00Z\n"
        "schema-version: 1\n"
        "---\n\n"
        "## Acceptance criteria\nSomething.\n\n"
        "## Execution plan\nSomething.\n\n"
        "## Routing record\n(pending)\n\n"
        "## Attempt log\n"
        f"{attempt_log}\n\n"
        "## Outcome\n(pending)\n"
    )
    (pathlib.Path(tasks_dir) / f"{task_id}.md").write_text(text, encoding="utf-8")


class HealthyRunPrintsNothingTests(unittest.TestCase):
    """Pin: a fully healthy queue + task-dir produces zero output, exit 0."""

    def test_healthy_run_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_dir = pathlib.Path(tmp) / ".forge"
            tasks_dir = forge_dir / "queue" / "tasks"
            tasks_dir.mkdir(parents=True)
            task_dir = pathlib.Path(tmp) / "task-output"
            task_dir.mkdir()

            _write_task(
                tasks_dir, "fg-h001", "Add widget support", state="active",
                claimed_by=f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
                attempt_log=f"attempt 1: dispatched {_iso(NOW - timedelta(hours=1))}",
            )
            transcript = task_dir / "fg-h001.transcript"
            transcript.write_text("$ pytest\nok\n", encoding="utf-8")
            recent = (NOW - timedelta(minutes=1)).timestamp()
            os.utime(transcript, (recent, recent))

            _write_task(tasks_dir, "fg-h002", "Refactor the parser module", state="ready")

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = watchdog.main([
                    "--forge-dir", str(forge_dir),
                    "--task-dir", str(task_dir),
                    "--now", NOW_ISO,
                ])
            self.assertEqual(rc, 0)
            self.assertEqual(buf.getvalue(), "")


class HungTests(unittest.TestCase):
    def test_stale_transcript_flags_hung(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-h100.transcript"
            transcript.write_text("$ pytest\n", encoding="utf-8")
            old = (NOW - timedelta(minutes=30)).timestamp()
            os.utime(transcript, (old, old))
            tasks = [{
                "id": "fg-h100", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_hung(tasks, task_dir, NOW, 10.0)
            self.assertEqual(len(flags), 1)
            self.assertTrue(flags[0].startswith("HUNG fg-h100:"))
            self.assertIn("30.0m", flags[0])
            self.assertIn(">= 10.0m", flags[0])

    def test_recently_grown_transcript_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-h101.transcript"
            transcript.write_text("$ pytest\n", encoding="utf-8")
            recent = (NOW - timedelta(minutes=1)).timestamp()
            os.utime(transcript, (recent, recent))
            tasks = [{
                "id": "fg-h101", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_hung(tasks, task_dir, NOW, 10.0)
            self.assertEqual(flags, [])

    def test_unclaimed_task_never_flagged_even_with_stale_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-h102.transcript"
            transcript.write_text("$ pytest\n", encoding="utf-8")
            old = (NOW - timedelta(hours=2)).timestamp()
            os.utime(transcript, (old, old))
            tasks = [{"id": "fg-h102", "state": "ready", "claimed_by": "null"}]
            flags = watchdog.check_hung(tasks, task_dir, NOW, 10.0)
            self.assertEqual(flags, [])


class RunawayByteBudgetTests(unittest.TestCase):
    def test_oversized_transcript_flags_runaway(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-r200.transcript"
            transcript.write_text("x" * 200, encoding="utf-8")
            tasks = [{
                "id": "fg-r200", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_runaway(tasks, task_dir, 100, 5)
            self.assertEqual(len(flags), 1)
            self.assertTrue(flags[0].startswith("RUNAWAY fg-r200:"))
            self.assertIn("200B", flags[0])
            self.assertIn("> 100B", flags[0])

    def test_undersized_transcript_not_flagged_on_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-r201.transcript"
            transcript.write_text("x" * 50, encoding="utf-8")
            tasks = [{
                "id": "fg-r201", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_runaway(tasks, task_dir, 100, 5)
            self.assertEqual(flags, [])


class RunawayRepeatTests(unittest.TestCase):
    def test_repeated_identical_command_flags_runaway(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-r210.transcript"
            lines = ["$ npm test\nfail\n"] * 6
            transcript.write_text("".join(lines), encoding="utf-8")
            tasks = [{
                "id": "fg-r210", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_runaway(tasks, task_dir, 10 * 1024 * 1024, 5)
            self.assertEqual(len(flags), 1)
            self.assertTrue(flags[0].startswith("RUNAWAY fg-r210:"))
            self.assertIn("x6", flags[0])
            self.assertIn(">= 5", flags[0])

    def test_varied_commands_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = pathlib.Path(tmp)
            transcript = task_dir / "fg-r211.transcript"
            transcript.write_text(
                "$ npm test\nok\n$ npm build\nok\n$ npm lint\nok\n",
                encoding="utf-8",
            )
            tasks = [{
                "id": "fg-r211", "state": "active",
                "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            }]
            flags = watchdog.check_runaway(tasks, task_dir, 10 * 1024 * 1024, 5)
            self.assertEqual(flags, [])


class StaleClaimTests(unittest.TestCase):
    def test_old_claim_with_no_attempt_log_activity_flags_stale_claim(self):
        tasks = [{
            "id": "fg-s300", "state": "active",
            "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=6))}",
            "body": "## Attempt log\n(pending)\n",
        }]
        flags = watchdog.check_stale_claim(tasks, NOW, 4.0)
        self.assertEqual(len(flags), 1)
        self.assertTrue(flags[0].startswith("STALE-CLAIM fg-s300:"))
        self.assertIn("6.0h", flags[0])
        self.assertIn(">= 4.0h", flags[0])

    def test_old_claim_with_recent_attempt_log_activity_not_flagged(self):
        tasks = [{
            "id": "fg-s301", "state": "active",
            "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=6))}",
            "body": (
                "## Attempt log\n"
                f"attempt 1: dispatched {_iso(NOW - timedelta(hours=1))}\n"
            ),
        }]
        flags = watchdog.check_stale_claim(tasks, NOW, 4.0)
        self.assertEqual(flags, [])

    def test_recent_claim_not_flagged_regardless_of_attempt_log(self):
        tasks = [{
            "id": "fg-s302", "state": "active",
            "claimed_by": f"sess-ab12 @ {_iso(NOW - timedelta(hours=1))}",
            "body": "## Attempt log\n(pending)\n",
        }]
        flags = watchdog.check_stale_claim(tasks, NOW, 4.0)
        self.assertEqual(flags, [])


class DuplicateTaskTests(unittest.TestCase):
    def test_near_identical_titles_flag_duplicate(self):
        tasks = [
            {"id": "fg-d400", "title": "Add retry logic to the fetch client", "state": "ready"},
            {"id": "fg-d401", "title": "Add retry logic to the fetch client!", "state": "backlog"},
        ]
        flags = watchdog.check_duplicates(tasks, 0.85)
        self.assertEqual(len(flags), 1)
        self.assertTrue(flags[0].startswith("DUPLICATE-TASK fg-d400/fg-d401:"))
        self.assertIn(">= 0.85", flags[0])

    def test_distinct_titles_not_flagged(self):
        tasks = [
            {"id": "fg-d402", "title": "Add retry logic to the fetch client", "state": "ready"},
            {"id": "fg-d403", "title": "Rewrite the onboarding docs", "state": "backlog"},
        ]
        flags = watchdog.check_duplicates(tasks, 0.85)
        self.assertEqual(flags, [])

    def test_done_task_excluded_from_duplicate_check(self):
        tasks = [
            {"id": "fg-d404", "title": "Add retry logic to the fetch client", "state": "ready"},
            {"id": "fg-d405", "title": "Add retry logic to the fetch client", "state": "done"},
        ]
        flags = watchdog.check_duplicates(tasks, 0.85)
        self.assertEqual(flags, [])


class AttemptCapTests(unittest.TestCase):
    def test_attempt_past_cap_flags_attempt_cap(self):
        tasks = [{
            "id": "fg-a500",
            "body": (
                "## Attempt log\n"
                "attempt 1: dispatched 2026-07-18T10:00:00Z\n"
                "attempt 2: FAIL (bounce, standard): re-verify\n"
                "attempt 3: FAIL (bounce, standard): re-verify\n"
                "attempt 4: dispatched 2026-07-19T10:00:00Z\n"
            ),
        }]
        flags = watchdog.check_attempt_cap(tasks, 3)
        self.assertEqual(len(flags), 1)
        self.assertTrue(flags[0].startswith("ATTEMPT-CAP fg-a500:"))
        self.assertIn("attempt 4", flags[0])
        self.assertIn("> 3", flags[0])

    def test_attempt_within_cap_not_flagged(self):
        tasks = [{
            "id": "fg-a501",
            "body": "## Attempt log\nattempt 1: dispatched 2026-07-18T10:00:00Z\n",
        }]
        flags = watchdog.check_attempt_cap(tasks, 3)
        self.assertEqual(flags, [])


class ThresholdOverrideTests(unittest.TestCase):
    def test_features_section_override_changes_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            forge_md = pathlib.Path(tmp) / "forge.md"
            forge_md.write_text(
                "# Forge config\n\n"
                "## Features\n"
                "- watchdog-hung-minutes: 45\n"
                "- watchdog-attempt-cap: 5\n",
                encoding="utf-8",
            )
            thresholds = watchdog.load_thresholds(forge_md)
            self.assertEqual(thresholds["hung-minutes"], 45)
            self.assertEqual(thresholds["attempt-cap"], 5)
            # unspecified keys keep the canonical default
            self.assertEqual(thresholds["title-similarity"], 0.85)

    def test_missing_forge_md_keeps_all_defaults(self):
        thresholds = watchdog.load_thresholds(pathlib.Path("/no/such/forge.md"))
        self.assertEqual(thresholds, watchdog.DEFAULTS)


class CheckReportMismatchTrueTests(unittest.TestCase):
    """--check-report: mismatch cases (REPORT-MISMATCH lines expected)."""

    def test_missing_claimed_file_flags_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = (
                "RESULT: completed\n"
                "SUMMARY: did the thing.\n"
                "FILES CHANGED:\n"
                "- tools/does_not_exist.py: added the thing\n"
                "GATES: python -m pytest tools/ -q -> pass (10 passed)\n"
            )
            flags = watchdog.check_report(report, tmp)
            self.assertEqual(len(flags), 1)
            self.assertIn("REPORT-MISMATCH file:", flags[0])
            self.assertIn("tools/does_not_exist.py", flags[0])

    def test_test_count_mismatch_against_gate_output_flags(self):
        report = (
            "RESULT: completed\n"
            "FILES CHANGED:\n"
            "- (none)\n"
            "GATES: python -m pytest tools/ -q -> 42 passed\n"
        )
        gate_output = "................................ \n40 passed in 1.23s\n"
        flags = watchdog.check_report(report, ".", gate_output_text=gate_output)
        mismatches = [f for f in flags if "test-count" in f]
        self.assertEqual(len(mismatches), 1)
        self.assertIn("claimed 42 passed", mismatches[0])
        self.assertIn("actual gate output shows 40 passed", mismatches[0])


class CheckReportMismatchFalseTests(unittest.TestCase):
    """--check-report: healthy report (no REPORT-MISMATCH lines expected)."""

    def test_all_claimed_files_exist_and_counts_match_no_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_file = pathlib.Path(tmp) / "tools" / "real_thing.py"
            real_file.parent.mkdir(parents=True)
            real_file.write_text("# real\n", encoding="utf-8")
            report = (
                "RESULT: completed\n"
                "FILES CHANGED:\n"
                "- tools/real_thing.py: added the thing\n"
                "GATES: python -m pytest tools/ -q -> 40 passed\n"
            )
            gate_output = "40 passed in 1.23s\n"
            flags = watchdog.check_report(report, tmp, gate_output_text=gate_output)
            self.assertEqual(flags, [])

    def test_no_gate_output_supplied_skips_count_check(self):
        report = "RESULT: completed\nFILES CHANGED:\n- (none)\nGATES: 42 passed\n"
        flags = watchdog.check_report(report, ".")
        self.assertEqual(flags, [])


if __name__ == "__main__":
    unittest.main()
