"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10701`: TestFgA10701DebugEscalationPins.
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


class TestFgA10701DebugEscalationPins(unittest.TestCase):
    """Covers fg-a10701's EARS clauses (constitution rule 3): the
    clean-context debug escalation — one auto-dispatched Hex attempt in a
    FRESH context between the 2nd verifier FAIL and the double-bounce
    block, routed through normal (delta-scoped) re-verification, capped at
    exactly one extra attempt — is pinned across docs/conventions.md and
    skills/kernel/SKILL.md so a future edit cannot silently drop the cap,
    the fresh-context requirement, the re-verify routing, or the kernel
    citation.
    """

    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 3: dated section, canonical home for the rule.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Clean-context debug escalation — 2026-07-18 (fg-a10701)", c
        )

    def test_toc_lists_the_new_section(self):
        # The TOC pin test enforces heading==entry; this is a direct check
        # of the same invariant scoped to this task's own section.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Clean-context debug escalation — 2026-07-18 (fg-a10701)", c
        )

    def test_fresh_context_requirement(self):
        # EARS clause 1: dispatch forge-debugger (Hex) in a FRESH context,
        # given the failing diff + both verifier FAIL notes, root-causing
        # from scratch rather than re-poking the same worker.
        c = self._norm("docs/conventions.md")
        self.assertIn("dispatch", c)
        self.assertIn(
            "`forge-debugger` (Hex) in a FRESH context, never the same "
            "worker re-poked with notes appended",
            c,
        )
        self.assertIn(
            "Hex's spawn contract carries the failing diff plus BOTH "
            "verifier FAIL notes as inputs",
            c,
        )
        self.assertIn("root-causes from scratch", c)
        self.assertIn("no memory of the stuck worker's prior attempts", c)

    def test_normal_verification_routing(self):
        # EARS clause 2 (fix path): equal-or-higher tier, delta-scoped
        # re-verify — never a fresh full panel.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "routes through NORMAL verification at the task's original "
            "equal-or-higher tier",
            c,
        )
        self.assertIn("delta-only bounce re-verify", c)
        self.assertIn("never a fresh full panel", c)

    def test_cannot_fix_blocks_with_postmortem_as_today(self):
        # EARS clause 2 (no-fix path): block with the postmortem exactly
        # as today.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "the kernel blocks the task with the postmortem exactly as "
            "today",
            c,
        )

    def test_one_extra_attempt_never_a_loop(self):
        # EARS clause 2 (the cap): exactly one attempt, never an infinite
        # loop — at most one Hex dispatch per task, ever.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "This escalation adds exactly one attempt, never a loop", c
        )
        self.assertIn("at most ONE Hex dispatch per task, ever", c)
        self.assertIn("never a second Hex dispatch", c)

    def test_kernel_cites_the_escalation_before_the_block(self):
        # EARS clause 3: kernel INTEGRATE carries one citing sentence,
        # placed before the double-bounce block it modifies.
        content = self._norm("skills/kernel/SKILL.md")
        self.assertIn(
            'auto-dispatch ONE clean-context Hex attempt: '
            '`docs/conventions.md`, "Clean-context debug escalation — '
            '2026-07-18 (fg-a10701)" — NORMATIVE.',
            content,
        )
        cite_idx = content.index("auto-dispatch ONE clean-context Hex attempt")
        block_idx = content.index(
            "`state: blocked`, `claimed-by: null`, and write a plain-English blocker"
        )
        self.assertLess(
            cite_idx, block_idx,
            "escalation citation must precede the double-bounce block it "
            "modifies",
        )

    def test_kernel_skill_within_char_ceiling(self):
        # Hard ceiling from the task contract: the kernel file must stay
        # under the pre-existing 31,617-char budget after displacement.
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)
