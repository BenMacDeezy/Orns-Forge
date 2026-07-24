"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9d0101`: TestFg9d0101EquipPins.
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


class TestFg9d0101EquipPins(unittest.TestCase):
    """Doc-pins for fg-9d0101 (/forge:equip): the skill exists with its trust
    preamble and proposes-only/consent anchors, the command exists and is
    listed in the README, and the equip-vs-scout/discover/onboard/seed
    boundary section is present in conventions.md — mirrors the pin style
    used for other command+skill additions (e.g. TestFg9c0304Pins) so a
    future rewrite of the surrounding prose can't silently gut the load-
    bearing anchors this test checks for.
    """

    def test_equip_skill_has_trust_preamble(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "equip" / "SKILL.md"))
        self.assertIn("## Trust preamble", content)
        self.assertIn(
            "untrusted iff neither `.forge/.provenance` nor `.forge/.trust-local` exists",
            content,
        )

    def test_equip_skill_has_proposes_only_consent_anchor(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "equip" / "SKILL.md"))
        self.assertIn("## 4. CONSENT", content)
        self.assertIn(
            "Nothing is installed, created, queued, or enabled without explicit approval",
            content,
        )

    def test_equip_skill_has_gap_classes_and_action_menu(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "equip" / "SKILL.md"))
        for cls in ("MISSING", "WEAK", "MISWIRED"):
            self.assertIn(cls, content)
        for action in ("FIND", "CREATE", "WIRE", "SKIP"):
            self.assertIn(f"**{action}**", content)

    def test_equip_command_exists(self):
        cmd_path = REPO_ROOT / "commands" / "equip.md"
        self.assertTrue(cmd_path.exists(), "commands/equip.md missing")
        content = _cached_read_text(cmd_path)
        self.assertIn("forge:equip", content)

    def test_readme_has_equip_row(self):
        readme = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("/forge:equip", readme)

    def test_conventions_has_equip_boundary_section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("## Capability-gap audits (equip)", content)
        self.assertIn("decides whether and why a gap exists", content)
        self.assertIn("forge:discover", content)
        self.assertIn("forge:onboard", content)
        self.assertIn("forge:seed", content)
        self.assertIn("forge:scout", content)

    def test_equip_inventory_section_pinned(self):
        """Pins the INVENTORY section heading and evidence-only MCP fragment
        so future rewrites can't silently remove the capability inventory
        requirement or the definition that 'connected' is evidence-only."""
        content = _cached_read_text((REPO_ROOT / "skills" / "equip" / "SKILL.md"))
        self.assertIn("## 1. INVENTORY", content)
        self.assertIn(
            "Evidence-only: an MCP server counts as",
            content,
        )

    def test_equip_no_charter_path_pinned(self):
        """Pins the no-charter-yet section heading and the lower-confidence
        labeling requirement so future rewrites can't drop the degraded-pass
        pathway or remove the accountability that non-charter-derived findings
        must be labeled as lower-confidence."""
        content = _cached_read_text((REPO_ROOT / "skills" / "equip" / "SKILL.md"))
        self.assertIn("## No charter yet", content)
        self.assertIn(
            "in that pass clearly as **lower-confidence**",
            content,
        )
