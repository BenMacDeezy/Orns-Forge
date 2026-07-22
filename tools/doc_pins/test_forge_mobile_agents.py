"""Doc-pin regression tests for task `forge-mobile-agent`: the forge-mobile /
forge-mobile-verifier agent pair, the roster/count surfaces they bump
23->25, and the dated conventions section that routes mobile-shaped work to
them. Sharded per the fg-a11040 per-task-id-module convention so this
task's pins land in their own file instead of conflicting with concurrent
tasks at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
)


class TestForgeMobileAgentsPins(unittest.TestCase):
    """forge-mobile-agent: both agent files exist with the right identity,
    the mobile-not-web boundary, the simulator/emulator observation surface,
    the honest-degradation flag wording, judges-only doctrine, the dated
    conventions.md section (TOC + shards manifest + body), and refreshed
    agent counts (23->25) across roster/count surfaces."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    SHARD_PATH = REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md"
    HEADING = "## Mobile routing (forge-mobile pair) — 2026-07-21"

    FORGE_MOBILE_PATH = REPO_ROOT / "agents" / "forge-mobile.md"
    FORGE_MOBILE_VERIFIER_PATH = REPO_ROOT / "agents" / "forge-mobile-verifier.md"

    @staticmethod
    def _read(path):
        return _read_path(path)

    def _section(self):
        content = self._read(self.CONVENTIONS_PATH)
        return content.split(self.HEADING, 1)[1].split("\n## ", 1)[0]

    def _norm_section(self):
        return " ".join(self._section().split())

    # -- both agent files exist --

    def test_both_agent_files_exist(self):
        self.assertTrue(self.FORGE_MOBILE_PATH.is_file())
        self.assertTrue(self.FORGE_MOBILE_VERIFIER_PATH.is_file())

    # -- forge-mobile: mobile-not-web identity --

    def test_forge_mobile_identity_is_mobile_not_web(self):
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        normalized = " ".join(content.split())
        self.assertIn("React Native / Expo / mobile task", normalized)
        self.assertIn(
            "Web-shaped UI (browser rendering, Core Web Vitals) stays "
            "with `forge-ui`", normalized,
        )
        self.assertIn(
            "Never copy web-specific doctrine (Core Web Vitals, browser "
            "DOM/CSS assumptions) onto native", normalized,
        )

    def test_forge_mobile_attaches_required_skills(self):
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        self.assertIn("react-native-foundations", content)
        self.assertIn("react-native-performance", content)
        self.assertIn("react-performance", content)

    def test_forge_mobile_performance_budgets(self):
        content = _cached_read_text(self.FORGE_MOBILE_PATH)
        self.assertIn("startup time", content)
        self.assertIn("JS-thread frame drops", content)
        self.assertIn("virtualize", content.lower())

    # -- forge-mobile-verifier: judges-only doctrine --

    def test_forge_mobile_verifier_judges_only(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn("Never fixes code — only judges it", content)
        self.assertIn("Never edit source code — you judge, you do not fix.",
                       content)
        self.assertIn("Never touch `.forge/`.", content)

    def test_forge_mobile_verifier_tools_are_read_only(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn("tools: Read, Grep, Glob, Bash, ToolSearch", content)
        self.assertNotIn("Edit", content.split("---", 2)[1])
        self.assertNotIn("Write", content.split("---", 2)[1])

    # -- forge-mobile-verifier: simulator/emulator observation surface --

    def test_forge_mobile_verifier_device_surfaces(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn("adb exec-out screencap -p", content)
        self.assertIn("adb shell", content)
        self.assertIn("logcat", content)
        self.assertIn("xcrun simctl", content)
        self.assertIn("macOS hosts only", content)
        self.assertIn("Never substitute a web browser", content)

    def test_forge_mobile_verifier_never_uses_browser(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn(
            "Never substitute a web browser for the device observation "
            "surface.", content,
        )

    # -- honest-degradation flag wording --

    def test_forge_mobile_verifier_honest_degradation(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn(
            "visual verification UNAVAILABLE on this host", content
        )
        self.assertIn("gate-level + static verification only", content)
        self.assertIn("A browser is NEVER a substitute observation", content)
        self.assertIn(
            "a visual PASS is never fabricated or\n      inferred from "
            "code alone.", content,
        )

    def test_forge_mobile_verifier_output_contract_has_device_surface_field(self):
        content = _cached_read_text(self.FORGE_MOBILE_VERIFIER_PATH)
        self.assertIn(
            "DEVICE SURFACE: <Android emulator (adb) | iOS Simulator "
            "(xcrun simctl) | visual verification UNAVAILABLE on this "
            "host>", content,
        )

    # -- dated conventions section: TOC + shards manifest + body --

    def test_conventions_corpus_has_dated_heading(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(self.HEADING, content)

    def test_conventions_toc_entry_present(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn("- Mobile routing (forge-mobile pair) — 2026-07-21\n",
                       content)

    def test_shards_manifest_maps_to_dispatch_and_routing(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            "- `Mobile routing (forge-mobile pair) — 2026-07-21` -> "
            "`docs/conventions/dispatch-and-routing.md`",
            content,
        )

    def test_shard_file_actually_contains_the_section(self):
        shard = _cached_read_text(self.SHARD_PATH)
        self.assertIn(self.HEADING, shard)

    def test_section_states_routing_rule(self):
        section = self._norm_section()
        self.assertIn("route it to `agents/forge-mobile.md` (persona Roam)",
                       section)
        self.assertIn("not `forge-ui`", section)

    def test_section_states_verification_rule(self):
        section = self._norm_section()
        self.assertIn(
            "use `agents/forge-mobile-verifier.md` (persona Lens)", section
        )

    def test_section_states_observation_surface(self):
        section = self._norm_section()
        self.assertIn("Android emulator via `adb`", section)
        self.assertIn("iOS Simulator via `xcrun simctl` (macOS hosts only)",
                       section)
        self.assertIn("never a web browser", section)

    def test_section_states_honest_degradation_rule(self):
        section = self._norm_section()
        self.assertIn(
            "degrade honestly: gate-level + static", section
        )
        self.assertIn("visual verification UNAVAILABLE on this host",
                       section)
        self.assertIn(
            "never a fabricated or browser-substituted visual pass",
            section,
        )

    # -- refreshed counts (23 -> 25) across roster surfaces --

    def test_agents_dir_has_exactly_twenty_five_files(self):
        files = sorted((REPO_ROOT / "agents").glob("*.md"))
        self.assertEqual(len(files), 25)

    def test_readme_agent_count_is_twenty_five(self):
        # Skill count bumped 48->52 (2026-07-21) when the longtail-skills
        # batch (i18n-and-localization, payment-integration-discipline,
        # email-and-templating, seo-fundamentals) shipped.
        # Bumped 57->58 (2026-07-21) when webgl-react-three-fiber (3D/WebGL
        # motion tier) shipped.
        # Bumped 58->60 (2026-07-21) when the cinematic-media pair
        # (cinematic-hero-sections, ai-generated-media-pipeline) shipped.
        readme = _cached_read_text(REPO_ROOT / "README.md")
        self.assertIn("a routed roster of twenty-five agents", readme)
        # 25 is the actual commands/*.md inventory count.
        self.assertIn("**61 skills · 25 agents · 26 commands**", readme)
        self.assertIn("Twenty-five routed agents, each spawned by the kernel",
                       readme)
        self.assertIn("| Roam | `forge-mobile` |", readme)
        self.assertIn("| Lens | `forge-mobile-verifier` |", readme)

    def test_map_agent_roster_states_twenty_five(self):
        content = _cached_read_text(
            REPO_ROOT / ".forge" / "map" / "subsystems" / "agent-roster.md"
        )
        self.assertIn("Twenty-five routed agents", content)
        self.assertIn("`forge-mobile`", content)
        self.assertIn("`forge-mobile-verifier`", content)

    def test_map_architecture_states_twenty_five_and_stays_under_ceiling(self):
        content = _cached_read_text(
            REPO_ROOT / ".forge" / "map" / "architecture.md"
        )
        self.assertIn("twenty-five routed agents", content)
        self.assertLessEqual(len(content), 8000)

    def test_docs_features_roster_states_twenty_five(self):
        content = _cached_read_text(REPO_ROOT / "docs" / "features" / "roster.md")
        self.assertIn("Twenty-five routed agents", content)
        self.assertIn("| Roam | `forge-mobile` |", content)
        self.assertIn("| Lens | `forge-mobile-verifier` |", content)

    def test_docs_architecture_states_twenty_five(self):
        content = _cached_read_text(REPO_ROOT / "docs" / "architecture.md")
        self.assertIn("25 routed agents plus the örn orchestrator", content)



class TestRnWebRulingPins(unittest.TestCase):
    """2026-07-21 human-ratified RN-web ruling: routing follows the
    rendered surface, never the source framework; dual-surface tasks are
    split before dispatch."""

    def _routing(self):
        return _cached_read_text(
            REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md")

    def test_ruling_heading_present_and_indexed(self):
        self.assertIn(
            "## Mobile routing — RN-web ruling — 2026-07-21",
            self._routing())
        index = _cached_read_text(REPO_ROOT / "docs" / "conventions.md")
        self.assertIn(
            "  - Mobile routing — RN-web ruling — 2026-07-21", index)
        self.assertIn(
            "- `Mobile routing — RN-web ruling — 2026-07-21` -> "
            "`docs/conventions/dispatch-and-routing.md`", index)

    def test_ruling_is_surface_based_not_framework_based(self):
        content = self._routing()
        self.assertIn(
            "routing follows the **rendered surface**, never the source\n"
            "framework", content)
        self.assertIn("Expo web export, React Native\n  Web target", content)

    def test_dual_surface_tasks_split_before_dispatch(self):
        content = self._routing()
        self.assertIn("**split before dispatch**", content)
        self.assertIn(
            "One task is\n  never closed with only one of its two declared "
            "surfaces verified.", content)


if __name__ == "__main__":
    unittest.main()
