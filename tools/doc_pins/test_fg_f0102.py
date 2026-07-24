"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0102`: TestFgF0102SyncPullWiringPins.
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


class TestFgF0102SyncPullWiringPins(unittest.TestCase):
    """Doc-pin regression tests for fg-f0102 (presence-sync-pull-wiring):
    the four short NORMATIVE citation lines skills/kernel/SKILL.md carries
    at SYNC/PULL/milestone-boundary/session-end, plus
    coordination-gate.md's kernel-step anchor mapping they point at --
    pinned so a future edit can't silently drop the pull-before-claim
    exclusion or the milestone/session-end manifest updates."""

    def _skill_content(self):
        path = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
        return _cached_read_text(path)

    def _gate_content(self):
        path = REPO_ROOT / "skills" / "kernel" / "references" / "coordination-gate.md"
        return _cached_read_text(path)

    def test_sync_cites_presence_manifest_write(self):
        content = self._skill_content()
        self.assertIn(
            "- **Presence manifest.** Write/refresh own manifest —\n"
            "  `skills/kernel/references/coordination-gate.md` §3. NORMATIVE.",
            content,
        )

    def test_pull_cites_pull_before_claim_exclusion(self):
        content = self._skill_content()
        self.assertIn(
            "first read peer presence manifests and\n"
            "exclude their claimed tasks/wave boundaries (pull-before-claim —\n"
            "`coordination-gate.md` §5–§6, NORMATIVE), then compute the wave",
            content,
        )

    def test_milestone_boundary_cites_manifest_update(self):
        content = self._skill_content()
        self.assertIn(
            "**Presence manifest.** Update own manifest at this claim, at wave dispatch,\n"
            "and at INTEGRATE — `coordination-gate.md` §3 Milestone-boundary update.\n"
            "NORMATIVE.",
            content,
        )

    def test_session_end_cites_manifest_ended(self):
        content = self._skill_content()
        self.assertIn(
            "**Presence manifest.** At session end, mark own manifest `ended` —\n"
            "`coordination-gate.md` §3 Session end. NORMATIVE.",
            content,
        )

    def test_coordination_gate_has_kernel_step_anchor_mapping(self):
        content = self._gate_content()
        self.assertIn(
            "## 9. Kernel-step anchor mapping (`fg-f0102`)", content
        )
        for anchor in (
            "**SYNC** -> write/refresh own manifest",
            "**PULL**, before the wave is computed",
            "**Milestone boundary** (a task claim, a wave dispatch, or an INTEGRATE)",
            "**Session end** (queue drained, budget cap, or an explicit stop)",
        ):
            self.assertIn(anchor, content)

    def test_non_goals_no_longer_fences_kernel_wiring(self):
        content = self._gate_content()
        self.assertNotIn("No kernel-loop wiring", content)
        # fg-f0106 built roster gating; the old "not built by this task"
        # fencing sentence is gone from §8 (superseded by §10).
        self.assertNotIn(
            "that gate is not\nbuilt by this task (`fg-f0106`)", content
        )
