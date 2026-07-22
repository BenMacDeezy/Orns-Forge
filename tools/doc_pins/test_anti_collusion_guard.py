"""Doc-pin regression tests for bm-anti-collusion-verify-guard
(`docs/specs/2026-07-22-phase2-external-workers.md`, "Anti-collusion
invariant -- builder/verifier separation (corrects section 11's scope)").

Pins the load-bearing sentences of `provider-judges.md` section 11.4 so a
future edit can't quietly weaken the anti-collusion invariant: (1) the
unconditional external-build -> Claude-verifier rule, (2) the
provider-co-verifier-never-the-sole-slot rule, and (3) the correction
scoping section 11's automatic codex-co-verifier mechanic to Claude-built
work only. Companion to `test_cross_model_consensus_pins.py`'s
`TestSequentialCrossModelReviewPins`, which pins the unrelated 11.1-11.3
mechanics this task does not touch.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import REPO_ROOT, _cached_read_text  # noqa: E402


class TestAntiCollusionInvariantPins(unittest.TestCase):
    """provider-judges.md section 11.4 -- the unconditional invariant and
    the section-11 scope correction it makes."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )

    def _content(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def test_section_11_4_heading(self):
        content = self._content()
        self.assertIn(
            "### 11.4 Anti-collusion invariant — builder/verifier "
            "separation (never a self-graded build)",
            content,
        )

    def test_unconditional_external_build_claude_verifier_rule(self):
        content = self._content()
        self.assertIn(
            "WHEN a task's BUILD is dispatched to an external provider "
            "(via the R1\nautomatic-default or a `provider:` override), "
            "THE SYSTEM SHALL require the\nmandatory adversarial verifier "
            "for that task to be Claude\n(`forge-verifier`/`forge-ui-"
            "verifier`) — exactly as section 7.5 already\nstates.",
            content,
        )
        self.assertIn(
            "it holds\nUNCONDITIONALLY — regardless of how the active "
            "profile's `role-co-verifier`\nis set",
            content,
        )

    def test_never_sole_slot_same_or_cross_provider(self):
        content = self._content()
        self.assertIn(
            "A provider co-verifier SHALL NEVER occupy the sole "
            "adversarial\npanel slot for a task that same provider, or "
            "ANY provider, built.",
            content,
        )
        self.assertIn(
            "including when `role-co-verifier` resolves to the SAME "
            "provider\nthat built the task, or to a DIFFERENT external "
            "provider than the builder:\nneither case ever substitutes "
            "for the Claude verifier on that task.",
            content,
        )

    def test_invariant_is_not_a_profile_customizable_default(self):
        content = self._content()
        self.assertIn(
            "This is\nan INVARIANT, not a default subject to profile "
            "customization,",
            content,
        )

    def test_section_11_scoped_to_claude_built_work_only(self):
        content = self._content()
        self.assertIn(
            "Section 11.1's automatic codex-adversarial-slot rule applies "
            "EXCLUSIVELY\nWHEN the BUILDER is a Claude in-harness worker "
            "AND the task is `tier: full`\nor sensitive-domain",
            content,
        )
        self.assertIn(
            "that\ncondition is EXCLUSIVE, not merely a default: WHEN the "
            "BUILDER is an\nexternal provider instead, section 11 in its "
            "entirety (11.1's two-stage\ncodex-sweep/Claude-findings-"
            "review mechanic and 11.2's dualverify\nexception alike) is "
            "simply inapplicable, and section 7.5 governs alone —",
            content,
        )

    def test_no_findings_review_or_dualverify_substitution_for_external_build(
        self,
    ):
        content = self._content()
        self.assertIn(
            "Claude verifies, period, with no codex co-verifier "
            "substitution, no\nfindings-review split, and no dualverify "
            "carve-out standing in for it.",
            content,
        )

    def test_1113_unchanged_by_this_correction(self):
        content = self._content()
        self.assertIn(
            "This correction changes no other section-11 mechanic: for "
            "Claude-built\n`tier: full`/sensitive-domain work, 11.1-11.3 "
            "above are unchanged and\nunaffected by this section.",
            content,
        )

    def test_intro_scope_correction_paragraph(self):
        content = self._content()
        self.assertIn(
            "**Scope correction (bm-anti-collusion-verify-guard, "
            "2026-07-22).**",
            content,
        )
        self.assertIn(
            "WHEN the task's BUILD was\ndispatched to an external "
            "provider instead, this section does not apply\nat all: "
            "section 7.5 governs in full and alone",
            content,
        )

    def test_cites_spec_section_title_verbatim(self):
        content = self._content()
        self.assertIn(
            "\"Anti-\ncollusion invariant — builder/verifier separation "
            "(corrects section 11's\nscope)\"",
            content,
        )

    def test_existing_section_11_heading_and_sibling_subsections_untouched(
        self,
    ):
        """Guard against this task's edit accidentally clobbering the
        pre-existing section-11 heading or the sibling 11.1/11.2/11.3
        subsection headings that `test_cross_model_consensus_pins.py`
        already pins."""
        content = self._content()
        self.assertIn(
            "## 11. Sequential cross-model review + dualverify "
            "exception — 2026-07-22 (spec cross-model-consensus)",
            content,
        )
        self.assertIn("### 11.1 Automatic sequential cross-model review",
                       content)
        self.assertIn(
            "### 11.2 Dual-verifier ceiling amendment — command-only",
            content,
        )
        self.assertIn(
            "### 11.3 Disagreement reconciliation — through the existing "
            "filter, never free-form synthesis",
            content,
        )


if __name__ == "__main__":
    unittest.main()
