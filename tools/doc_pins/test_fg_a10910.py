"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10910`: TestFgA10910BoundaryMapPins.
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


class TestFgA10910BoundaryMapPins(unittest.TestCase):
    """fg-a10910: spec-time file-boundary maps (cc-sdd steal-list item 2) —
    every decomposition item computed at spec step 4 carries `Boundary:`/
    `Depends:` annotations, overlapping Boundary claims resolve BEFORE the
    approval ask, an approved item's Boundary carries into the created task
    file as the source the kernel's dispatch-contract file-ownership line
    quotes, and the rule is stated once in a dated conventions section and
    pinned across the spec skill, the spec-writer draft format, and
    conventions itself."""

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 4: dated section, canonical home for the rule.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Spec-time boundary maps — 2026-07-18 (fg-a10910)", c
        )

    def test_toc_lists_the_new_section(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Spec-time boundary maps — 2026-07-18 (fg-a10910)", c
        )

    def test_spec_skill_annotation_requirement(self):
        # EARS clause 1: every decomposition item carries Boundary:/Depends:,
        # derived from the design's file structure plan.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn("Boundary/Depends annotations (fg-a10910)", s)
        self.assertIn(
            "carries `Boundary:` (the files/dirs it owns exclusively) and "
            "`Depends:` (the contract tasks it consumes), derived from the "
            "design's file structure plan",
            s,
        )

    def test_spec_skill_composes_with_contract_first(self):
        # EARS clause 1 rider: Boundary/Depends composes with contract-first
        # decomposition (fg-a10901) rather than duplicating it.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "the contract item that Contract-first decomposition (above) "
            "already splits out is exactly what a consumer's `Depends:` "
            "line points at",
            s,
        )

    def test_spec_skill_conflict_resolution_before_approval(self):
        # EARS clause 2: overlapping Boundary paths resolve BEFORE step 5 —
        # a blocked-by edge or a re-split, never a conflicted decomposition
        # presented for approval.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "WHEN two items claim overlapping `Boundary:` paths, resolve it "
            "BEFORE the approval ask in step 5",
            s,
        )
        self.assertIn(
            "never carry an unresolved `Boundary:` conflict into the "
            "approval gate",
            s,
        )

    def test_spec_skill_boundary_carried_into_task_file(self):
        # EARS clause 3: Boundary carries verbatim into the created task
        # file's Execution plan body, pre-seeded rather than left (pending).
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "carries verbatim into the created task file's Execution plan "
            "body",
            s,
        )
        self.assertIn(
            "is the SOURCE the kernel's dispatch-contract SCOPE",
            s,
        )

    def test_conventions_section_states_context_pack_linkage(self):
        # EARS clause 3 rider: the dated section itself states the
        # Boundary -> context-pack linkage, citing fg-a10908 (and the spawn
        # contract template) rather than restating that section's prose.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "Verification infrastructure — 2026-07-18 (fg-a10908)", c
        )
        self.assertIn(
            "is the SOURCE the kernel's dispatch-contract file-ownership "
            "line quotes",
            c,
        )
        self.assertIn(
            "skills/kernel/references/spawn-contract-template.md", c
        )

    def test_conventions_section_conflict_resolution(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "that conflict is resolved BEFORE the approval ask in step 5",
            c,
        )
        self.assertIn(
            "A decomposition with an unresolved `Boundary:` conflict is "
            "never presented for human approval",
            c,
        )

    def test_spec_writer_draft_format_carries_fields(self):
        # forge-spec-writer's draft format emits the two new fields per item.
        w = self._norm("agents/forge-spec-writer.md")
        self.assertIn(
            "Boundary: <files/dirs this item owns exclusively>", w
        )
        self.assertIn(
            "Depends: <none | contract item(s) this item consumes>", w
        )
        self.assertIn(
            "Spec-time boundary maps — 2026-07-18 (fg-a10910)", w
        )

    def test_spec_flow_pins_untouched(self):
        # This task must compose with, not disturb, the existing
        # compute-early/write-late pins in tools/test_pins_spec_flow.py —
        # sanity-check the two load-bearing sentences those pins anchor are
        # still intact after this task's step-4/step-6 edits.
        s = self._norm("skills/spec/SKILL.md")
        self.assertIn(
            "it writes NOTHING to `.forge/queue/`, now or at any point "
            "before approval.",
            s,
        )
        self.assertIn(
            "After tasks are queued, state the next command in the reply: "
            "`/forge:start`",
            s,
        )
