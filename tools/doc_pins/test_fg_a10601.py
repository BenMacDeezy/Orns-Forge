"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10601`: TestFgA10601DesignFoundationPins.
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


class TestFgA10601DesignFoundationPins(unittest.TestCase):
    """Doc-pins for fg-a10601 (parallel design-foundation track): the
    `.forge/design/foundation.md` artifact format lands in
    docs/conventions.md as a dated section (with TOC entry), the
    design-direction step wires into `skills/spec/SKILL.md` at the same
    kickoff point as decomposition, the propose-2-3-directions rule and the
    same-gate presentation rule survive, the forge-ui/forge-animator
    binding lines exist, and the no-UI-no-ceremony carve-out is stated
    explicitly in both the format section and the agent contracts.

    Covers all 4 EARS clauses: (1) artifact + parallel-with-decomposition
    kickoff timing; (2) 2-3 distinct directions proposed by the design lead
    at the SAME human gate as decomposition, human picks/steers, chosen
    direction written to the file; (3) forge-ui/forge-animator spawn
    binding to the foundation, craft skills pull FROM it; (4) no UI work ->
    no forced foundation.
    """

    SECTION_HEADING = (
        "## Design foundation artifact (`.forge/design/foundation.md`) — "
        "2026-07-18"
    )

    def test_conventions_has_artifact_format_section_and_toc_entry(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn(
            "- Design foundation artifact (`.forge/design/foundation.md`) "
            "— 2026-07-18",
            content,
        )

    def test_conventions_artifact_section_has_frontmatter_and_body_sections(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("| status | draft \\| approved \\| superseded |", section)
        for heading in (
            "## Visual identity",
            "## Token system",
            "## Layout language",
            "## Component patterns",
            "## Interaction personality",
            "## Candidate directions",
            "## Amendments",
        ):
            self.assertIn(heading, section)
        self.assertIn(
            "color / type / spacing / radius / shadow / motion", section
        )
        self.assertIn(
            "skills/spec/references/design-foundation-template.md", section
        )

    def test_conventions_artifact_section_has_kickoff_parallel_timing(self):
        """EARS clause 1: authored AT KICKOFF, in PARALLEL with the
        technical decomposition, never a later phase."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn(
            "established AT KICKOFF, in\nPARALLEL with the technical "
            "decomposition — never a later, bolted-on phase",
            section,
        )

    def test_conventions_artifact_section_has_same_gate_and_propose_rule(self):
        """EARS clause 2: 2-3 DISTINCT directions, SAME gate as
        decomposition, human picks/steers, chosen direction written."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "presented to the human at the SAME approval gate as the "
            "technical decomposition", normalized,
        )
        self.assertIn("the spec pipeline's one human gate", normalized)
        self.assertIn("never a separate design-approval step", normalized)
        self.assertIn("The human picks one, steers a synthesis", normalized)

    def test_conventions_artifact_section_has_no_ui_carveout(self):
        """EARS clause 4: no UI work -> no forced foundation, no ceremony."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN no project or spec has UI work, THE SYSTEM SHALL NOT "
            "create `.forge/design/foundation.md`", normalized,
        )
        self.assertIn("no ceremony where it does not apply", normalized)

    def test_conventions_artifact_section_has_binding_rule(self):
        """EARS clause 3: forge-ui/forge-animator spawn binds to the
        foundation; craft skills pull tokens/patterns FROM it."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN a `forge-ui` or `forge-animator` task dispatches in a "
            "project that has `.forge/design/foundation.md`, THE SYSTEM "
            "SHALL bind the spawn contract to it", normalized,
        )
        self.assertIn("visual-polish-and-craft", normalized)
        self.assertIn("ui-behavior-correctness", normalized)
        self.assertIn("component-system-shadcn-radix", normalized)
        self.assertIn("pull tokens/patterns FROM the foundation", normalized)

    def test_spec_skill_has_design_direction_step_wired_at_kickoff(self):
        """The design-direction step lives in skills/spec/SKILL.md,
        directly after Pre-compute decomposition (step 4) and before the
        Approval gate (step 5) — parallel with decomposition, same
        kickoff point, not a later phase."""
        content = _cached_read_text((REPO_ROOT / "skills" / "spec" / "SKILL.md"))
        self.assertIn("### Design direction (UI work only)", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Runs at the same kickoff point, in PARALLEL with the "
            "decomposition above", normalized,
        )
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "Design foundation artifact (`.forge/design/foundation.md`) "
            "— 2026-07-18",
            normalized,
        )
        # The subsection sits between step 4's own heading and step 5's.
        idx_step4 = content.index("## 4. Pre-compute decomposition")
        idx_design = content.index("### Design direction (UI work only)")
        idx_step5 = content.index("## 5. Approval gate")
        self.assertTrue(idx_step4 < idx_design < idx_step5)

    def test_spec_skill_approval_gate_presents_directions_at_same_gate(self):
        """EARS clause 2's same-gate presentation, expressed in the
        pipeline that actually runs the gate (not just the format doc)."""
        content = _cached_read_text((REPO_ROOT / "skills" / "spec" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "present them at this SAME gate, alongside the spec body and "
            "decomposition", normalized,
        )
        self.assertIn("never a separate design-approval ask", normalized)
        self.assertIn(
            "Write the chosen direction into `.forge/design/foundation.md`",
            normalized,
        )

    def test_spec_skill_design_direction_has_no_ui_carveout(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "spec" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "THE SYSTEM SHALL NOT force a design foundation", normalized
        )
        self.assertIn("no ceremony where it does not apply", normalized)

    def test_forge_ui_has_foundation_binding_and_design_lead_capability(self):
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-ui.md"))
        self.assertIn("## Design-lead capability (spec kickoff)", content)
        self.assertIn("## Foundation binding", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("2-3 DISTINCT professional design directions", normalized)
        self.assertIn(
            "THE SYSTEM SHALL bind this task to it", normalized,
        )
        self.assertIn("pull tokens/patterns FROM the foundation", normalized)
        # ui-behavior-correctness is pinned to a single occurrence elsewhere
        # in this file (tools/test_pins_ui_behavior.py); the binding
        # paragraph must not repeat the literal skill name, only its craft
        # (overlay/dismissal discipline) — assert the count stays exactly
        # one so this pin and that one can never silently drift apart.
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    def test_forge_animator_has_one_line_foundation_binding(self):
        """forge-animator.md gets exactly ONE added line for the binding
        invariant — pin the line's presence and that it's a single bullet
        under Rules, not a whole new section."""
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-animator.md"))
        self.assertIn(
            "pull motion tokens/patterns FROM it, same binding as "
            "`forge-ui`",
            content,
        )
        # Single-line invariant: no new "## " section heading was added.
        self.assertNotIn("## Foundation binding", content)

    def test_design_foundation_seed_template_exists(self):
        tpl_path = (
            REPO_ROOT / "skills" / "spec" / "references"
            / "design-foundation-template.md"
        )
        self.assertTrue(tpl_path.exists(), "design-foundation-template.md missing")
        content = _cached_read_text(tpl_path)
        for heading in (
            "## Visual identity",
            "## Token system",
            "## Layout language",
            "## Component patterns",
            "## Interaction personality",
            "## Candidate directions",
            "## Amendments",
        ):
            self.assertIn(heading, content)
