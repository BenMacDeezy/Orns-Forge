"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10208`: TestFgA10208IdleWaitPins.
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


class TestFgA10208IdleWaitPins(unittest.TestCase):
    """Doc-pins for fg-a10208 (idle-wait discipline): the canonical dated
    conventions section (heading + TOC line), its never-polls and no-op-turn
    NORMATIVE bullets, the single-scheduled-fallback-wakeup clause, and the
    kernel's one citing sentence in ROUTE + DISPATCH naming the section by
    exact name.

    The kernel char-ceiling pin already exists
    (TestFgA10201VerifierFindingFilterPins.test_kernel_skill_within_char_ceiling)
    and is intentionally not duplicated here — this task's own trim-to-fit
    work is covered by that pre-existing assertion staying green.
    """

    SECTION_HEADING = "## Idle-wait discipline — 2026-07"

    def test_conventions_has_section_heading(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_section_in_toc(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("- Idle-wait discipline — 2026-07", content)

    def test_conventions_section_has_never_polls_sentence(self):
        """Pins the exact no-polling-worker-transcripts clause, including
        the literal substring "never polls" the task contract requires."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("never polls", normalized)
        self.assertIn(
            "The kernel never polls worker transcripts turn-by-turn",
            normalized,
        )

    def test_conventions_section_has_no_op_turn_sentence(self):
        """Pins the no-op-turn behavior for a stray wakeup/hook fire that
        carries no new notification: at most one status line, no
        worker-output reads."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "ends the turn as a no-op — at most one short status line, no",
            normalized,
        )
        self.assertIn("worker-output reads", normalized)

    def test_conventions_section_has_fallback_wakeup_clause(self):
        """Pins the single-scheduled-fallback-wakeup clause (>= 20 minutes,
        harness-permitting) so a future edit can't quietly drop the hang
        safety net or loosen it into a recurring poll."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("At most ONE long fallback wakeup", normalized)
        self.assertIn(">= 20 minutes, harness-permitting", normalized)

    def test_conventions_section_names_mem_9b31c5_lineage(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("mem-9b31c5", section)

    def test_kernel_cites_idle_wait_section_by_exact_name(self):
        """Pins the kernel's one citing sentence in ROUTE + DISPATCH, naming
        the conventions section by exact heading text."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Idle-wait discipline — 2026-07"',
            normalized,
        )

    def test_kernel_dispatch_counting_cites_budget_keys_amendment(self):
        """Pins fg-a10208's restored pointer on the Dispatch counting
        paragraph (ROUTE + DISPATCH, step 5): the count-is-portable /
        budget-guard-is-a-backstop-only distinction, and the exact-name
        citation of the conventions section it lives in. Bounce fix for a
        verifier finding that a prior trim deleted this distinction with no
        replacement (mem-e4a917)."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("budget-guard", normalized)
        self.assertIn(
            '`docs/conventions.md`, "Budget keys — amendment (2026-07-17)"',
            normalized,
        )
