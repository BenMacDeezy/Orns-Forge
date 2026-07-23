"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0302`: TestFgB0302FastPathMintFlowPins.
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


class TestFgB0302FastPathMintFlowPins(unittest.TestCase):
    """fg-b0302 (spec-b71f3a, bm-fast-path-mint-flow): the kernel-inline
    ephemeral minting flow -- agent-factory SKILL.md's new "Fast path"
    section (mechanical checklist run inline, no separate spawn, no
    `AskUserQuestion`, three-namespace no-roster-duplication scan,
    checklist-failure falls through to the nearest fitting existing agent
    rather than an ungated dispatch, every mint logged) and the kernel's
    ROUTE + DISPATCH mint-before-dispatch precondition, landed within the
    pre-existing 31,617-char ceiling via zero-normative-loss trims. Covers
    all 5 EARS clauses (AC4-AC8 in the task file).
    """

    AGENT_FACTORY_PATH = REPO_ROOT / "skills" / "agent-factory" / "SKILL.md"
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617
    FAST_PATH_HEADING = "## Fast path (kernel-initiated ephemeral minting)"

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = _read_path(path)
        return " ".join(text.split())

    def test_fast_path_heading_exists(self):
        # The new section heading, verbatim.
        content = _cached_read_text(self.AGENT_FACTORY_PATH)
        self.assertIn(self.FAST_PATH_HEADING, content)

    def test_fast_path_section_cites_spec_and_kernel(self):
        section = self._norm(self.AGENT_FACTORY_PATH).split(
            "## Fast path (kernel-initiated ephemeral minting)"
        )[1].split("## Seeding rules")[0]
        self.assertIn("spec-b71f3a", section)
        self.assertIn("skills/kernel/SKILL.md", section)
        self.assertIn("AC4", section)
        self.assertIn("AC5", section)
        self.assertIn("AC7", section)
        self.assertIn("AC8", section)

    def test_fast_path_runs_inline_no_spawn_no_ask_user_question(self):
        # AC4: mechanical checklist run inline, no separate spawn, no
        # AskUserQuestion.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn("run inline, no separate spawn, no `AskUserQuestion`", section)
        self.assertIn("no spawn, no `AskUserQuestion`", section)

    def test_fast_path_three_namespace_dup_scan(self):
        # AC5: agents/*.md, .forge/agents/*.md, .forge/agents/archive/*.md,
        # same scan commands/agent.md step 1 performs; a match routes to
        # the existing agent instead of minting.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn(
            "scan `agents/*.md`, `.forge/agents/*.md`, and "
            "`.forge/agents/archive/*.md` by name + description",
            section,
        )
        self.assertIn("commands/agent.md` step 1 performs", section)
        self.assertIn(
            "A match in ANY namespace routes the dispatch to that "
            "existing agent instead of minting",
            section,
        )

    def test_fast_path_checklist_failure_falls_through_never_ungated(self):
        # AC7: a failing checklist item means NO file is written and the
        # kernel falls through to the nearest fitting existing agent --
        # never an ungated dispatch.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn("A failing item means the file is NOT written", section)
        self.assertIn(
            "falls through to the nearest fitting existing agent "
            "(roster, project-local, or archive) instead", section,
        )
        self.assertIn("never an ungated dispatch", section)

    def test_fast_path_template_fill_and_direct_archive_write(self):
        # AC6: all six body sections plus Provenance with lifecycle:
        # ephemeral, written directly to .forge/agents/archive/<name>.md.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn(
            "fill all six body sections (Mission, Attached skills, "
            "Default routing, Rules, Output contract, Forbidden actions) "
            "plus Provenance with `lifecycle: ephemeral`", section,
        )
        self.assertIn(
            "write directly to `.forge/agents/archive/<name>.md`", section
        )
        self.assertIn("never mirrored to `.claude/agents/`", section)

    def test_fast_path_logs_every_mint(self):
        # AC8: every fast-path mint logged in the session report (name,
        # scope, rationale, source-task id), same rule as "Log every
        # creation", no reduction for being non-interactive.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn(
            "Every fast-path mint is recorded in the session report",
            section,
        )
        self.assertIn('per "Log every', section)
        self.assertIn("no reduction for being non-interactive", section)

    def test_fast_path_agent_or_skill_first_decision_unchanged(self):
        # Spec AC (universal dispatch): a genuine skill still defers to
        # skill-creator, never forced into a fast-path agent.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn("First decision unchanged", section)
        self.assertIn("defers to `skill-creator`", section)

    def test_fast_path_never_targets_forge_agent_command(self):
        # /forge:agent stays the untouched human-initiated route; the fast
        # path is a separate, kernel-only surface.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn("kernel-only creation surface", section)
        self.assertIn("`/forge:agent` stays the untouched human-initiated route", section)

    def test_fast_path_defers_dispatch_mechanics_to_fg_b0303(self):
        # This task builds the mint flow only, not the harness-transport
        # dispatch mechanics (fg-b0303's boundary) -- cited forward, not
        # built here.
        section = self._norm(self.AGENT_FACTORY_PATH)
        self.assertIn("land with fg-b0303, not here", section)

    def test_kernel_cites_mint_before_dispatch_precondition(self):
        # Kernel ROUTE + DISPATCH carries the mint-before-dispatch
        # citation: no fitting agent -> fast-path mint via agent-factory,
        # THEN dispatch; the file's existence precedes the dispatch.
        content = self._norm(self.KERNEL_PATH)
        section = content.split("### 5. ROUTE + DISPATCH")[1].split(
            "### 6. VERIFY"
        )[0]
        self.assertIn("Mint-before-dispatch", section)
        self.assertIn(
            "No fitting agent -> fast-path mint (agent-factory "
            '"Fast path") first; file precedes dispatch', section,
        )
        # The precondition precedes the actual dispatch sentence -- file's
        # existence precedes dispatch, never a follow-up.
        mint_idx = section.index("Mint-before-dispatch")
        dispatch_idx = section.index(
            "Dispatch `forge-worker` (or a fitter agent) with the contract"
        )
        self.assertLess(mint_idx, dispatch_idx)

    def test_kernel_skill_within_char_ceiling(self):
        # Hard ceiling from the task contract: the kernel file must stay
        # under the pre-existing 31,617-char budget after displacement
        # (grep 31617 -- prior instances of this same shared ceiling).
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)
