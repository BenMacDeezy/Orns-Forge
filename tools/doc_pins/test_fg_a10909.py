"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10909`: TestFgA10909HumanTaskNamePins.
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


class TestFgA10909HumanTaskNamePins(unittest.TestCase):
    """fg-a10909: every human surface leads with the task's short name, id
    trailing in parens; ids stay the only load-bearing join key."""

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    def test_task_name_amendment_present_and_binding(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Dispatch display labels — task-name amendment — 2026-07-18", c
        )
        self.assertIn("with the id trailing in parens", c)
        self.assertIn("never a bare `fg-xxxx`", c)
        self.assertIn("Ids remain the ONLY join key", c)

    def test_version_skew_nudge_in_status_command(self):
        # fg-a10907 rider: the status surface carries the once-per-session
        # version-skew line, fail-silent.
        s = self._norm("commands/status.md")
        self.assertIn("Version-skew nudge (fg-a10907", s)
        self.assertIn("restart at the next milestone boundary", s)
        self.assertIn("stay silent (fail-silent, zero protocol weight)", s)
