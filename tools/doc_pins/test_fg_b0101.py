"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0101`: TestFgB0101PersistenceBoundaryPins.
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


class TestFgB0101PersistenceBoundaryPins(unittest.TestCase):
    """fg-b0101 (spec-4d2a): the customization-persistence contract's
    docs/conventions.md dated section — plugin-cache/user-space/
    project-space tier definitions, update-survival guarantees, and the
    tools/validate_persistence_boundary.py gate description."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    CONVENTIONS_HEADING = (
        "## Customization persistence contract — 2026-07-18 (fg-b0101)"
    )
    VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_persistence_boundary.py"

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(self.CONVENTIONS_HEADING, c)

    def test_toc_lists_the_new_section(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Customization persistence contract — 2026-07-18 (fg-b0101)",
            c,
        )

    def test_manifest_maps_section_to_config_and_features_shard(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(
            "`Customization persistence contract — 2026-07-18 (fg-b0101)` "
            "-> `docs/conventions/config-and-features.md`",
            c,
        )

    def test_three_tiers_named_with_update_survival_guarantees(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn("**Plugin cache**", c)
        self.assertIn("**Update-survival guarantee: none.**", c)
        self.assertIn("**User space**", c)
        self.assertIn("**Project space**", c)
        self.assertEqual(
            c.count("**Update-survival guarantee: byte-for-byte unchanged**"),
            2,
        )

    def test_plugin_cache_tier_names_claude_plugin_root(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", c)

    def test_gate_tool_named_with_offending_file_line_behavior(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn("tools/validate_persistence_boundary.py", c)
        self.assertIn(
            "fails with the offending `file:line` if one is found", c
        )

    def test_validator_module_exists(self):
        self.assertTrue(self.VALIDATOR_PATH.is_file())

    def test_validator_docstring_states_what_it_does_not_catch(self):
        content = _cached_read_text(self.VALIDATOR_PATH)
        self.assertIn("WHAT THIS DOES NOT CATCH", content)
