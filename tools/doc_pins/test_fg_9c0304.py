"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9c0304`: TestFg9c0304Pins.
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


class TestFg9c0304Pins(unittest.TestCase):
    """Doc-pins for fg-9c0304: UI/motion agent attachments + handoff citation,
    discover onboard-first card, and command next-step pointers.

    The citation pin doubles as a regression pin for the FAIL-NOTE-1 fix
    (agents/forge-ui.md and agents/forge-animator.md previously cited
    docs/conventions.md as "UI+motion splitting", which is NOT a substring of
    the corrected "UI+motion task splitting" — the missing "task " makes this
    pin revert-red: reverting the citation fix makes these assertions fail
    again, they don't just degrade to a looser match.
    """

    def test_forge_ui_has_attached_skills_and_citation(self):
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-ui.md"))
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)
        self.assertIn("UI+motion task splitting", content)

    def test_forge_animator_has_attached_skills_and_citation(self):
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-animator.md"))
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)
        self.assertIn("UI+motion task splitting", content)

    def test_forge_ui_verifier_has_attached_skills(self):
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-ui-verifier.md"))
        self.assertIn("visual-polish-and-craft", content)
        self.assertIn("webapp-visual-testing", content)

    def test_discover_has_onboard_first_nudge(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "discover" / "SKILL.md"))
        self.assertIn("Onboard-first nudge", content)
        self.assertIn("Set up Forge fully first (onboard", content)
        self.assertIn("Just run discovery (minimal init)", content)

    def test_triage_command_points_to_forge_start(self):
        content = _cached_read_text((REPO_ROOT / "commands" / "triage.md"))
        self.assertIn("/forge:start", content)

    def test_spec_command_points_to_forge_start(self):
        content = _cached_read_text((REPO_ROOT / "commands" / "spec.md"))
        self.assertIn("/forge:start", content)
