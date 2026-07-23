"""Doc-pin regression tests for fg-a10205 (skills/ui-behavior-correctness):
the skill exists with stable rule-ID anchors (top-layer rule, no-z-index-
escalation rule, a Playwright recipe anchor), the three agent files
(forge-ui, forge-animator, forge-ui-verifier) each carry exactly one
attachment line for it, and the skill's boundary section states it owns
interaction BEHAVIOR.

Own pin file (not tools/test_doc_pins.py) — that file is contended by a
parallel task per this task's execution plan.
"""
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "ui-behavior-correctness" / "SKILL.md"


class TestUiBehaviorSkillExists(unittest.TestCase):
    """EARS clause 1: a UI agent building/verifying overlay work finds this
    skill, covering stacking contexts, the native top-layer route, anchor
    positioning with collision-aware fallback, portals, scroll lock, focus
    management/dismissal, and viewport-edge spacing/collision — each rule
    ID'd, with browser-support status cited."""

    def test_skill_file_exists(self):
        self.assertTrue(SKILL_PATH.exists(), "skills/ui-behavior-correctness/SKILL.md missing")

    def test_frontmatter_description_triggers_on_overlay_work(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        lines = content.splitlines()
        self.assertEqual(lines[0], "---", "SKILL.md must open with frontmatter")
        description_line = next(l for l in lines if l.startswith("description:"))
        for phrase in ("dropdown", "z-index", "collision", "popover"):
            self.assertIn(
                phrase, description_line,
                f"description must trigger on {phrase!r}",
            )

    def test_has_last_verified_stamp(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("last-verified: 2026-07", content)

    def test_no_z_index_escalation_rule_anchor(self):
        """Pins UB-02 by ID and its verbatim rule sentence — the exact
        wording named in the task's execution plan ("Rule: overlays escape
        via top layer or portal, never via z-index escalation")."""
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-02 No z-index escalation", content)
        self.assertIn(
            "overlays escape via top layer or portal, never via z-index escalation",
            content,
        )

    def test_stacking_context_creators_rule_anchor(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-01 Stacking-context creators", content)

    def test_top_layer_rule_anchor_with_baseline_citations(self):
        """Pins UB-03 by ID plus verified Baseline-status facts for both the
        Popover API and <dialog> — the current-baseline-support-status
        requirement, not just a bare mention of "top layer"."""
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-03 Top-layer first", content)
        self.assertIn("popover=\"auto\"", content)
        self.assertIn("Newly available\n    since 2025-01-27", content)
        self.assertIn("showModal()", content)
        self.assertIn("Baseline Widely available\n    since March 2022", content)

    def test_anchor_positioning_rule_has_support_status(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-04 Anchor positioning", content)
        self.assertIn("not yet Widely available", content)

    def test_floating_ui_fallback_rule_has_middleware_vocabulary(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-05 JS fallback: floating-ui", content)
        for middleware in ("offset()", "flip()", "shift()", "size()", "arrow()"):
            self.assertIn(middleware, content)

    def test_focus_and_dismissal_rules_present(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-08 Dismissal per type", content)
        self.assertIn("UB-09 Focus management", content)
        self.assertIn("Focus trap is for **modals only**", content)

    def test_when_to_not_hand_roll_rule_cites_component_system_skill(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("UB-10 Use the primitive when one exists", content)
        self.assertIn("component-system-shadcn-radix", content)


class TestUiBehaviorPlaywrightRecipes(unittest.TestCase):
    """EARS clause 2: Playwright-CLI-scripted behavioral audit recipes in
    the same skill — open-overlay-assert-top-layer-and-unclipped,
    viewport-edge-flip, scroll-reposition, Esc/outside-click dismissal,
    tab-order traversal — runnable via Bash, consistent with
    webapp-visual-testing's tool ladder."""

    def setUp(self):
        self.content = SKILL_PATH.read_text(encoding="utf-8")

    def test_cites_webapp_visual_testing_tool_ladder(self):
        self.assertIn("`webapp-visual-testing`'s tool ladder", self.content)
        self.assertIn("npx playwright test", self.content)

    def test_all_five_recipe_names_present(self):
        for recipe in (
            "open-overlay-assert-top-layer-and-unclipped",
            "viewport-edge-flip",
            "scroll-reposition",
            "esc-and-outside-click-dismissal",
            "tab-order-and-return-focus",
        ):
            self.assertIn(recipe, self.content)

    def test_top_layer_recipe_proves_actually_on_top_via_element_from_point(self):
        """The load-bearing assertion of recipe (a): elementFromPoint at the
        overlay's center, proving it's actually on top rather than merely
        within-viewport-shaped — the exact anti-occlusion proof the task's
        execution plan calls for."""
        self.assertIn("document.elementFromPoint(x, y)", self.content)
        self.assertIn("toBeGreaterThanOrEqual(0)", self.content)

    def test_each_recipe_states_what_it_proves_and_failure_smell(self):
        self.assertEqual(self.content.count("Failure smell:"), 5)


class TestUiBehaviorBoundaryAnchor(unittest.TestCase):
    """EARS clause 3: forge-ui, forge-animator, forge-ui-verifier each find
    the skill attached, with a stated boundary versus visual-polish-and-
    craft (looks) and webapp-visual-testing (capture mechanics) — this
    skill owns interaction BEHAVIOR."""

    def test_boundary_section_exists(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("## Boundary", content)

    def test_boundary_states_owns_interaction_behavior(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("this skill owns interaction BEHAVIOR", content)

    def test_boundary_cites_visual_polish_and_craft(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("VP-06", content)

    def test_boundary_cites_webapp_visual_testing_capture_mechanics(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("`webapp-visual-testing` owns the capture mechanics", content)

    def test_boundary_cites_accessibility_and_component_system_skills(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("accessibility-wcag-aria", content)
        self.assertIn("component-system-shadcn-radix", content)


class TestUiBehaviorAgentAttachments(unittest.TestCase):
    """EARS clause 3 (attachment half): each of the three agents carries
    exactly one new attachment line for ui-behavior-correctness, with the
    one-line invariant — nothing else in the file changed except that
    single inserted line."""

    ATTACH_LINE = (
        "- ui-behavior-correctness — stacking/top-layer/collision/dismissal "
        "discipline for overlays and interactive components."
    )

    def test_forge_ui_has_attachment_line(self):
        content = (REPO_ROOT / "agents" / "forge-ui.md").read_text(encoding="utf-8")
        self.assertIn(self.ATTACH_LINE, content)
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    def test_forge_animator_has_attachment_line(self):
        content = (REPO_ROOT / "agents" / "forge-animator.md").read_text(encoding="utf-8")
        self.assertIn(self.ATTACH_LINE, content)
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    def test_forge_ui_verifier_has_attachment_line(self):
        content = (REPO_ROOT / "agents" / "forge-ui-verifier.md").read_text(encoding="utf-8")
        self.assertIn(self.ATTACH_LINE, content)
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    def test_attachment_line_sits_inside_attached_skills_section(self):
        """The inserted line must live under each file's '## Attached
        skills' heading, not appended somewhere unrelated."""
        for fname in ("forge-ui.md", "forge-animator.md", "forge-ui-verifier.md"):
            content = (REPO_ROOT / "agents" / fname).read_text(encoding="utf-8")
            self.assertIn("## Attached skills", content)
            section = content.split("## Attached skills", 1)[1]
            next_heading = section.find("\n## ")
            if next_heading != -1:
                section = section[:next_heading]
            self.assertIn(
                "ui-behavior-correctness", section,
                f"{fname}: attachment line not inside the Attached skills section",
            )


if __name__ == "__main__":
    unittest.main()
