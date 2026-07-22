"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9c0301_0302`: TestFg9c0301_0302Pins.
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


class TestFg9c0301_0302Pins(unittest.TestCase):
    """Doc-pins for fg-9c0301 (visual-polish-and-craft + design-tokens-pipeline
    reference) and fg-9c0302 (webapp-visual-testing).

    fg-9c0301's own bounce reworded four near-verbatim passages in
    visual-polish-and-craft/SKILL.md (eyebrow-everywhere, hero-metric-template,
    side-stripe-border, and the micro-copy example sentence) so the wording is
    genuinely re-derived rather than a lightly-synonym-swapped copy of the
    mined sources. Deliberately do NOT pin those passages by their new
    wording here — doing so would just re-verbatim-lock a different string
    and defeat future rewrites. Pin the stable pattern IDs instead; the prose
    around them is free to keep changing.
    """

    def test_visual_polish_has_all_nine_hard_rule_ids(self):
        """Verify every VP-01..VP-09 hard-rule ID is still present.

        Catches a rule being silently dropped, renumbered, or merged into
        another during future edits to the hard-rules section.
        """
        content = _cached_read_text((REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md"))
        for n in range(1, 10):
            self.assertIn(f"VP-{n:02d}", content, f"VP-{n:02d} missing from hard rules")

    def test_visual_polish_has_boundary_vs_anti_generic(self):
        """Verify the §6 Boundary section still draws the direction-vs-execution
        line against anti-generic-design-restraint.

        Pins "owns direction-level taste" — the actual dividing line the
        boundary paragraph draws, not just a mention of the other skill's
        name — so a future edit can't gut the boundary rule while leaving
        the cross-reference intact.
        """
        content = _cached_read_text((REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md"))
        self.assertIn("anti-generic-design-restraint", content)
        self.assertIn("owns direction-level taste", content)

    def test_visual_polish_has_banned_pattern_ids(self):
        """Verify the three banned-pattern IDs touched by the fg-9c0301 rewrite
        still exist by ID, independent of whatever prose currently describes
        them (the prose was rewritten once already and may be rewritten
        again; the ID is the stable contract)."""
        content = _cached_read_text((REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md"))
        self.assertIn("eyebrow-everywhere", content)
        self.assertIn("hero-metric-template", content)
        self.assertIn("side-stripe-border", content)

    def test_visual_polish_has_both_source_citations(self):
        """Verify both Adapted-from citations in the Sources section survive:
        pbakaus/impeccable and anthropics/skills frontend-design, each tagged
        with their actual license."""
        content = _cached_read_text((REPO_ROOT / "skills" / "visual-polish-and-craft" / "SKILL.md"))
        self.assertIn("pbakaus/impeccable (Apache-2.0)", content)
        self.assertIn("anthropics/skills `frontend-design` (Apache-2.0)", content)

    def test_design_tokens_curated_palettes_reference_exists(self):
        """Verify the design-tokens-pipeline curated-palettes-and-pairings
        reference exists, cites its MIT source, and still refuses to mine the
        source's by-industry pick-list shape.

        Pins "does not mine that shape of data" — the sentence stating the
        deliberate omission — so a future edit can't quietly turn this file
        into the by-industry lookup table anti-generic-design-restraint
        exists to veto.
        """
        ref_path = (
            REPO_ROOT
            / "skills"
            / "design-tokens-pipeline"
            / "references"
            / "curated-palettes-and-pairings.md"
        )
        self.assertTrue(ref_path.exists(), "curated-palettes-and-pairings.md missing")
        content = _cached_read_text(ref_path)
        self.assertIn("nextlevelbuilder/ui-ux-pro-max-skill (MIT)", content)
        self.assertIn("does not mine that shape of data", content)

    def test_webapp_visual_testing_has_tool_ladder(self):
        """Verify the three-tier tool ladder (browser-MCP-first,
        Playwright-second, neither-available) is intact by its actual
        heading text, plus the Apache-2.0 source citation."""
        content = _cached_read_text((REPO_ROOT / "skills" / "webapp-visual-testing" / "SKILL.md"))
        self.assertIn("Browser MCP (first choice)", content)
        self.assertIn("Repo-native Playwright via Bash (second choice)", content)
        self.assertIn("Neither available.", content)
        self.assertIn("anthropics/skills webapp-testing", content)
        self.assertIn("(Apache-2.0)", content)

    def test_webapp_visual_testing_has_default_breakpoints(self):
        """Verify the 375/768/1280 default breakpoint trio survives — the
        fallback used when a task doesn't specify its own breakpoints."""
        content = _cached_read_text((REPO_ROOT / "skills" / "webapp-visual-testing" / "SKILL.md"))
        self.assertIn("375px", content)
        self.assertIn("768px", content)
        self.assertIn("1280px", content)
