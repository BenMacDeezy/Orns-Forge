"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0203`: TestFgB0203PortCommandPins.
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


class TestFgB0203PortCommandPins(unittest.TestCase):
    """Doc-pins for fg-b0203 (spec-6b7c, "Agent porting and lifecycle"):
    commands/port.md, the new `/forge:port` guided-conversion command, plus
    the map/README/docs count-surface refresh (23 -> 24 commands) its
    addition to commands/*.md required. Every substring below is unique to
    text this task added -- never a phrase agent.md, uninstall.md, or
    port_agent.py already owns in text this task cites but does not
    restate."""

    PORT_PATH = REPO_ROOT / "commands" / "port.md"

    def _port(self):
        return _cached_read_text(self.PORT_PATH)

    def test_port_command_file_exists(self):
        self.assertTrue(self.PORT_PATH.exists())

    def test_port_frontmatter_description_and_argument_hint(self):
        content = self._port()
        self.assertIn(
            "description: Guided port of an existing custom agent (Claude "
            "Code subagent, CrewAI/LangChain, or bare system prompt) into "
            "a Forge project-local agent, human-approved before anything "
            "is written",
            content,
        )
        self.assertIn('argument-hint: "[<source-path>]"', content)

    def test_port_drives_python_api_not_detector_only_main(self):
        content = self._port()
        self.assertIn(
            "It drives `tools/port_agent.py`'s\nPython API directly — "
            "`detect_source_format` (fg-b0201) and\n"
            "`map_source_to_agent_fields` (fg-b0202) — never the module's "
            "own `main()`,\nwhich is detector-only",
            content,
        )
        self.assertIn(
            "Never runs `port_agent.py`'s own `main()` as the entry "
            "point", content,
        )

    def test_port_no_path_form_scans_and_presents_candidates(self):
        content = self._port()
        self.assertIn(
            "Scan `~/.claude/agents/` and other common harness\n"
            "  agent-definition locations",
            content,
        )
        self.assertIn(
            "proceed with the\n  approved candidate exactly as the path "
            "form would",
            content,
        )
        self.assertIn("spec-6b7c clarification 5", content)

    def test_port_unrecognized_format_stops_no_guessed_mapping(self):
        content = self._port()
        self.assertIn(
            "**Unrecognized stops\n   here**: report the reason and do "
            "not guess a mapping (spec-6b7c AC1).",
            content,
        )

    def test_port_credential_findings_kind_and_count_never_value(self):
        content = self._port()
        self.assertIn(
            "`credential_findings` are reported as **kind + count only**",
            content,
        )
        self.assertIn(
            "the matched\n  value itself is never shown in the diff, the "
            "compat note, the chat\n  transcript, or any written file",
            content,
        )

    def test_port_never_silently_drops_a_source_feature(self):
        content = self._port()
        self.assertIn(
            "A source feature Forge cannot represent 1:1 (an unexposed "
            "tool, a\n  multi-agent crew topology, a memory/vector-store "
            "dependency) is always\n  named, never silently absorbed into "
            "the port.",
            content,
        )

    def test_port_provenance_block_records_source_path_and_format(self):
        content = self._port()
        self.assertIn(
            "- ported: yes\n   - source-path: <resolved source path>\n   "
            "- source-format: claude-subagent | crewai-langchain | "
            "bare-system-prompt",
            content,
        )
        self.assertIn(
            'This is the record spec-6b7c AC requires — "a Provenance '
            'block recording\n   it was ported and from what source path '
            'and format" — never omitted,',
            content,
        )

    def test_port_single_structured_approval_bundles_diff_and_compat_note(self):
        content = self._port()
        self.assertIn(
            "Present exactly one `AskUserQuestion`", content,
        )
        self.assertIn(
            "1. **The side-by-side diff** — source definition (as read) "
            "vs. the\n   generated `.forge/agents/<name>.md` content "
            "assembled in step 2.",
            content,
        )
        self.assertIn(
            "2. **The full compatibility note** — every `compat_notes` "
            "entry and every\n   `credential_findings` kind+count, never "
            "truncated.",
            content,
        )

    def test_port_nothing_written_before_approval_sentence(self):
        content = self._port()
        self.assertIn(
            "**Nothing is written to disk until this question is "
            "answered `Approve`.**",
            content,
        )
        self.assertIn(
            "No partial write, no draft file, no scratch copy — the diff "
            "and compat note\nare held in memory/chat only until approval.",
            content,
        )

    def test_port_approval_writes_canonical_plus_mirror_no_registration_step(self):
        content = self._port()
        self.assertIn(
            "write the assembled content to\n  `.forge/agents/<name>.md`",
            content,
        )
        self.assertIn(
            "then mirror it byte-for-byte to `.claude/agents/<name>.md`\n"
            "  exactly per the existing project-local-agent convention",
            content,
        )
        self.assertIn(
            "no separate registration step, no queue\n  task, no index "
            "file to update",
            content,
        )
        self.assertIn("spec-6b7c AC3", content)

    def test_port_decline_writes_nothing(self):
        content = self._port()
        self.assertIn(
            "**On decline:** write nothing. No partial file, no log entry "
            "beyond this\n  session's own chat transcript, no queue task.",
            content,
        )

    def test_port_never_does_list_covers_automatic_unattended(self):
        content = self._port()
        self.assertIn(
            "- Never performs an automatic or unattended port — every "
            "port is a human\n  decision on the step 4 structured "
            "question, every session.",
            content,
        )

    def test_readme_lists_port_command_row(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn(
            "| `/forge:port` | Guided, human-approved port of an existing "
            "custom agent into `.forge/agents/` |",
            content,
        )

    def test_map_architecture_names_port_entry_point_and_count(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertIn(
            "- `/forge:port [<path>]` → `commands/port.md`: guided agent "
            "port, human-approved write.",
            content,
        )
        # prd-blueprint-command bumped this 24->25 (commands/blueprint.md
        # added /forge:blueprint); this pin now asserts the current count,
        # not the count port's own addition produced.
        self.assertIn("twenty-six slash commands", content)
        self.assertIn(
            "Twenty-six thin slash-command entry points",
            content,
        )

    def test_map_architecture_under_char_ceiling(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertLessEqual(len(content), 8000)

    def test_map_subsystems_commands_names_port(self):
        subsys_path = (
            REPO_ROOT / ".forge" / "map" / "subsystems" / "commands.md"
        )
        if not subsys_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(subsys_path)
        self.assertIn("Twenty-six thin slash-command entry points", content)
        self.assertIn("`port`", content)
        self.assertIn(
            "`port` (`fg-b0203`, spec-6b7c) is the guided agent-porting "
            "flow",
            content,
        )

    def test_docs_architecture_names_twenty_four_commands(self):
        content = _read_path("docs/architecture.md")
        self.assertIn(
            "Twenty-six thin slash-command entry points under "
            "`commands/*.md`",
            content,
        )


    def test_port_name_collision_never_silently_overwrites(self):
        """2026-07-20 retro-verify P1 fix: an existing agent at the target
        path must surface a prominent overwrite warning with an
        existing-vs-generated diff, Rename recommended, and explicit
        destructive wording -- never a silent replace."""
        content = _cached_read_text(REPO_ROOT / "commands" / "port.md")
        self.assertIn("Name-collision check — runs BEFORE the approval "
                      "question is shown.", content)
        self.assertIn("overwrites an existing agent", content)
        self.assertIn("existing-target vs. generated", content)
        self.assertIn("`Rename (recommended)`", content)
        self.assertIn(
            "NEVER allowed to silently replace an\nexisting agent", content)



if __name__ == "__main__":
    unittest.main()
