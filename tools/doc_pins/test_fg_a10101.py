"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10101`: TestFgA10101TelemetryPins.
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


class TestFgA10101TelemetryPins(unittest.TestCase):
    """Doc-pins for fg-a10101: /forge:telemetry command surface, wired into
    README + the map's count-consistency pin, plus its own NORMATIVE
    vocabulary section and skill boundary line."""

    def test_telemetry_command_and_skill_files_exist(self):
        self.assertTrue((REPO_ROOT / "commands" / "telemetry.md").exists())
        self.assertTrue((REPO_ROOT / "skills" / "telemetry" / "SKILL.md").exists())
        self.assertTrue((REPO_ROOT / "tools" / "telemetry.py").exists())

    def test_readme_lists_telemetry_command(self):
        # "26 commands" (not 19): inventory count from commands/*.md.
        # bumping the count. This pin lives in a test file, not README.md
        # itself -- fg-a10904 does not touch README (fg-a10903 owns README
        # this wave; the count is already updated there to "26 commands"),
        # it only keeps this hardcoded companion pin in sync with it.
        readme = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("/forge:telemetry", readme)
        self.assertIn("26 commands", readme)

    def test_map_command_count_is_twenty(self):
        """Regression companion to test_map_command_count_consistent above:
        pins the literal spelled-out word so a future drift back to
        "nineteen" without updating the count fails here even if the
        3-way pin's arithmetic happened to still agree by coincidence.

        Bumped 19->20 by fg-a10904 (commands/banner.md added the
        `/forge:banner` entry point; this is the commands-count surface the
        task's bounce scope item 4 required fixing -- the pin lives in
        .forge/map/architecture.md, NOT README.md, so no coordination with
        fg-a10903 (README owner) was needed). Bumped 20->21 at the
        2026-07-18 map refresh (commands/update.md added /forge:update,
        fg-a10914); the sibling pin's capture regex also gained hyphen
        support, since no non-hyphenated English word for 21 exists. Bumped
        to 23 by court-system-spec-review (commands/court.md added
        /forge:court, the adversarial five-phase document trial). Bumped
        23->24 by fg-b0203 (commands/port.md added /forge:port, the guided
        agent-porting flow). Bumped 24->25 by prd-blueprint-command
        (commands/blueprint.md added /forge:blueprint, the PRD -> advisory
        wave/parallelization blueprint command)."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertIn("Twenty-six thin slash-command entry points", content)

    def test_conventions_has_telemetry_vocabulary_section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("## Telemetry vocabulary — 2026-07", content)
        self.assertIn("attempt N: dispatched", content)
        self.assertIn("attempt N verify:", content)
        self.assertIn("attempt N (bounce,", content)
        self.assertIn("MECHANICAL", content)
        self.assertIn("JUDGMENT", content)
        self.assertIn("kernel-inline", content)

    def test_telemetry_skill_has_boundary_vs_status_and_coverage_rule(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "telemetry" / "SKILL.md"))
        self.assertIn("Boundary vs `/forge:status`", content)
        self.assertIn("current state", content)
        self.assertIn("history across attempts", content)
        self.assertIn("Honest-coverage rule", content)
        self.assertIn("never silently dropped and never crashes", content)

    def test_telemetry_command_is_read_only(self):
        content = _cached_read_text((REPO_ROOT / "commands" / "telemetry.md"))
        self.assertIn(
            "never writes `.forge/`, transitions a task, or\ncommits anything",
            content,
        )

    def test_skill_count_consistent(self):
        """Verify the skill count — README claim, map prose, and actual
        skill directories on disk — all agree.

        Three independent surfaces claim to describe "how many skills Forge
        has": the README prose (e.g. "42 skills"), the map's intro paragraph
        (spelled out, e.g. "Forty-two skills"), and the real skill directories
        with SKILL.md files on disk. They can silently drift from each other
        when a skill is added/removed and only one surface gets updated —
        this pin catches that drift.
        """
        # Count actual skill directories with SKILL.md files
        actual_skills = list((REPO_ROOT / "skills").glob("*/SKILL.md"))
        actual_count = len(actual_skills)

        # Parse count from README (format: "**42 skills")
        readme_content = _cached_read_text((REPO_ROOT / "README.md"))
        readme_match = re.search(r"\*\*(\d+)\s+skills\b", readme_content)
        self.assertIsNotNone(
            readme_match,
            "README prose ('<N> skills') not found",
        )
        readme_count = int(readme_match.group(1))

        # Parse count from map prose (format: "Forty-two skills, nineteen...")
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        map_content = _cached_read_text(map_path)
        # fg-forge-mobile-agent (2026-07-21) bumped the map's agent count
        # 20->25 ("twenty routed agents" -> "twenty-five routed agents");
        # match any spelled-out count word here rather than hardcoding one,
        # since this pin only cares about the *skills* count agreeing.
        map_match = re.search(
            r"\b([A-Za-z-]+)\s+skills,\s+[a-z-]+\s+routed\s+agents",
            map_content
        )
        self.assertIsNotNone(
            map_match,
            "Map prose ('<N> skills, <N> routed agents') not found",
        )
        word = map_match.group(1).lower()
        self.assertIn(
            word, _WORD_TO_INT,
            f"unrecognized spelled-out number {word!r} in map prose",
        )
        map_count = _WORD_TO_INT[word]

        # Assert all three agree
        self.assertEqual(
            actual_count, readme_count,
            f"Actual skills on disk: {actual_count}, but README claims {readme_count}",
        )
        self.assertEqual(
            actual_count, map_count,
            f"Actual skills on disk: {actual_count}, but map prose says {map_count}",
        )
