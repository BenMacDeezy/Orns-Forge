"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0105`: TestFgF0105CoordinationDocsPins.
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


class TestFgF0105CoordinationDocsPins(unittest.TestCase):
    """Doc-pin regression tests for fg-f0105 (dated conventions section for
    multi-operator coordination + fg-e103 superseded-by-spec frontmatter
    note): the new docs/conventions.md dated section citing
    coordination-gate.md by section number rather than restating it, its
    TOC/manifest entries, and fg-e103's task-file frontmatter note."""

    def _conventions_content(self):
        return _read_path("docs/conventions.md")

    def test_conventions_has_multi_operator_coordination_section(self):
        content = self._conventions_content()
        self.assertIn(
            "## Multi-operator coordination — 2026-07-20", content)
        self.assertIn(
            '> Amends: "Offline merge convention" (above).', content)

    def test_section_cites_coordination_gate_sections_by_number(self):
        content = self._conventions_content()
        self.assertIn(
            "`skills/kernel/references/coordination-gate.md` §§1-7 (not "
            "restated\n  here).",
            content,
        )
        self.assertIn("`coordination-gate.md` §11.", content)
        self.assertIn("`coordination-gate.md` §10.", content)

    def test_section_cites_readable_ids_without_restating(self):
        content = self._conventions_content()
        self.assertIn(
            "see \"Readable task\n  ids — 2026-07-20\" (above), not "
            "restated here.",
            content,
        )

    def test_section_notes_notification_channel_dropped(self):
        content = self._conventions_content()
        self.assertIn(
            "spec-f0c2's outbound-only notification\n  channel design "
            "point (decomposition item 5) was dropped entirely at\n  "
            "ratification (Amendments item 3)",
            content,
        )

    def test_section_notes_sync_cadence_human_override_precedence(self):
        content = self._conventions_content()
        self.assertIn(
            "an explicit human instruction to\n  push elsewhere takes "
            "precedence over this multi-operator default for\n  that "
            "push",
            content,
        )

    def test_conventions_toc_and_manifest_reference_new_section(self):
        raw = _cached_read_text(pathlib.Path(REPO_ROOT / "docs" / "conventions.md"))
        self.assertIn(
            "  - Multi-operator coordination — 2026-07-20", raw)
        self.assertIn(
            "- `Multi-operator coordination — 2026-07-20` -> "
            "`docs/conventions/artifact-formats.md`",
            raw,
        )

    def test_fg_e103_task_carries_superseded_by_spec(self):
        content = _read_path(
            ".forge/queue/tasks/"
            "fg-e103-offline-multi-machine-safety-for-the-que.md"
        )
        self.assertIn("superseded-by-spec: spec-f0c2", content)
        self.assertIn("state: done", content)
        self.assertIn(
            "Widened id regex to fg-/spec-[0-9a-f]{4,8} (backward "
            "compatible), 6-hex new ids, offline merge convention "
            "appended. Gates: 102 tests pass, validators 0 errors.",
            content,
        )
