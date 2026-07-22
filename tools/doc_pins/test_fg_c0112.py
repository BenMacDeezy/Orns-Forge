"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0112`: TestFgC0112ProviderDocsAndConventionsPins.
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


class TestFgC0112ProviderDocsAndConventionsPins(unittest.TestCase):
    """Pins for fg-c0112 (spec-e8a3): the five normative provider-dispatch
    rules' load-bearing phrases, both new dated-section headings, and both
    new Shards-manifest rows."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
