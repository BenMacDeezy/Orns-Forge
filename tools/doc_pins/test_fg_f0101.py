"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0101`: TestFgF0101PresenceManifestPins.
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


class TestFgF0101PresenceManifestPins(unittest.TestCase):
    """Doc-pin regression tests for fg-f0101 (presence manifest format):
    skills/kernel/references/coordination-gate.md's schema, write/read/
    staleness procedure, and non-goals -- pinned so a future edit can't
    silently drop the 4-hour Amendments-governed staleness threshold, the
    explicit `ended` field (never deletion), or the git-tracked directory
    rule."""

    def _content(self):
        path = REPO_ROOT / "skills" / "kernel" / "references" / "coordination-gate.md"
        return _cached_read_text(path)

    def test_manifest_path_and_schema_fields_present(self):
        content = self._content()
        self.assertIn(
            "`.forge/coordination/<operator-handle>.md`", content
        )
        for field in (
            "**`operator`**",
            "**`machine label`**",
            "**`branch`**",
            "**`claimed task ids`**",
            "**`in-flight wave boundary file paths`**",
            "**`started`**",
            "**`updated`**",
            "**`ended`**",
        ):
            self.assertIn(field, content)

    def test_ended_field_is_never_deletion(self):
        content = self._content()
        self.assertIn(
            "the same manifest is never\n  deleted on end, only updated with "
            "this one additional field",
            content,
        )

    def test_staleness_threshold_pinned_to_four_hours_amendments_governed(self):
        content = self._content()
        self.assertIn(
            "**Pin — staleness-threshold:** peer-manifest staleness is "
            "**4 hours**",
            content,
        )
        self.assertIn(
            "This value is fixed by spec-f0c2's Amendments section (which\n"
            "GOVERNS over the spec body's earlier "
            '"[resolved 2026-07-20: 4 hours]"',
            content,
        )
        self.assertIn("claim-staleness-hours", content)

    def test_stale_manifest_degrades_to_advisory_not_exclusion(self):
        content = self._content()
        self.assertIn(
            "THE SYSTEM SHALL treat that manifest as\nADVISORY ONLY",
            content,
        )
        self.assertIn(
            "log one session-report note", content
        )

    def test_coordination_directory_is_git_tracked(self):
        content = self._content()
        self.assertIn(
            "The directory is git-tracked (committed, not gitignored)",
            content,
        )

    def test_operator_handle_defers_to_fg_f0103_without_restating(self):
        content = self._content()
        self.assertIn(
            "decomposition item 3's\nconvention (`fg-f0103`, sibling work "
            "under the same spec), cited here\nwithout restating",
            content,
        )

    def test_non_goals_exclude_kernel_wiring_roster_cadence_and_notifications(self):
        content = self._content()
        self.assertIn("## 8. Non-goals of this file", content)
        self.assertIn(
            "## 9. Kernel-step anchor mapping (`fg-f0102`)", content
        )
        self.assertIn("`.forge/coordination/roster.md`", content)
        self.assertIn("`fg-f0104`", content)
        self.assertIn(
            "No notification\nchannel of any kind — dropped entirely at "
            "ratification (Amendments item\n3) and out of scope "
            "permanently, not merely deferred.",
            content,
        )
