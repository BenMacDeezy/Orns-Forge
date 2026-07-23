"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10207`: TestFgA10207ArchitectRefuterPins.
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


class TestFgA10207ArchitectRefuterPins(unittest.TestCase):
    """Doc-pins for fg-a10207 (architect-plan refuter): the canonical dated
    conventions section (heading + TOC line), the checklist-cited-not-
    restated anchor, the checklist-gated trigger sentence, the no-match
    proceed-as-today sentence, the irreconcilable-disagreement-to-human
    sentence, the kernel PLAN citation by exact section name, and
    forge-architect's output-contract refuted-plan note.

    Covers all 3 EARS clauses: (1) checklist-gated trigger runs ONE refuter
    pass at equal-or-higher tier attacking DECISIONS/TRADE-OFFS/BLAST
    RADIUS before decomposition, verdict handed to the kernel alongside the
    architect's OPEN QUESTIONS; (2) no match -> proceed as today, no
    refuter, no added cost; (3) irreconcilable disagreement -> both
    positions surfaced to the human, kernel never silently picks.
    """

    SECTION_HEADING = "## Architect-plan refuter — 2026-07"

    def test_conventions_has_section_heading_and_toc_line(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn("- Architect-plan refuter — 2026-07", content)

    def test_conventions_section_cites_checklist_not_restated(self):
        """Pins that the checklist is cited by name/location (tier-escalation
        checklist in skills/spec/SKILL.md) rather than copied into this
        section — a future edit can't quietly turn this into a stale
        duplicate of the categories already listed in skills/spec/SKILL.md."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("tier-escalation checklist", normalized)
        self.assertIn("skills/spec/SKILL.md", normalized)
        self.assertIn("never repeats those items", normalized)
        # The checklist's own category words must NOT be duplicated here.
        for word in ("auth/authz", "PII/user data", "money/payments"):
            self.assertNotIn(word, normalized)

    def test_conventions_section_has_checklist_gated_trigger_sentence(self):
        """EARS clause 1: checklist-gated trigger runs ONE refuter pass at
        equal-or-higher tier attacking DECISIONS/TRADE-OFFS/BLAST RADIUS
        before decomposition, verdict handed to the kernel alongside the
        architect's own OPEN QUESTIONS."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN a `forge-architect` plan's BOUNDARIES or BLAST RADIUS "
            "touches the tier-escalation checklist, THE SYSTEM SHALL run "
            "ONE refuter pass",
            normalized,
        )
        self.assertIn("equal-or-higher model tier", normalized)
        self.assertIn(
            "attacking the plan's DECISIONS, TRADE-OFFS, and BLAST RADIUS "
            "before decomposition",
            normalized,
        )
        self.assertIn(
            "handed to the kernel alongside the architect's own OPEN "
            "QUESTIONS",
            normalized,
        )

    def test_conventions_section_has_no_match_proceeds_as_today_sentence(self):
        """EARS clause 2: no checklist match -> proceed exactly as today, no
        refuter, no added cost."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN the plan does not touch the checklist, THE SYSTEM SHALL "
            "proceed exactly as today — no refuter pass, no added cost",
            normalized,
        )

    def test_conventions_section_has_disagreement_to_human_sentence(self):
        """EARS clause 3: irreconcilable disagreement -> both positions
        surfaced to the human, kernel never silently picks a side."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "WHEN the refuter and the architect disagree irreconcilably, "
            "THE SYSTEM SHALL surface BOTH positions to the human",
            normalized,
        )
        self.assertIn("the kernel never silently picks a side", normalized)

    def test_conventions_section_has_no_finder_no_judge_scope_note(self):
        """Pins the scope-limiting sentence: this is one pass, not a full
        tribunal — no FINDER, no JUDGE role."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("One pass, not a tribunal", normalized)
        self.assertIn("no FINDER", normalized)
        self.assertIn("no JUDGE", normalized)

    def test_kernel_plan_cites_architect_refuter_section_by_exact_name(self):
        """Pins the kernel's one citing sentence in PLAN (where architect
        output is consumed), naming the conventions section by exact
        heading text."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Architect-plan refuter — 2026-07"',
            normalized,
        )
        self.assertIn("tier-escalation checklist", normalized)
        self.assertIn("run ONE refuter pass", normalized)

    def test_kernel_skill_within_char_ceiling(self):
        """Sanity pin: this task's addition must stay under the 31,617-char
        ceiling (same ceiling TestFgA10201VerifierFindingFilterPins and
        TestFgA10208IdleWaitPins already pin) — a duplicate assertion here
        keeps this task's own fit-under-budget claim independently checked."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertLess(len(content), 31617)

    def test_forge_architect_has_refuted_plan_output_contract_note(self):
        """Pins forge-architect's output-contract note: a plan may be
        refuted; the architect responds to the refuter exchange, never
        revises silently."""
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-architect.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            '`docs/conventions.md`, "Architect-plan refuter — 2026-07"',
            normalized,
        )
        self.assertIn(
            "respond to the refuter's challenge", normalized,
        )
        self.assertIn("never silently revise the plan", normalized)
