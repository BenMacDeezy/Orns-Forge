"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0103`: TestFgF0103NameIdPins.
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


class TestFgF0103NameIdPins(unittest.TestCase):
    """fg-f0103: doc pins for the spec-f0c2 Amendments item 2 readable-name-id
    convention -- validator id-minting text in skills/queue and skills/spec,
    plus the docs/conventions.md dated amendment section. Pins semantic body
    text (not just headings), so a rename/gut of the actual rule fails these
    even if a heading survives."""

    def test_queue_skill_task_crud_mints_name_ids(self):
        content = _read_path(
            "skills/queue/references/task-crud.md")
        self.assertIn("human-readable kebab-case name", content)
        self.assertIn("spec-f0c2 Amendments item 2", content)
        self.assertIn(
            "Legacy `fg-`/`spec-` hex ids already in the queue are never "
            "renamed to this scheme.",
            content,
        )

    def test_spec_skill_mints_name_ids(self):
        content = _read_path("skills/spec/SKILL.md")
        self.assertIn("readable-kebab-case-name", content)
        self.assertIn("spec-f0c2 Amendments item 2", content)
        self.assertIn(
            "Legacy `spec-<hex>` ids already on disk are\n"
            "never renamed to this scheme.",
            content,
        )

    def test_conventions_has_readable_task_ids_section(self):
        content = _read_path("docs/conventions.md")
        self.assertIn("## Readable task ids — 2026-07-20", content)
        self.assertIn(
            '> Amends: "Offline merge convention" (above).',
            content,
        )
        self.assertIn(
            "checked unique against every id already in the\n"
            "repo before minting",
            content,
        )

    def test_conventions_extends_offline_merge_with_rename_on_collision(self):
        content = _read_path("docs/conventions.md")
        self.assertIn(
            "This extends the \"Offline merge convention\" collision rule "
            "(above) with\nrename-on-collision",
            content,
        )
        self.assertIn("`-2`, `-3`, ...", content)

    def test_conventions_toc_and_manifest_reference_new_section(self):
        raw = _cached_read_text(pathlib.Path(REPO_ROOT / "docs" / "conventions.md"))
        self.assertIn("  - Readable task ids — 2026-07-20", raw)
        self.assertIn(
            "- `Readable task ids — 2026-07-20` -> "
            "`docs/conventions/artifact-formats.md`",
            raw,
        )
