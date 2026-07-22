"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10211`: TestFgA10211WatchdogPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
    _CONVENTIONS_PATH_RESOLVED,
    _WORD_TO_INT,
    validate_task,
    shard_task,
    conventions_corpus,
)


class TestFgA10211WatchdogPins(unittest.TestCase):
    """Doc-pin regression tests for fg-a10211 (watchdog): the new "Watchdog
    thresholds — 2026-07-20" conventions section and its one-sentence
    amendment to "Idle-wait discipline — 2026-07"."""

    def _corpus(self):
        return _read_path(REPO_ROOT / "docs" / "conventions.md")

    def test_watchdog_thresholds_heading_present_in_corpus(self):
        content = self._corpus()
        self.assertIn("## Watchdog thresholds — 2026-07-20", content)

    def test_watchdog_thresholds_toc_entry_present(self):
        content = self._corpus()
        self.assertIn("- Watchdog thresholds — 2026-07-20", content)
        self.assertIn(
            "  - Idle-wait discipline — watchdog amendment — 2026-07-20",
            content,
        )

    def test_watchdog_thresholds_defaults_documented(self):
        content = self._corpus()
        self.assertIn("| HUNG | worker transcript file has not grown for | 10 minutes |", content)
        self.assertIn("| RUNAWAY | transcript byte budget | 2 MB |", content)
        self.assertIn(
            "| RUNAWAY | identical command repeated in the tail | 5 times |",
            content,
        )
        self.assertIn(
            "| STALE-CLAIM | claimed-by age with no new Attempt-log line | 4 hours |",
            content,
        )
        self.assertIn(
            "| DUPLICATE-TASK | normalized-title similarity "
            "(`difflib.SequenceMatcher`) | 0.85 |",
            content,
        )
        self.assertIn("| ATTEMPT-CAP | attempts past the bounce cap | 3 |", content)

    def test_watchdog_thresholds_features_override_documented(self):
        content = self._corpus()
        self.assertIn(
            "Every threshold above is overridable per-project via\n"
            "`.forge/forge.md`'s `## Features` section, as "
            "`watchdog-<name>: <value>`\nbullet lines",
            content,
        )

    def test_watchdog_check_report_scope_documented(self):
        content = self._corpus()
        self.assertIn(
            "`tools/watchdog.py --check-report` reads a worker\n"
            "RETURN report on stdin and mechanically verifies checkable "
            "claims only",
            content,
        )
        self.assertIn(
            "Prose-quality judgment (is the\nsummary accurate, is the fix "
            "actually right) stays with verifiers; this\nmode never "
            "attempts it.",
            content,
        )

    def test_idle_wait_discipline_amendment_sentence_present(self):
        """The one-sentence amendment lives in a new, separately-headed
        amendment section (never a rewrite of the existing Idle-wait
        discipline body -- docs/conventions/verification.md's R1 shard
        conservation gate forbids editing a base-existing section's body in
        place, so this follows the repo's established amendment pattern:
        a new heading with an "Amends:" pointer, e.g. "Sharded fan-out —
        per-shard write surfaces amendment (2026-07-19, fg-b0401)")."""
        content = self._corpus()
        self.assertIn(
            "## Idle-wait discipline — watchdog amendment — 2026-07-20",
            content,
        )
        self.assertIn(
            '> Amends: "Idle-wait discipline — 2026-07" (above).',
            content,
        )
        self.assertIn(
            "On the one long fallback wakeup the discipline above allows, "
            "the kernel\n"
            "runs `tools/watchdog.py` for that turn and acts only on the "
            "flags it\n"
            "prints (see \"Watchdog thresholds — 2026-07-20\", below)",
            content,
        )

    def test_idle_wait_discipline_original_bullets_unchanged(self):
        """Zero-rewrite property spot-check: the original NORMATIVE bullets
        still read exactly as before the amendment."""
        content = self._corpus()
        self.assertIn(
            "- WHILE background dispatches are in flight and nothing is "
            "actionable, the\n"
            "  kernel waits for completion notifications rather than "
            "checking in on its\n"
            "  own initiative.",
            content,
        )
        self.assertIn(
            "- An unrelated hook fire or stray wakeup that lands with no "
            "new notification\n"
            "  attached ends the turn as a no-op — at most one short "
            "status line, no\n"
            "  worker-output reads, no re-derivation of state already "
            "known from the\n"
            "  last real notification.",
            content,
        )
