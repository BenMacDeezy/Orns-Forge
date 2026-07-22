"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0204`: TestFgB0204EquipPortProposalCardPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestFgB0204EquipPortProposalCardPins(unittest.TestCase):
    """Doc-pins for fg-b0204 (spec-6b7c, "Agent porting and lifecycle"):
    the PORT proposal card added to `forge:equip`'s existing FIND/CREATE/
    WIRE/SKIP surface (commands/equip.md, skills/equip/SKILL.md), handing
    off to `/forge:port` on approval rather than restating its flow. Every
    substring below is unique to text this task added -- never a phrase
    commands/port.md or tools/port_agent.py already owns in text this task
    cites but does not restate."""

    EQUIP_CMD_PATH = REPO_ROOT / "commands" / "equip.md"
    EQUIP_SKILL_PATH = REPO_ROOT / "skills" / "equip" / "SKILL.md"

    def _equip_cmd(self):
        return _cached_read_text(self.EQUIP_CMD_PATH)

    def _equip_skill(self):
        return _cached_read_text(self.EQUIP_SKILL_PATH)

    def test_equip_command_file_exists(self):
        self.assertTrue(self.EQUIP_CMD_PATH.exists())

    def test_equip_skill_file_exists(self):
        self.assertTrue(self.EQUIP_SKILL_PATH.exists())

    def test_equip_command_proposal_cards_add_port(self):
        content = self._equip_cmd()
        self.assertIn(
            "- Present a ranked proposal via structured option cards — "
            "FIND / CREATE /\n  WIRE / SKIP per gap, plus PORT wherever "
            "the inventory turned up a\n  non-Forge agent file.",
            content,
        )
        self.assertIn(
            "Install, create, queue, port, or enable NOTHING\n  without "
            "explicit approval on the cards.",
            content,
        )

    def test_equip_command_still_names_find_create_wire_skip(self):
        # AC2: adding PORT must not remove/rename the existing four verbs.
        content = self._equip_cmd()
        for verb in ("FIND", "CREATE", "WIRE", "SKIP"):
            self.assertIn(verb, content)

    def test_equip_skill_inventory_flags_non_forge_agent_files(self):
        content = self._equip_skill()
        self.assertIn(
            "Also note any non-Forge\n  agent definition found in project "
            "or user space — a Claude Code subagent\n  outside "
            "`.forge/agents/`",
            content,
        )
        self.assertIn(
            "the shapes `tools/port_agent.py`'s\n  `detect_source_format` "
            "classifies.",
            content,
        )
        self.assertIn(
            "This is inventory only — equip doesn't\n  run the detector "
            "itself, it flags the file as a PORT candidate for §3.",
            content,
        )

    def test_equip_skill_proposal_names_port_card(self):
        content = self._equip_skill()
        self.assertIn(
            "- **PORT** — offered only for a discovered non-Forge agent "
            "file (§1(b)).",
            content,
        )
        self.assertIn(
            "Names the discovered source path and its detected format",
            content,
        )
        self.assertIn(
            "`claude-subagent` / `crewai-langchain` / `bare-system-prompt` "
            "/\n  `unrecognized`",
            content,
        )

    def test_equip_skill_port_card_cites_forge_port_flow_not_restated(self):
        content = self._equip_skill()
        self.assertIn(
            "states what approving it would produce: `/forge:port`'s\n  "
            "own guided flow — parse, map, a side-by-side diff plus "
            "compatibility note,\n  one structured approval, nothing "
            "written until that approval\n  (`commands/port.md`).",
            content,
        )
        self.assertIn(
            "Equip never restates or re-runs that flow itself —\n  "
            "approving the PORT card hands off directly to `/forge:port "
            "<path>`, which\n  owns its own approval gate from there.",
            content,
        )

    def test_equip_skill_consent_section_covers_approved_port(self):
        content = self._equip_skill()
        self.assertIn(
            "An approved PORT item hands off to `/forge:port <path>` "
            "immediately —\nequip's own approval on the card only "
            "authorizes starting that flow, not\nthe port itself; "
            "`/forge:port` runs its own step-4 approval (diff +\n"
            "compatibility note) before writing anything "
            "(`commands/port.md`).",
            content,
        )

    def test_equip_skill_boundary_lists_forge_port(self):
        content = self._equip_skill()
        self.assertIn(
            "- **vs `/forge:port`** — equip only detects that a non-Forge "
            "agent file\n  exists and offers the PORT hand-off card; "
            "`/forge:port` owns the entire\n  guided conversion (parse, "
            "map, diff, compatibility note, approval, write).\n  Equip "
            "never parses the source file, never runs `port_agent.py`, "
            "and never\n  writes to `.forge/agents/` itself.",
            content,
        )

    def test_equip_skill_existing_verbs_unchanged_wording_present(self):
        # AC2: FIND/CREATE/WIRE/SKIP bullets from before this task still
        # carry their pre-existing contract text, untouched by the PORT
        # addition.
        content = self._equip_skill()
        self.assertIn(
            "- **FIND** — route to `forge:scout` for that specific gap;",
            content,
        )
        self.assertIn(
            "- **CREATE** — queue a skill-authoring task via `forge:queue`",
            content,
        )
        self.assertIn(
            "- **WIRE** — attach an existing-but-unattached skill to the "
            "agent that needs",
            content,
        )
        self.assertIn(
            "- **SKIP** — record the decision so re-runs don't re-nag",
            content,
        )


if __name__ == "__main__":
    unittest.main()
