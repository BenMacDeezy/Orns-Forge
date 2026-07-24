"""Doc-pin regression tests for task cold-cache-dispatch-warning: the new
"Idle-wait discipline — cold-cache dispatch note — 2026-07-20" conventions
section (docs/conventions/verification.md) and its TOC/manifest entries in
docs/conventions.md. Follows the tools/doc_pins/ sharded-module pattern
(fg-a11040): one module per task-id prefix so concurrent tasks appending
pins land in separate files instead of conflicting at a shared tail.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
)


class TestColdCacheDispatchWarningPins(unittest.TestCase):
    """Doc-pin regression tests for cold-cache-dispatch-warning: the new
    dated amendment section noting cold-prompt-cache cost visibility for
    kernel dispatches that follow a >5-minute session idle gap."""

    def _corpus(self):
        return _read_path(REPO_ROOT / "docs" / "conventions.md")

    def test_cold_cache_section_heading_present_in_corpus(self):
        content = self._corpus()
        self.assertIn(
            "## Idle-wait discipline — cold-cache dispatch note — 2026-07-20",
            content,
        )

    def test_cold_cache_section_amends_idle_wait_discipline(self):
        content = self._corpus()
        self.assertIn(
            '> Amends: "Idle-wait discipline — 2026-07" (above).',
            content,
        )

    def test_cold_cache_ears_clause_documented(self):
        content = self._corpus()
        self.assertIn(
            "WHEN a kernel dispatch follows more than 5 minutes of session "
            "idle (no tool\nactivity), THE SYSTEM SHALL add one line to "
            "the session report naming the\nidle-gap length and the "
            "dispatch it preceded.",
            content,
        )

    def test_cold_cache_visibility_only_never_blocking_documented(self):
        content = self._corpus()
        self.assertIn(
            "This is visibility only: the\nnote never blocks the dispatch, "
            "and it never triggers auto-rescheduling.",
            content,
        )

    def test_cold_cache_no_v1_threshold_config_documented(self):
        content = self._corpus()
        self.assertIn(
            "No\nthreshold configuration ships in v1 — the 5-minute figure "
            "is fixed, not a\n`.forge/forge.md` override key",
            content,
        )

    def test_cold_cache_cites_jcode_pattern_promotion(self):
        content = self._corpus()
        self.assertIn(
            "Promoted from the jcode pattern (fg-a10702 steal-list, "
            "2026-07-20)",
            content,
        )

    def test_cold_cache_composes_with_watchdog_by_citation_not_restatement(self):
        content = self._corpus()
        self.assertIn(
            "**Composition with the watchdog fallback wakeup.** This note "
            "does not\nrestate \"Idle-wait discipline — watchdog amendment "
            "— 2026-07-20\"'s\nfallback-wakeup sentence (above) — cited, "
            "not repeated:",
            content,
        )

    def test_cold_cache_toc_entry_nested_under_idle_wait_discipline(self):
        content = self._corpus()
        self.assertIn(
            "- Idle-wait discipline — 2026-07\n"
            "  - Idle-wait discipline — watchdog amendment — 2026-07-20\n"
            "  - Idle-wait discipline — cold-cache dispatch note — "
            "2026-07-20\n"
            "- Watchdog thresholds — 2026-07-20",
            content,
        )

    def test_cold_cache_manifest_entry_present(self):
        content = self._corpus()
        self.assertIn(
            "- `Idle-wait discipline — cold-cache dispatch note — "
            "2026-07-20` -> `docs/conventions/verification.md`",
            content,
        )

    def test_original_idle_wait_discipline_bullets_unchanged(self):
        """Zero-rewrite property spot-check: the original NORMATIVE bullets
        still read exactly as before this amendment (same discipline as the
        fg-a10211 watchdog pin's equivalent check)."""
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

    def test_watchdog_amendment_body_unchanged(self):
        """The sibling watchdog amendment section this task cites/composes
        with must remain untouched (append-only discipline)."""
        content = self._corpus()
        self.assertIn(
            "## Idle-wait discipline — watchdog amendment — 2026-07-20\n"
            "\n"
            '> Amends: "Idle-wait discipline — 2026-07" (above).\n'
            "\n"
            "On the one long fallback wakeup the discipline above allows, "
            "the kernel\n"
            "runs `tools/watchdog.py` for that turn and acts only on the "
            "flags it\n"
            "prints",
            content,
        )


if __name__ == "__main__":
    unittest.main()
