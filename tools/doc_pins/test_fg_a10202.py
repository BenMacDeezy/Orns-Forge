"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10202`: TestFgA10202GraphPins.
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


class TestFgA10202GraphPins(unittest.TestCase):
    """Doc-pins for fg-a10202 (queue dependency DAG): the tool + its test
    file exist, `/forge:status --graph` is documented in commands/status.md,
    and the queue skill's Status board section offers the graph for
    multi-task waves, naming tools/queue_graph.py."""

    def test_queue_graph_tool_exists(self):
        self.assertTrue((REPO_ROOT / "tools" / "queue_graph.py").is_file())

    def test_queue_graph_test_file_exists(self):
        self.assertTrue((REPO_ROOT / "tools" / "test_queue_graph.py").is_file())

    def test_status_command_documents_graph_flag(self):
        content = _cached_read_text((REPO_ROOT / "commands" / "status.md"))
        self.assertIn("--graph", content)
        self.assertIn("tools/queue_graph.py", content)

    def test_queue_skill_status_board_offers_graph(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "queue" / "SKILL.md"))
        section = content.split("## Status board")[1].split("## Timestamps")[0]
        self.assertIn("tools/queue_graph.py", section)
        self.assertIn("3+", section)
