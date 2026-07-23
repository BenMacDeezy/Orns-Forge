"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-f0106`: TestFgF0106RosterGatingPins.
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


class TestFgF0106RosterGatingPins(unittest.TestCase):
    """Doc-pin regression tests for fg-f0106 (roster gating): the new §10
    in coordination-gate.md that narrows §5's peer-manifest read procedure
    to rostered operators when `.forge/coordination/roster.md` exists,
    open-by-default when it doesn't, and never-lockout on a malformed
    roster (spec-f0c2 Clarifications item 4)."""

    def _gate_content(self):
        path = REPO_ROOT / "skills" / "kernel" / "references" / "coordination-gate.md"
        return _cached_read_text(path)

    def test_roster_gating_section_exists(self):
        content = self._gate_content()
        self.assertIn("## 11. Roster gating (`fg-f0106`)", content)

    def test_roster_file_path_and_minimal_shape_pinned(self):
        content = self._gate_content()
        self.assertIn("`.forge/coordination/roster.md`", content)
        self.assertIn(
            "one operator handle per bullet line (`- <handle>`", content
        )
        self.assertIn("git-tracked", content)

    def test_present_roster_narrows_to_listed_operators_and_logs_unrostered(self):
        content = self._gate_content()
        self.assertIn(
            "**WHEN `.forge/coordination/roster.md` exists**, THE SYSTEM "
            "SHALL apply §5's\nread procedure (claim-exclusion, §6 "
            "staleness rule) only to peer manifests\nwhose `operator` "
            "field matches a handle listed in the roster.",
            content,
        )
        self.assertIn(
            "SHALL be logged as\nexactly one session-report note", content
        )
        self.assertIn(
            "SHALL NOT be honored for claim-exclusion", content
        )
        self.assertIn(
            "an\nunrostered manifest can never lock a rostered peer out of "
            "the claimable\nset",
            content,
        )

    def test_missing_roster_stays_open_by_default(self):
        content = self._gate_content()
        self.assertIn(
            "**WHEN no roster file exists** at "
            "`.forge/coordination/roster.md`, THE\nSYSTEM SHALL honor "
            "every manifest per §5 exactly as before this section\n"
            "existed — open-by-default, current behavior unchanged.",
            content,
        )

    def test_malformed_roster_degrades_to_open_never_lockout(self):
        content = self._gate_content()
        self.assertIn("**Failure direction:**", content)
        self.assertIn("SHALL degrade to\nopen-by-default", content)
        self.assertIn("SHALL NEVER degrade to\nlockout", content)

    def test_section_5_cross_references_roster_gating(self):
        content = self._gate_content()
        self.assertIn(
            "see §11 for the\nroster-gating narrowing this procedure is "
            "subject to when a roster file\nexists",
            content,
        )

    def test_non_goals_no_longer_defers_roster_gating(self):
        content = self._gate_content()
        self.assertNotIn("No roster/allowlist gating", content)
        self.assertIn(
            "## 8. Non-goals of this file\n\nNo notification\n"
            "channel of any kind",
            content,
        )

    def test_kernel_step_anchor_mapping_still_intact(self):
        # §9's heading and body must survive this task's insertion of §10
        # after it (siblings/future readers rely on this exact anchor).
        content = self._gate_content()
        self.assertIn("## 9. Kernel-step anchor mapping (`fg-f0102`)", content)
        self.assertIn(
            "**Session end** (queue drained, budget cap, or an explicit "
            "stop) -> mark\n  own manifest `ended` (§3, \"Session end\").",
            content,
        )
