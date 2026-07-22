"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task `sibling-notes-at-plan`: TestSiblingNotesAtPlanPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestSiblingNotesAtPlanPins(unittest.TestCase):
    """Doc-pin regression tests for `sibling-notes-at-plan` (cc-sdd rule,
    fg-a10702 steal-list, promoted 2026-07-20): PLAN reads same-spec DONE
    siblings' Attempt logs/Implementation Notes before dispatch, and LEARN
    does not mint a memory fact for knowledge with only intra-spec
    lifetime -- pinned so a future edit can't silently drop either half of
    this two-sided rule or its citation."""

    def _skill_content(self):
        path = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
        return _cached_read_text(path)

    def _reference_content(self):
        path = (
            REPO_ROOT
            / "skills"
            / "kernel"
            / "references"
            / "spawn-contract-template.md"
        )
        return _cached_read_text(path)

    def test_plan_step_cites_sibling_notes_reference(self):
        content = self._skill_content()
        self.assertIn(
            "WHEN a task's spec has DONE sibling tasks, PLAN reads their "
            "Attempt logs\nbefore dispatch",
            content,
        )
        self.assertIn(
            '`references/spawn-contract-template.md`, "Sibling task\n'
            'notes." NORMATIVE.',
            content,
        )

    def test_learn_step_cites_sibling_notes_reference_against_fact_minting(self):
        content = self._skill_content()
        self.assertIn(
            "Do NOT mint a LEARN fact for knowledge only serving same-spec "
            "siblings —\nsame reference, "
            '"Sibling task notes." NORMATIVE.',
            content,
        )

    def test_spawn_contract_context_pack_has_sibling_notes_line(self):
        content = self._reference_content()
        self.assertIn(
            '- Sibling task notes: <reusable context from same-spec DONE '
            'siblings, or "none">',
            content,
        )

    def test_reference_file_states_plan_reads_siblings_before_dispatch(self):
        content = self._reference_content()
        self.assertIn(
            "## Sibling task notes (cc-sdd pattern, fg-a10702 steal-list, "
            "promoted 2026-07-20)",
            content,
        )
        self.assertIn(
            "WHEN PLAN runs for a task whose spec has sibling tasks already "
            "`state: done`,\nTHE SYSTEM SHALL read those siblings' "
            "task-file Attempt logs / Implementation\nNotes for reusable "
            "context (helpers created, conventions settled, gotchas)\n"
            "BEFORE dispatch",
            content,
        )
        self.assertIn(
            'fold relevant findings into this contract\'s\nCONTEXT PACK '
            '"Sibling task notes" line rather than re-deriving them',
            content,
        )

    def test_reference_file_states_learn_shall_not_mint_intra_spec_fact(self):
        content = self._reference_content()
        self.assertIn(
            "WHEN LEARN considers filing a memory fact, THE SYSTEM SHALL "
            "NOT mint one for\nknowledge that only serves same-spec "
            "siblings",
            content,
        )
        self.assertIn(
            "intra-spec handoff rides the\ntask files themselves (this "
            "section), never a LEARN fact; LEARN facts are\nreserved for "
            "knowledge that outlives the spec.",
            content,
        )


if __name__ == "__main__":
    unittest.main()
