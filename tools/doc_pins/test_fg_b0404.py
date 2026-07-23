"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0404`: TestFgB0404WorktreeDisciplineSkillPins.
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


class TestFgB0404WorktreeDisciplineSkillPins(unittest.TestCase):
    """Pins for fg-b0404: skills/worktree-discipline/SKILL.md — the worker-side
    worktree contract, its two agent attachment lines, and the audit's three
    P2 forbidden-action classes each adapted extract must never reintroduce.
    """

    SKILL_PATH = REPO_ROOT / "skills" / "worktree-discipline" / "SKILL.md"
    WORKER_PATH = REPO_ROOT / "agents" / "forge-worker.md"
    MIGRATOR_PATH = REPO_ROOT / "agents" / "forge-migrator.md"

    def _skill_content(self):
        return _cached_read_text(self.SKILL_PATH)

    def test_skill_file_exists(self):
        self.assertTrue(self.SKILL_PATH.is_file())

    def test_skill_has_stay_in_worktree_phrase(self):
        content = self._skill_content()
        self.assertIn(
            "Work exclusively inside the worktree path named in your "
            "spawn contract",
            content,
        )

    def test_skill_has_never_commit_phrase(self):
        content = self._skill_content()
        self.assertIn(
            "Never commit, push, branch-switch, or run any `git worktree` "
            "command",
            content,
        )

    def test_skill_has_provenance_gated_cleanup_phrase(self):
        content = self._skill_content()
        self.assertIn("provenance-gated", content)
        self.assertIn(
            "Whoever CREATED the worktree owns its cleanup", content
        )

    def test_skill_has_kernel_owned_integrate_phrase(self):
        content = self._skill_content()
        self.assertIn("INTEGRATE is kernel-owned", content)

    def test_skill_cites_parallel_dispatch_reference(self):
        content = self._skill_content()
        self.assertIn(
            "skills/kernel/references/parallel-dispatch.md", content
        )

    def test_skill_has_all_four_attribution_comments(self):
        """Each of the four copy-adapted extracts must carry its own
        attribution comment naming superpowers 6.1.1 and the source skill —
        never a live-cite of the plugin cache (2026-07-19 forge-security
        audit version-drift ruling)."""
        content = self._skill_content()
        self.assertIn(
            "<!-- adapted from superpowers 6.1.1 using-git-worktrees -->",
            content,
        )
        self.assertIn(
            "<!-- adapted from superpowers 6.1.1 "
            "finishing-a-development-branch -->",
            content,
        )
        self.assertEqual(
            content.count(
                "<!-- adapted from superpowers 6.1.1 "
                "subagent-driven-development -->"
            ),
            2,
        )

    def test_skill_has_three_forbidden_action_classes(self):
        """The audit's three P2 conflict classes must be named explicitly
        so adapted prose can never reintroduce them."""
        content = self._skill_content()
        section = content.split("## Forbidden actions")[1]
        self.assertIn("Never self-merge to any base branch", section)
        self.assertIn("delete branches", section)
        self.assertIn("Never dispatch a raw generic subagent", section)
        self.assertIn(
            "Never keep progress or state in any store outside `.forge/`",
            section,
        )

    def test_worker_has_worktree_discipline_attachment(self):
        content = _cached_read_text(self.WORKER_PATH)
        section = content.split("## Attached skills")[1].split("##")[0]
        self.assertIn("- worktree-discipline —", section)

    def test_migrator_has_worktree_discipline_attachment(self):
        content = _cached_read_text(self.MIGRATOR_PATH)
        section = content.split("## Attached skills")[1].split("##")[0]
        self.assertIn("- worktree-discipline —", section)
