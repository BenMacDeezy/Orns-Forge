"""Doc-pin regression tests for fg-9e0104: spec pipeline reorders the
approval-gate and decompose steps into compute-early / write-late — the full
task decomposition is derived once clarifications resolve and the spec body
freezes for the approval ask, then presented alongside the approval card.
Nothing is written to `.forge/queue/` before human approval; on approval,
task creation is a mechanical batch-write of the already-derived content; on
revision, the decomposition is recomputed from the revised spec (a stale
pre-compute is never reused).

These pins target skills/spec/SKILL.md only. They do not duplicate or
compete with tools/test_doc_pins.py's existing pins (e.g. "UI+motion task
splitting" on agents/forge-ui.md and agents/forge-animator.md) — this file
pins the spec skill's own reordered prose.
"""
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_SKILL = REPO_ROOT / "skills" / "spec" / "SKILL.md"


class TestSpecPrecomputeDecomposePins(unittest.TestCase):
    """Pins for fg-9e0104: compute-early / write-late reorder in the spec skill."""

    def setUp(self):
        self.content = SPEC_SKILL.read_text(encoding="utf-8")

    def test_write_nothing_before_approval(self):
        """Pins the explicit write-nothing-before-approval sentence.

        This is the core guarantee of EARS clause 1: the decomposition is
        derived pre-approval but nothing lands in the queue until a human
        approves. Anchor on the actual sentence, not just the heading, so a
        revert that guts the guarantee while keeping the step title fails
        this test.
        """
        self.assertIn(
            "it writes NOTHING to\n`.forge/queue/`, now or at any point before approval.",
            self.content,
        )

    def test_decomposition_presented_with_approval_card(self):
        """Pins the anchor proving the decomposition presents WITH the
        approval card, not after it — the human approves spec and
        decomposition in one look."""
        self.assertIn(
            "Present the clean draft spec body together with the decomposition pre-computed\n"
            "in step 4, so the human approves spec and decomposition in one look",
            self.content,
        )

    def test_approval_creates_via_mechanical_batch_write(self):
        """Pins EARS clause 2: on approval, task creation is a mechanical
        batch-write of already-derived content, not a fresh derivation pass."""
        self.assertIn(
            "create the queue tasks via the\n"
            "`forge:queue` skill from the decomposition already derived in step 4 — a\n"
            "mechanical batch-write of that already-derived content, not a fresh\n"
            "derivation pass.",
            self.content,
        )

    def test_revision_recomputes_never_reuses_stale_precompute(self):
        """Pins the recompute-on-revision sentence: a stale pre-compute from
        before a "Revise" is discarded, never reused for the next approval
        ask."""
        self.assertIn(
            "On \"Revise\": the spec body changes, which invalidates the step-4 pre-compute.\n"
            "Discard it and recompute the decomposition from the revised spec before the\n"
            "next approval ask — a stale pre-compute is never reused.",
            self.content,
        )

    def test_ui_motion_split_rule_survives_the_move(self):
        """The UI+motion split-at-intake rule moved from the old step 5 into
        the new step 4 (Pre-compute decomposition) verbatim in substance.
        Pin the citation phrase test_doc_pins.py also anchors elsewhere
        (agents/forge-ui.md, agents/forge-animator.md) so a revert that
        drops the citation while moving text fails loudly here too.
        """
        self.assertIn("UI+motion task splitting", self.content)

    def test_one_human_gate_and_self_approval_prohibition_untouched(self):
        """The one-human-gate rule and self-approval prohibition must survive
        the reorder unchanged in substance."""
        self.assertIn("Approval gate (the one human gate)", self.content)
        self.assertIn("Never self-approve.", self.content)

    def test_next_step_pointer_to_forge_start_untouched(self):
        """The /forge:start next-step pointer after task creation stays put."""
        self.assertIn(
            "After tasks are queued, state the next command in the reply: `/forge:start`",
            self.content,
        )

    def test_steps_are_renumbered_cleanly_with_no_gaps_or_dupes(self):
        """Sanity check on the reorder itself: top-level numbered steps run
        1..6 with no gaps or duplicates after the pre-compute step was
        inserted and decompose/approval were split into three steps."""
        import re

        numbers = [
            int(n)
            for n in re.findall(r"(?m)^## (\d+)\. ", self.content)
        ]
        self.assertEqual(numbers, [1, 2, 3, 4, 5, 6])


if __name__ == "__main__":
    unittest.main()
