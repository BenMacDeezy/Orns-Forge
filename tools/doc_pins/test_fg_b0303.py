"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0303`: TestFgB0303EphemeralDispatchMechanicsPins.
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


class TestFgB0303EphemeralDispatchMechanicsPins(unittest.TestCase):
    """fg-b0303 (spec-b71f3a, bm-ephemeral-dispatch-mechanics): the kernel
    transport rule for archive-tier dispatch (harness generic subagent_type
    as transport, archive-file content as the spawn contract, the file
    authors the dispatch), the VERIFY mode 3 finder-pattern carve-out
    realigned to route through fast-path minting, and the dated
    conventions.md amendment converting "Prefer the agent factory over ad
    hoc generic dispatch" and "Report tasks (finder pattern)" from
    prefer/recurrence-gated to mandatory -- dated heading + TOC entries +
    Amended-by pointers on both base sections. Covers all 3 EARS clauses in
    the task file.
    """

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617
    CONVENTIONS_HEADING = (
        "## Universal Forge-agent dispatch — 2026-07-19 "
        "(fg-b0303, spec-b71f3a)"
    )

    @staticmethod
    def _read(path):
        return _read_path(path)

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    # -- conventions.md: dated heading + TOC + Amended-by pointers --------

    def test_conventions_has_dated_heading(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(self.CONVENTIONS_HEADING, content)

    def test_conventions_toc_entry_under_report_tasks(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Report tasks (finder pattern) — 2026-07-17\n"
            "  - UI+motion task splitting, empty-repo gates-pending, and "
            "finder dispatch — 2026-07-18 (also amends forge.md (project "
            "config), above)\n"
            "  - Universal Forge-agent dispatch — 2026-07-19 "
            "(fg-b0303, spec-b71f3a)",
            content,
        )

    def test_conventions_toc_entry_under_prefer_the_factory(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Prefer the agent factory over ad hoc generic dispatch — "
            "2026-07-19\n"
            "  - Universal Forge-agent dispatch — 2026-07-19 "
            "(fg-b0303, spec-b71f3a) (also amends Report tasks (finder "
            "pattern), above)",
            content,
        )

    def test_conventions_report_tasks_base_section_amended_by_pointer(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            '## Report tasks (finder pattern) — 2026-07-17\n\n'
            '> Amended by: "UI+motion task splitting, empty-repo '
            'gates-pending, and finder dispatch — 2026-07-18", '
            '"Universal Forge-agent dispatch — 2026-07-19 '
            '(fg-b0303, spec-b71f3a)"',
            content,
        )

    def test_conventions_prefer_factory_base_section_amended_by_pointer(self):
        content = self._read(self.CONVENTIONS_PATH)
        self.assertIn(
            '## Prefer the agent factory over ad hoc generic dispatch — '
            '2026-07-19\n\n'
            '> Amended by: "Universal Forge-agent dispatch — 2026-07-19 '
            '(fg-b0303, spec-b71f3a)"',
            content,
        )

    # -- mandatory language: "never"/"instead of" on BOTH amended behaviors

    def test_conventions_prefer_factory_amended_to_mandatory(self):
        section = self._norm(self.CONVENTIONS_PATH).split(
            self.CONVENTIONS_HEADING
        )[1].split("## ")[0]
        self.assertIn(
            'the "single genuinely one-off exploration... can stay '
            'generic" carve-out is withdrawn', section,
        )
        self.assertIn("mints an archive-tier ephemeral agent via the fast path INSTEAD of staying generic", section)
        self.assertIn(
            "never dispatch raw generic; mint instead", section
        )

    def test_conventions_finder_pattern_amended_to_mandatory(self):
        section = self._norm(self.CONVENTIONS_PATH).split(
            self.CONVENTIONS_HEADING
        )[1].split("## ")[0]
        self.assertIn(
            "a report task's finder now mints an archive-tier agent via "
            "the fast path before dispatch, never a raw generic dispatch "
            "with no backing file", section,
        )

    def test_conventions_states_why_now_control_moved_to_promotion_retention(self):
        # Spec item 6 / AC3: explicit about WHAT changed and WHY -- minting
        # is now cheap; the anti-graveyard control moved from gating
        # creation to gating promotion + retention.
        section = self._norm(self.CONVENTIONS_PATH).split(
            self.CONVENTIONS_HEADING
        )[1].split("## ")[0]
        self.assertIn("now cheap and non-blocking", section)
        self.assertIn(
            "the anti-graveyard control that used to gate CREATION now "
            "gates PROMOTION", section,
        )
        self.assertIn("never creation", section)

    def test_conventions_cites_fast_path_and_ephemeral_tier_not_restated(self):
        section = self._norm(self.CONVENTIONS_PATH).split(
            self.CONVENTIONS_HEADING
        )[1].split("## ")[0]
        self.assertIn(
            'Fast path (kernel-initiated ephemeral minting)', section
        )
        self.assertIn(
            "Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)",
            section,
        )
        self.assertIn("cited here rather than restated", section)

    def test_conventions_dispatch_mechanics_transport_rule(self):
        # AC1/AC5/AC9: harness generic/catch-all subagent_type as
        # transport, full archive-file content injected as the spawn
        # contract, the file authors the dispatch; cites the kernel rather
        # than restating.
        section = self._norm(self.CONVENTIONS_PATH).split(
            self.CONVENTIONS_HEADING
        )[1].split("## ")[0]
        self.assertIn("harness's generic/catch-all `subagent_type` as transport", section)
        self.assertIn(
            "injecting the full `.forge/agents/archive/<name>.md` file's "
            "content as the spawn contract", section,
        )
        self.assertIn("the persisted file authors the dispatch", section)
        self.assertIn("File existence is a precondition of dispatch, not a follow-up", section)
        self.assertIn("skills/kernel/SKILL.md", section)

    # -- kernel: transport rule phrasing + char ceiling --------------------

    def test_kernel_mint_before_dispatch_extended_with_transport_rule(self):
        # Extends (does not duplicate) the Mint-before-dispatch bullet
        # landed by fg-b0302.
        content = self._norm(self.KERNEL_PATH)
        self.assertIn(
            "**Mint-before-dispatch.** No fitting agent -> fast-path mint "
            '(agent-factory "Fast path") first; file precedes dispatch.',
            content,
        )
        self.assertIn(
            "Archive-tier: harness generic subagent_type as transport, "
            "file content as spawn contract — the file authors the "
            "dispatch.",
            content,
        )

    def test_kernel_verify_mode_3_realigned_no_raw_generic_carveout(self):
        # VERIFY mode 3's finder route no longer describes itself as a
        # bare "generic read-only agent dispatch, no roster agentType" --
        # it now mints via the fast path before dispatch, consistent with
        # the universal-dispatch invariant (no remaining raw-generic path).
        # fg-b0402 (deviation beyond the architect's 8-pin repoint list):
        # the finder detail this pin inspects moved verbatim from
        # skills/kernel/SKILL.md to skills/kernel/references/verify-modes.md
        # in the same slimming pass that moved the other finder pin
        # (test_kernel_finder_stub_has_pointer_and_enforcement_condition);
        # this pin was not in the architect's explicit repoint list but
        # reads the exact same moved block, so it is repointed identically
        # -- pin STRINGS unchanged, only the file read and the section
        # marker (the numbered "3." list marker is kernel-structural and
        # does not exist in the reference file's own heading).
        ref_path = REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"
        content = re.sub(r"\s+", " ", _cached_read_text(ref_path))
        section = content.split(
            "**Finder / kernel-synthesis (report tasks only).**"
        )[1]
        self.assertNotIn("no roster", section)
        self.assertIn(
            "The finder route now mints via the fast path before "
            "dispatch, never raw generic", section,
        )
        self.assertIn(
            '"Report tasks (finder pattern),"',
            section,
        )
        self.assertIn("no-open-ended-exploration rule is not implicated", section)

    def test_kernel_no_remaining_raw_generic_dispatch_language(self):
        # Sanity sweep: "generic" appears only in the two sanctioned
        # spots (the harness subagent_type transport rule, and the
        # finder-route realignment note) -- no stray carve-out survives.
        # fg-b0402 (deviation beyond the architect's 8-pin repoint list):
        # the finder-route "generic" occurrence moved out of
        # skills/kernel/SKILL.md into references/verify-modes.md alongside
        # the rest of the finder detail (see the repoint note on
        # test_kernel_verify_mode_3_realigned_no_raw_generic_carveout,
        # above); the kernel now carries exactly ONE "generic" occurrence
        # (the harness subagent_type transport rule) and the reference file
        # carries the other -- same total of two sanctioned spots, split
        # across the two files the finder move created.
        kernel_content = _cached_read_text(self.KERNEL_PATH)
        self.assertEqual(kernel_content.count("generic"), 1)
        ref_content = _cached_read_text((
            REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"
        ))
        self.assertEqual(ref_content.count("generic"), 1)

    def test_kernel_skill_within_char_ceiling(self):
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)
