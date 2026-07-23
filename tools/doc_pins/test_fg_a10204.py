"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10204`: TestFgA10204InquestPins.
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


class TestFgA10204InquestPins(unittest.TestCase):
    """Doc-pins for fg-a10204 (/forge:inquest adversarial deep-debug
    tribunal): the skill exists with its never-loop-initiated gate and
    three role contracts, the refuter's verdict bins, the judge's
    triage-routing table, the command and workflow files exist, and the
    conventions.md boundary + NORMATIVE verdict-vocabulary section survives
    alongside its TOC line. Command/skill count pins moving 18->19 are
    covered separately (TestFgA10101TelemetryPins.test_map_command_count_is_
    nineteen and test_readme_lists_telemetry_command, both updated by this
    same task) rather than re-pinned here.
    """

    def test_inquest_skill_exists_and_never_loop_initiated(self):
        skill_path = REPO_ROOT / "skills" / "inquest" / "SKILL.md"
        self.assertTrue(skill_path.exists(), "skills/inquest/SKILL.md missing")
        content = _cached_read_text(skill_path)
        self.assertIn("NEVER loop-initiated", content)
        self.assertIn("human ask or an accepted recommendation card", content)

    def test_inquest_skill_has_charter_requirement(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "inquest" / "SKILL.md"))
        self.assertIn("Charter first", content)
        self.assertIn("**Scope**", content)
        self.assertIn("**Budget**", content)
        self.assertIn("**Stop conditions**", content)

    def test_inquest_skill_has_three_role_contracts(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "inquest" / "SKILL.md"))
        self.assertIn("### FINDER", content)
        self.assertIn("### REFUTER", content)
        self.assertIn("### JUDGE", content)
        # FINDER: maximalist mindset + structured-finding fields
        self.assertIn("everything and anything might be a bug", content)
        self.assertIn("**Location**", content)
        self.assertIn("**Claim**", content)
        self.assertIn("**Concrete failure scenario**", content)
        self.assertIn("**Severity**", content)
        # JUDGE: weighs, never re-investigates
        self.assertIn("does not re-litigate or re-investigate", content)

    def test_inquest_skill_has_refuter_verdict_bins(self):
        """Pins the refuter's exact three-way verdict vocabulary plus the
        running-code-beats-argument rule, not just the headings."""
        content = _cached_read_text((REPO_ROOT / "skills" / "inquest" / "SKILL.md"))
        self.assertIn("**REFUTED**", content)
        self.assertIn("**CONFIRMED**", content)
        self.assertIn("**UNRESOLVED**", content)
        self.assertIn("Running code beats argument", content)
        self.assertIn(
            "outranks prose reasoning", re.sub(r"\s+", " ", content)
        )

    def test_inquest_skill_judge_routes_via_triage(self):
        """Pins the judge routing table: CONFIRMED -> forge:triage draft,
        DISMISSED -> recorded with reason, UNRESOLVED -> surfaced to human,
        and the nothing-silently-dropped guarantee."""
        content = _cached_read_text((REPO_ROOT / "skills" / "inquest" / "SKILL.md"))
        self.assertIn("Routes through the `forge:triage` door", content)
        self.assertIn("Constitution rule 1", content)
        self.assertIn("Recorded with the REFUTER's reason", content)
        self.assertIn("Surfaced to the human directly", content)
        self.assertIn("Nothing silently dropped", content)

    def test_inquest_skill_has_routing_tiers_and_boundary(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "inquest" / "SKILL.md"))
        self.assertIn("sonnet/high", content)
        self.assertIn(
            "equal-or-higher model tier than the FINDER it's attacking",
            content,
        )
        self.assertIn("opus/high", content)
        self.assertIn("Proportionality", content)
        self.assertIn("vs. `forge-debugger`", content)
        self.assertIn("vs. the finder pattern in report tasks", content)
        self.assertIn("vs. the verifier-finding filter", content)

    def test_inquest_command_exists(self):
        cmd_path = REPO_ROOT / "commands" / "inquest.md"
        self.assertTrue(cmd_path.exists(), "commands/inquest.md missing")
        content = _cached_read_text(cmd_path)
        self.assertIn("forge:inquest", content)

    def test_inquest_workflow_exists(self):
        wf_path = REPO_ROOT / "workflows" / "forge-inquest.md"
        self.assertTrue(wf_path.exists(), "workflows/forge-inquest.md missing")
        content = _cached_read_text(wf_path)
        self.assertIn("forge-inquest", content)
        self.assertIn("parallel(", content)
        self.assertIn("pipeline(", content)

    def test_conventions_has_inquest_section_and_toc_line(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("## Inquest tribunal — 2026-07", content)
        self.assertIn("- Inquest tribunal — 2026-07", content)

    def test_conventions_inquest_section_has_normative_verdict_vocabulary(self):
        content = conventions_corpus.corpus_text()
        section = content.split("## Inquest tribunal — 2026-07")[1]
        self.assertIn("Verdict vocabulary — NORMATIVE", section)
        self.assertIn("`REFUTED`", section)
        self.assertIn("`CONFIRMED`", section)
        self.assertIn("`UNRESOLVED`", section)
        self.assertIn("`DISMISSED`", section)

    def test_conventions_inquest_section_has_boundary(self):
        content = conventions_corpus.corpus_text()
        section = content.split("## Inquest tribunal — 2026-07")[1]
        self.assertIn("forge-debugger", section)
        self.assertIn("finder pattern in report tasks", section)
        self.assertIn("verifier-finding filter", section)
