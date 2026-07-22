"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0310`: TestFgB0310DispatchProvenanceFlagPins.
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


class TestFgB0310DispatchProvenanceFlagPins(unittest.TestCase):
    """fg-b0310 (spec-b71f3a): the dispatch-provenance flag hook
    (hooks/scripts/agent-provenance-flag.sh) -- dated conventions.md
    section, TOC entry + Amended-by pointer nested under "Universal
    Forge-agent dispatch — 2026-07-19", and the four pinned facts every
    reader of that section needs: what's logged/where, the hook never
    denies, budget-guard.sh stays the only blocking hook, and the
    generic-transport limitation is stated rather than hidden.
    """

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    HEADING = "## Dispatch-provenance flag — 2026-07-19 (fg-b0310, spec-b71f3a)"
    PARENT_HEADING = (
        "## Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)"
    )

    @staticmethod
    def _read(path):
        return _read_path(path)

    def _section(self):
        content = self._read(self.CONVENTIONS_PATH)
        return content.split(self.HEADING, 1)[1].split("\n## ", 1)[0]

    def _norm_section(self):
        # Whitespace-normalized (markdown line-wrap-tolerant) view, matching
        # the pattern established by TestFgB0303EphemeralDispatchMechanicsPins
        # for pinning prose that spans a hard line wrap.
        return " ".join(self._section().split())

    def test_conventions_has_dated_heading(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(self.HEADING, content)

    def test_conventions_toc_entry_nested_under_universal_dispatch(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            "  - Universal Forge-agent dispatch — 2026-07-19 "
            "(fg-b0303, spec-b71f3a)\n"
            "    - Dispatch-provenance flag — 2026-07-19 "
            "(fg-b0310, spec-b71f3a)\n",
            content,
        )

    def test_conventions_parent_section_has_amended_by_pointer(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            self.PARENT_HEADING + "\n\n"
            '> Amended by: "Dispatch-provenance flag — 2026-07-19 '
            '(fg-b0310, spec-b71f3a)"',
            content,
        )

    def test_new_section_amends_pointer_back_to_parent(self):
        section = self._norm_section()
        self.assertIn(
            '"Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, '
            'spec-b71f3a)"',
            section,
        )

    def test_section_cites_spec_and_hook_file(self):
        section = self._section()
        self.assertIn(
            ".forge/specs/2026-07-19-universal-agent-dispatch-lifecycle.md",
            section,
        )
        self.assertIn("Install-time ecosystem enforcement", section)
        self.assertIn("hooks/scripts/agent-provenance-flag.sh", section)
        self.assertIn("hooks/hooks.json", section)

    def test_section_states_what_and_where_is_logged(self):
        section = self._section()
        self.assertIn(".forge/telemetry/dispatch-provenance.log", section)
        self.assertIn("UTC timestamp", section)
        self.assertIn("subagent_type", section)

    def test_section_states_never_denies(self):
        section = self._norm_section()
        self.assertIn("this hook never returns a deny decision", section)
        self.assertIn("always exits 0", section)

    def test_section_states_budget_guard_stays_only_blocking_hook(self):
        section = self._norm_section()
        self.assertIn(
            "budget-guard.sh` remains the only hook allowed to block a "
            "dispatch",
            section,
        )

    def test_section_states_generic_transport_limitation(self):
        section = self._section()
        self.assertIn("Generic-transport limitation, stated rather than hidden",
                       section)
        self.assertIn(
            "this is a documented limit of the hook's vantage point, "
            "not an oversight",
            section,
        )

    def test_section_states_fail_silent_scope(self):
        section = self._section()
        self.assertIn("No `.forge/` present -> silent", section)
        self.assertIn("fail-silent doctrine", section)

    def test_hook_script_exists_and_registered(self):
        script = REPO_ROOT / "hooks" / "scripts" / "agent-provenance-flag.sh"
        self.assertTrue(script.is_file())
        hooks_json = _cached_read_text((REPO_ROOT / "hooks" / "hooks.json"))
        self.assertIn("agent-provenance-flag.sh", hooks_json)
        self.assertIn('"matcher": "Task|Agent"', hooks_json)
