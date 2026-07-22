"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10802`: TestFgA10802GruntPins.
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


class TestFgA10802GruntPins(unittest.TestCase):
    """Doc-pins for fg-a10802 (Grud, the goblin grunt / forge-grunt): the
    new roster agent's haiku/low + no-craft-skills + refuse-on-judgment
    contract, the canonical "Grud routing" conventions section (routing
    rule, the Grud-vs-Tern boundary, verification inheritance tied to the
    Low-risk predicate -- not a blanket exemption, persona registration),
    the README roster row, the kernel ROUTE citation line + char ceiling,
    and the 19->20 count-surface bump this task rides in on.
    """

    AGENT_PATH = REPO_ROOT / "agents" / "forge-grunt.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    README_PATH = REPO_ROOT / "README.md"
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    GRUD_ROUTE_LINE = (
        "Zero-judgment fully-specified bulk -> forge-grunt haiku/low; "
        "boundary vs migrator: conventions 'Grud routing'. NORMATIVE."
    )

    def _agent_content(self):
        return _cached_read_text(self.AGENT_PATH)

    def _conventions_content(self):
        return _read_path(self.CONVENTIONS_PATH)

    def _readme_content(self):
        return _cached_read_text(self.README_PATH)

    def _kernel_content(self):
        return _cached_read_text(self.KERNEL_PATH)

    # -- EARS clause 1: agent file, haiku/low, no craft skills, refuse-on-judgment --

    def test_agent_file_exists(self):
        self.assertTrue(self.AGENT_PATH.is_file())

    def test_agent_frontmatter_model_is_haiku(self):
        content = self._agent_content()
        frontmatter = content.split("---", 2)[1]
        m = re.search(r"^model:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "haiku")

    def test_agent_display_name_is_grud(self):
        content = self._agent_content()
        frontmatter = content.split("---", 2)[1]
        m = re.search(r"^display-name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Grud")

    def test_agent_default_routing_is_haiku_low_always(self):
        content = self._agent_content()
        section = content.split("## Default routing")[1].split("##")[0]
        self.assertIn("haiku / low, always", section)

    def test_agent_has_no_craft_skills(self):
        content = self._agent_content()
        section = content.split("## Attached skills")[1].split("##")[0]
        self.assertIn("none", section)

    def test_agent_refuses_on_judgment_call(self):
        normalized = re.sub(r"\s+", " ", self._agent_content())
        self.assertIn("REFUSE-AND-RETURN", normalized)
        self.assertIn(
            "if the contract requires ANY judgment call", normalized
        )
        self.assertIn(
            "bounce the whole task back to the kernel unexecuted",
            normalized,
        )

    def test_agent_output_contract_has_refused_result(self):
        content = self._agent_content()
        self.assertIn("RESULT: completed | refused | blocked", content)

    def test_agent_forbidden_actions_never_touch_forge_dir(self):
        content = self._agent_content()
        section = content.split("## Forbidden actions")[1]
        self.assertIn("Never touch `.forge/`.", section)

    # -- EARS clause 4 / boundary: Grud vs Tern, quote-matched wording --

    def test_conventions_has_grud_routing_heading(self):
        content = self._conventions_content()
        self.assertIn("## Grud routing (goblin grunt) \u2014 2026-07-18", content)

    def test_conventions_grud_routing_in_toc(self):
        content = self._conventions_content()
        self.assertIn("- Grud routing (goblin grunt) \u2014 2026-07-18", content)

    def _grud_section(self):
        content = self._conventions_content()
        return content.split("## Grud routing (goblin grunt) \u2014 2026-07-18")[1]

    def test_conventions_routing_rule_present(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "WHEN the kernel faces fully-specified, zero-judgment bulk "
            "work", normalized,
        )
        self.assertIn(
            "THE SYSTEM SHALL route it to `forge-grunt`, always dispatched "
            "at **haiku/low**", normalized,
        )
        self.assertIn("Grud #1..#N", normalized)

    def test_conventions_boundary_vs_migrator_stated(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "Grud vs Tern (`forge-migrator`) \u2014 the boundary, stated so "
            "they never overlap", normalized,
        )
        self.assertIn("Judgment about WHAT to change", normalized)
        self.assertIn(
            "Fully specified and only executed", normalized
        )

    def test_conventions_verification_inheritance_not_a_blanket_exemption(self):
        """EARS clause 3 (verify) + the fg-a10815-inherited rule this task
        must quote-match, not paraphrase into a new blanket exemption."""
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn(
            "a mechanical-tier slug does not get a looser bar", normalized
        )
        self.assertIn(
            "never a blanket \"mechanical \u2192 optional verify\" exemption "
            "invented for this persona", normalized,
        )
        self.assertIn(
            "Skip per-shard EARS verify \u2014 tied to Low-risk verification, "
            "not a blanket exemption", normalized,
        )
        self.assertIn("Gates-green \u2260 acceptance-met", normalized)

    def test_conventions_persona_registration(self):
        normalized = re.sub(r"\s+", " ", self._grud_section())
        self.assertIn('"Grud (grunt)"', normalized)
        self.assertIn('"Grud #1..#N (grunt)"', normalized)
        self.assertIn("| forge-grunt | Grud |", self._grud_section())
        self.assertIn("20th agent", normalized)

    # -- README roster row --

    def test_readme_has_grud_roster_row(self):
        content = self._readme_content()
        self.assertIn(
            "| Grud | `forge-grunt` |", content
        )

    def test_readme_agent_count_is_twenty_three(self):
        # "26 commands" (not 19): inventory count from commands/*.md.
        # bumping the count. Same rule as
        # TestFgA10101TelemetryPins.test_readme_lists_telemetry_command --
        # the pin is a hardcoded companion in this test file, not README.md
        # itself, which fg-a10904 does not touch (fg-a10903 owns README
        # this wave, and already carries "26 commands"). Agent count bumped
        # 20->23 (2026-07-19) when the inquest tribunal's three roles
        # (Hound/Foil/Gavel) were roster-ified out of generic dispatch.
        # Skill count bumped 44->45 (fg-b0404, 2026-07-19) when
        # skills/worktree-discipline/SKILL.md was added.
        # Skill count bumped 45->48 (2026-07-20) when the mobile/React-perf
        # trio (react-performance, react-native-performance,
        # react-native-foundations) was added.
        # Agent count bumped 23->25 (forge-mobile-agent, 2026-07-21) when
        # the forge-mobile / forge-mobile-verifier pair was roster-ified.
        # Skill count bumped 48->52 (2026-07-21) when the longtail-skills
        # batch (i18n-and-localization, payment-integration-discipline,
        # email-and-templating, seo-fundamentals) shipped.
        content = self._readme_content()
        self.assertIn("a routed roster of twenty-five agents", content)
        self.assertIn("**61 skills \u00b7 25 agents \u00b7 26 commands**", content)
        self.assertIn("Twenty-five routed agents, each spawned by the kernel", content)

    # -- Kernel ROUTE citation line + char ceiling --

    def test_kernel_has_grud_route_line(self):
        content = self._kernel_content()
        self.assertIn(self.GRUD_ROUTE_LINE, content)
        route_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        verify_heading_idx = content.index("### 6. VERIFY")
        line_idx = content.index(self.GRUD_ROUTE_LINE)
        self.assertLess(route_heading_idx, line_idx)
        self.assertLess(line_idx, verify_heading_idx)

    def test_kernel_skill_within_char_ceiling(self):
        """Same pre-existing 31,617-char ceiling as the three/four prior
        instances (grep 31617) -- this task's trim-to-fit addition must
        still clear it, not regress the kernel back toward its
        pre-restructure size."""
        content = self._kernel_content()
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    # -- Count surfaces say 20 --

    def test_agents_dir_has_exactly_twenty_three_files(self):
        # Bumped 23->25 (forge-mobile-agent, 2026-07-21): forge-mobile.md +
        # forge-mobile-verifier.md added.
        files = sorted((REPO_ROOT / "agents").glob("*.md"))
        self.assertEqual(len(files), 25)
