"""Doc-pin regression tests for the batched sibling build of three mobile
craft skills (scout shortlist A, 2026-07-21 tasks react-native-motion-gestures,
mobile-visual-testing, expo-eas-workflow): each SKILL.md exists with its scope
one-liner, the Maestro free-CLI-only rule, the expo/skills provenance line,
and the two agent-attachment lines wiring the mobile skills into
agents/forge-mobile.md and agents/forge-mobile-verifier.md. Sharded per the
fg-a11040 per-task-id-module convention so this trio's pins land in their own
file instead of conflicting with concurrent tasks at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestMobileSkillTrioFilesExist(unittest.TestCase):
    """Each of the three skills ships as skills/<id>/SKILL.md."""

    SKILL_PATHS = {
        "react-native-motion-gestures": REPO_ROOT / "skills"
        / "react-native-motion-gestures" / "SKILL.md",
        "mobile-visual-testing": REPO_ROOT / "skills"
        / "mobile-visual-testing" / "SKILL.md",
        "expo-eas-workflow": REPO_ROOT / "skills"
        / "expo-eas-workflow" / "SKILL.md",
    }

    def test_all_three_skill_files_exist(self):
        for name, path in self.SKILL_PATHS.items():
            self.assertTrue(path.is_file(), f"{name}: {path} missing")

    def test_all_three_have_frontmatter_name_matching_dir(self):
        for name, path in self.SKILL_PATHS.items():
            content = _cached_read_text(path)
            self.assertTrue(content.startswith("---\n"))
            self.assertIn(f"name: {name}", content)


class TestReactNativeMotionGesturesPins(unittest.TestCase):
    """Scope one-liner (frontmatter description) and load-bearing worklet/
    gesture-composition/interop phrases from
    skills/react-native-motion-gestures/SKILL.md."""

    PATH = REPO_ROOT / "skills" / "react-native-motion-gestures" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_scope_one_liner(self):
        content = self._content()
        self.assertIn(
            "Build native-driven animation and gesture interactions in "
            "React Native/Expo with Reanimated 4 + Gesture Handler 3",
            content,
        )

    def test_worklet_and_shared_value_concepts(self):
        content = self._content()
        self.assertIn("useSharedValue", content)
        self.assertIn("useAnimatedStyle", content)
        self.assertIn('`"worklet";`', content)

    def test_gesture_composition_hooks(self):
        content = self._content()
        self.assertIn("useSimultaneousGestures", content)
        self.assertIn("useExclusiveGestures", content)
        self.assertIn("useCompetingGestures", content)

    def test_interop_pitfalls(self):
        content = self._content()
        self.assertIn("Stale closures", content)
        self.assertIn("runOnJS", content)
        self.assertIn("runOnUI", content)

    def test_cross_references_react_native_performance_and_motion_principles(self):
        content = self._content()
        self.assertIn("`react-native-performance`", content)
        self.assertIn("`motion-design-principles`", content)

    def test_sources_cite_reanimated_and_gesture_handler(self):
        content = self._content()
        self.assertIn("docs.swmansion.com/react-native-reanimated", content)
        self.assertIn("docs.swmansion.com/react-native-gesture-handler", content)


class TestMobileVisualTestingPins(unittest.TestCase):
    """Scope one-liner, the Maestro free-local-CLI-only rule (paid cloud
    explicitly out of scope), and flake-source coverage from
    skills/mobile-visual-testing/SKILL.md."""

    PATH = REPO_ROOT / "skills" / "mobile-visual-testing" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_scope_one_liner(self):
        content = self._content()
        self.assertIn(
            "Drive and screenshot a running React Native/Expo app on a "
            "real device surface for visual verification", content,
        )

    def test_maestro_free_cli_only_rule(self):
        content = self._content()
        self.assertIn("free local CLI only", content)
        self.assertIn(
            "Maestro Cloud (parallel hosted device runs,\n   priced per "
            "concurrent device) is a separate paid product and is\n   "
            "explicitly out of scope for this skill",
            content,
        )
        self.assertIn("never assume or reach for cloud execution", content)

    def test_adb_and_simctl_capture_recipes(self):
        content = self._content()
        self.assertIn("adb exec-out screencap -p", content)
        self.assertIn("xcrun simctl io booted screenshot", content)

    def test_flake_sources_covered(self):
        content = self._content()
        self.assertIn("Animation settle", content)
        self.assertIn("Keyboard state", content)
        self.assertIn("Permission dialogs", content)

    def test_forge_mobile_verifier_rules_point_at_this_skill(self):
        # This skill is the HOW behind forge-mobile-verifier's
        # render-and-observe step, per its own header claim.
        content = self._content()
        self.assertIn("forge-mobile-verifier", content)
        verifier = _cached_read_text(
            REPO_ROOT / "agents" / "forge-mobile-verifier.md"
        )
        self.assertIn("mobile-visual-testing", verifier)


class TestExpoEasWorkflowPins(unittest.TestCase):
    """Scope one-liner, the expo/skills provenance line (MIT, cite-not-copy),
    and the paid-tier cost flag from skills/expo-eas-workflow/SKILL.md."""

    PATH = REPO_ROOT / "skills" / "expo-eas-workflow" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_scope_one_liner(self):
        content = self._content()
        self.assertIn(
            "Operational workflow for shipping an Expo/React Native app "
            "with EAS", content,
        )

    def test_provenance_line_cites_expo_skills_mit(self):
        content = self._content()
        self.assertIn(
            "Adapted (not copied) from **github.com/expo/skills** "
            "(MIT License,", content,
        )
        self.assertIn("650 Industries/Expo", content)
        self.assertIn("`eas-app-stores`", content)
        self.assertIn("`eas-workflows`", content)

    def test_paid_tier_cost_flag(self):
        content = self._content()
        self.assertIn("EAS costs money past the free tier", content)
        self.assertIn("expo.dev/pricing", content)

    def test_update_compatibility_and_channels_covered(self):
        content = self._content()
        self.assertIn("runtime version", content)
        self.assertIn("rollout percentage", content)
        self.assertIn("Channels", content)


class TestMobileAgentAttachmentPins(unittest.TestCase):
    """The two agent-attachment lines: forge-mobile.md attaches
    react-native-motion-gestures, forge-mobile-verifier.md attaches
    mobile-visual-testing."""

    FORGE_MOBILE_PATH = REPO_ROOT / "agents" / "forge-mobile.md"
    FORGE_MOBILE_VERIFIER_PATH = REPO_ROOT / "agents" / "forge-mobile-verifier.md"

    def test_forge_mobile_attaches_motion_gestures_skill(self):
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        self.assertIn("react-native-motion-gestures", content)

    def test_forge_mobile_verifier_attaches_visual_testing_skill(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn("mobile-visual-testing", content)

    def test_dispatch_routing_skills_paragraph_names_both(self):
        # Tail-touch of the existing "Mobile routing" section's Skills
        # paragraph (docs/conventions/dispatch-and-routing.md) — this pin
        # only checks the two new skill names are named there; it does not
        # re-pin the pre-existing routing/verification/observation-surface/
        # honest-degradation wording (covered by test_forge_mobile_agents.py).
        content = _cached_read_text(
            REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md"
        )
        self.assertIn("react-native-motion-gestures", content)
        self.assertIn("mobile-visual-testing", content)

    def test_skill_count_includes_the_trio(self):
        # This trio bumped the skills/ directory by 3; concurrent sibling
        # batches (wt-skillsb +2, wt-skillsc +4) landed in the same
        # integration wave, so the pin asserts a floor, not a literal —
        # on-disk vs README vs map consistency itself is pinned by
        # tools/doc_pins/test_fg_a10101.py (test_skill_count_consistent).
        actual = len(list((REPO_ROOT / "skills").glob("*/SKILL.md")))
        self.assertGreaterEqual(actual, 51)


if __name__ == "__main__":
    unittest.main()
