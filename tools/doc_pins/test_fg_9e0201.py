"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9e0201`: TestFg9e0201LowRiskVerifyPins.
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


class TestFg9e0201LowRiskVerifyPins(unittest.TestCase):
    """Doc-pins for fg-9e0201 (low-risk verification sub-tier): the canonical
    dated conventions section, kernel VERIFY mode-2 routing paragraph, and
    forge-verifier's ESCALATE contract addition.

    Covers all 4 EARS clauses: (1) qualification + reduced-protocol section
    exists and is cited by exact name from kernel SKILL.md; (2) ESCALATE is
    present as a third VERDICT value scoped to low-risk mode only, with
    mandatory-escalation-on-doubt language; (3) the sampling-audit rule is
    documented; (4) the disqualification list (skills/, agents/, hooks/,
    workflows/, .forge/ protocol files) and the UI-never-qualifies carve-out
    both survive verbatim enough to catch a future edit gutting them.
    """

    def test_conventions_has_low_risk_verify_section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "## Low-risk verification (standard sub-class) — 2026-07", content
        )

    def test_conventions_low_risk_section_has_disqualification_list(self):
        """Pins the explicit disqualification list — hooks/ and workflows/
        must both appear, not just skills/ and agents/ — so a future edit
        can't quietly narrow the disqualified set."""
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Low-risk verification (standard sub-class) — 2026-07"
        )[1]
        self.assertIn("hooks/", section)
        self.assertIn("workflows/", section)
        self.assertIn("skills/", section)
        self.assertIn("agents/", section)
        self.assertIn(".forge/", section)

    def test_conventions_low_risk_section_has_ui_never_qualifies(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "UI/animation tasks never qualify as low-risk verification", content
        )
        self.assertIn("output is behavioral by definition", content)

    def test_conventions_low_risk_section_has_normative_prose_disqualifier(self):
        """Pins the content-based disqualifier (fix for the leak found in
        verification: a docs/-only edit to normative protocol/trust/consent/
        verification-rule prose must NOT qualify just because it sits under
        docs/). Anchors the operative sentence plus the self-referential
        carve-out naming this section itself, so a future edit can't quietly
        drop either half."""
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Low-risk verification (standard sub-class) — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("NORMATIVE prose never qualifies, regardless of path", normalized)
        self.assertIn(
            "a task editing this Low-risk verification section always gets "
            "full verification",
            normalized,
        )
        self.assertIn(
            "Only non-normative documentation (README files, code comments, "
            "non-normative reference data) qualifies",
            normalized,
        )

    def test_conventions_low_risk_section_has_escalate_on_doubt(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("mandatory on doubt", content)
        self.assertIn("when uncertain, ESCALATE", content)
        self.assertIn("sampling audit", content)
        self.assertIn("low-risk\nverify: qualified", content)

    def test_conventions_low_risk_section_in_toc(self):
        """The set-compare TOC pin (tools/test_pins_conventions_toc.py)
        already catches a missing TOC entry generically; this pin nails
        down the exact bullet text for this specific section so the two
        test files agree on what "in the TOC" means for fg-9e0201."""
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "- Low-risk verification (standard sub-class) — 2026-07", content
        )

    def test_kernel_has_low_risk_routing_paragraph_with_exact_citation(self):
        # fg-b0402: the low-risk verify-routing paragraph moved verbatim
        # from skills/kernel/SKILL.md to
        # skills/kernel/references/verify-modes.md -- pin STRINGS
        # unchanged, only the file read.
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"))
        self.assertIn("Low-risk verify routing", content)
        self.assertIn(
            '"Low-risk verification (standard sub-class) — 2026-07"', content
        )
        self.assertIn("VERDICT: ESCALATE", content)
        self.assertIn("sampling audit", content)

    def test_kernel_low_risk_routing_mirrors_normative_prose_disqualifier(self):
        """Pins the one-sentence mirror of the content-based disqualifier in
        the kernel's routing paragraph — it must cite the conventions
        section's rule by name rather than diverge from it, and state
        plainly that the kernel checks diff CONTENT, not just paths.
        fg-b0402: paragraph moved verbatim to references/verify-modes.md;
        pin STRINGS unchanged, only the file read."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"))
        self.assertIn('"NORMATIVE prose never\n   qualifies"', content)
        self.assertIn(
            "the kernel checks the CONTENT of the diff, not\n   just its path",
            content,
        )

    def test_kernel_low_risk_routing_does_not_contradict_hard_rule_3(self):
        """Pins the explicit statement that this stays mode 2 — a separate
        verifier spawn — and does not contradict Hard Rule 3.
        fg-b0402: paragraph moved verbatim to references/verify-modes.md;
        pin STRING unchanged, only the file read."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"))
        self.assertIn("does not contradict Hard Rule 3", content)

    def test_verifier_has_low_risk_mode_section(self):
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-verifier.md"))
        self.assertIn("## Low-risk mode", content)
        self.assertIn("mandatory on doubt", content.replace("**", ""))

    def test_verifier_output_contract_has_scoped_escalate(self):
        """Verifies ESCALATE is added as a third VERDICT value AND scoped to
        low-risk mode only, plus the ESCALATE REASON line exists."""
        content = _cached_read_text((REPO_ROOT / "agents" / "forge-verifier.md"))
        self.assertIn(
            "VERDICT: PASS | FAIL | ESCALATE   (ESCALATE valid only in low-risk mode)",
            content,
        )
        self.assertIn("ESCALATE REASON:", content)
        self.assertIn(
            "and full mode\nnever returns ESCALATE.", content,
        )
