"""Doc-pin regression tests for component-library-references (2026-07-21):
Base UI becomes the default primitive layer in
skills/component-system-shadcn-radix/SKILL.md (Radix staying fully
supported), the registry supply-chain rule (never `--overwrite` against an
unfamiliar registry), the situational-alternatives list, and the mobile
component-system cross-reference (NativeWind + react-native-reusables as
default, Tamagui as the web+native alternative, gluestack-ui carrying an
amber maintenance flag) landing in skills/react-native-foundations/SKILL.md
and agents/forge-mobile.md. Sharded per the fg-a11040 per-task-id-module
convention so this task's pins land in their own file."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestShadcnRadixBaseUiPins(unittest.TestCase):
    """Base UI as the default primitive layer, Radix as the fully-supported
    alternate, and the asChild <-> render auto-conversion note in
    skills/component-system-shadcn-radix/SKILL.md."""

    PATH = REPO_ROOT / "skills" / "component-system-shadcn-radix" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_base_ui_default_sentence(self):
        content = self._content()
        self.assertIn(
            "Base UI is the default primitive library for new projects as of\n"
            "  July 2026",
            content,
        )
        self.assertIn("npx shadcn@latest init -b base", content)
        self.assertIn("2:1", content)
        self.assertIn("v1.6.0 (Jun 2026)", content)

    def test_radix_fully_supported_alternate(self):
        content = self._content()
        self.assertIn(
            "Radix stays fully supported, never deprecated", content
        )
        self.assertIn("npx shadcn@latest init -b radix", content)
        self.assertIn("every component still\n  ships for both", content)

    def test_aschild_render_migration_is_skill_not_cli(self):
        # 2026-07-21 grouped-verify P2 fix: migration is a coding-agent
        # skill with human-decided behavior changes, NOT a CLI
        # auto-conversion — pin the corrected mechanism and ban the old
        # claim.
        content = self._content()
        self.assertIn("`asChild` (Radix) and `render` (Base UI)", content)
        self.assertIn("Migration between the two is NOT a CLI feature",
                      content)
        self.assertIn("npx skills add shadcn/ui", content)
        self.assertIn("behavior changes are flagged for a human decision",
                      content)
        self.assertNotIn("shadcn CLI auto-converts", content)

    def test_cli_registry_mcp_sections_untouched(self):
        # AC: CLI/registry/MCP sections stay unchanged — sanity-check the
        # pre-existing load-bearing sentences from those sections survive
        # this task's edits.
        content = self._content()
        self.assertIn(
            "The CLI copies component **source\nfiles** into the project",
            content,
        )
        self.assertIn(
            "makes **any** repo a shadcn registry the CLI can install from",
            content,
        )
        self.assertIn(
            "use it** instead of\nscripting `add`/`view` by hand",
            content,
        )


class TestShadcnRadixSupplyChainPins(unittest.TestCase):
    """The registry supply-chain rule: unaudited registry.json == unreviewed
    npm package, never --overwrite against unfamiliar registries, inspect
    file/dependency lists for script runners, hand-vendor when in doubt, and
    the recency-unverified example libraries."""

    PATH = REPO_ROOT / "skills" / "component-system-shadcn-radix" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_never_overwrite_rule(self):
        content = self._content()
        self.assertIn(
            "Never pass `--overwrite` against an unfamiliar registry.",
            content,
        )

    def test_unreviewed_npm_package_framing(self):
        content = self._content()
        self.assertIn(
            "treat an\nunaudited registry the same way you'd treat an "
            "unreviewed npm package",
            content,
        )

    def test_inspect_files_and_deps_for_script_runners(self):
        content = self._content()
        self.assertIn(
            "view the item's file list and dependency list", content
        )
        self.assertIn("dev-dependency script runners", content)
        self.assertIn("Discussion #7747", content)

    def test_hand_vendor_when_in_doubt(self):
        content = self._content()
        self.assertIn("Hand-vendor when in doubt", content)

    def test_recency_unverified_examples(self):
        content = self._content()
        self.assertIn("Origin UI, Aceternity, Magic UI, and Park UI", content)
        self.assertIn("unverified — check directly before use", content)


class TestShadcnRadixSituationalAlternativesPins(unittest.TestCase):
    """React Aria Components, Ark UI, and the Mantine RSC non-fit note."""

    PATH = REPO_ROOT / "skills" / "component-system-shadcn-radix" / "SKILL.md"

    def _content(self):
        return _cached_read_text(self.PATH)

    def test_react_aria_components(self):
        content = self._content()
        self.assertIn("React Aria Components", content)
        self.assertIn(
            "date pickers, grids, drag-and-drop", content
        )

    def test_ark_ui_multi_framework(self):
        content = self._content()
        self.assertIn("Ark UI", content)
        self.assertIn("multi-framework", content)

    def test_mantine_rsc_non_fit(self):
        content = self._content()
        self.assertIn("Mantine", content)
        self.assertIn(
            "non-fit for RSC-first Next.js App Router\n  projects", content
        )


class TestMobileComponentSystemReferencePins(unittest.TestCase):
    """NativeWind + react-native-reusables as the mobile default reference,
    Tamagui as the web+native alternative, and gluestack-ui's amber
    maintenance flag in skills/react-native-foundations/SKILL.md and the
    one-line pointer in agents/forge-mobile.md."""

    RN_FOUNDATIONS_PATH = (
        REPO_ROOT / "skills" / "react-native-foundations" / "SKILL.md"
    )
    FORGE_MOBILE_PATH = REPO_ROOT / "agents" / "forge-mobile.md"

    def test_nativewind_reusables_default_line(self):
        content = _cached_read_text(self.RN_FOUNDATIONS_PATH)
        self.assertIn(
            "**Component system: NativeWind + react-native-reusables is "
            "the default\n  reference**",
            content,
        )
        self.assertIn("web pick, and the same copy-in philosophy:", content)
        self.assertIn("~36 of\n  shadcn's 51 components are ported", content)

    def test_tamagui_web_native_alternative(self):
        content = _cached_read_text(self.RN_FOUNDATIONS_PATH)
        self.assertIn("**Tamagui** is the alternative", content)
        self.assertIn("shared across web *and* native", content)

    def test_gluestack_amber_flag(self):
        content = _cached_read_text(self.RN_FOUNDATIONS_PATH)
        self.assertIn(
            "**gluestack-ui** carries a maintenance-trajectory **amber "
            "flag**",
            content,
        )

    def test_forge_mobile_points_at_the_reference(self):
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        self.assertIn(
            "Absent a project-specific\n  skill, `react-native-foundations`'"
            " component-system cross-reference\n  (NativeWind + "
            "react-native-reusables) is the default.",
            content,
        )

    def test_forge_mobile_design_system_line_not_restructured(self):
        # AC: "ONE added line, no restructure" — the pre-existing sentence
        # this task's addition sits next to must survive verbatim.
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        self.assertIn(
            "the project's design-system skill, if the repo has one — the "
            "source of\n  truth for tokens/components; do not override it.",
            content,
        )


if __name__ == "__main__":
    unittest.main()
