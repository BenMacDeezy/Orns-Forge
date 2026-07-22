"""Doc-pin regression tests for the cross-model-consensus spec
(`docs/specs/2026-07-22-cross-model-consensus.md`): the plan consensus
escalation (provider-judges.md section 10), the sequential cross-model
review + dualverify exception (provider-judges.md section 11), the split
BUILDER/JUDGE attribute-routing matrices (dispatch-and-routing.md), and
the consensus escalation dispatch labels (telemetry-and-labels.md). Pins
the load-bearing sentences of each so a future edit that quietly drops
the escalate-only entry, the fixed two-critique cap, the exact-coverage
rule, the retry-counting rule, the sequential-review automatic-slot rule,
the findings-review-doubles-as-delta-re-verify rule, the dual-only-in-
command exception, the five-step precedence chain (in order), or the
tier-keys-only citation rule fails loudly instead of silently.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
)


class TestPlanConsensusEscalationPins(unittest.TestCase):
    """provider-judges.md section 10 — escalate-only entry, fixed cap of
    two, exact-coverage, retry counting."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )

    def _content(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def test_section_10_heading(self):
        content = self._content()
        self.assertIn(
            "## 10. Plan consensus escalation — 2026-07-22 (spec "
            "cross-model-consensus)",
            content,
        )

    def test_escalate_only_entry_off_existing_refuter_pass(self):
        content = self._content()
        self.assertIn(
            "This is an ESCALATE-ONLY addition on top of the existing\n"
            "single Architect-plan-refuter pass "
            "(`docs/conventions/verification.md`,",
            content,
        )
        self.assertIn(
            "section fires ONLY when that pass returns at least one "
            "REJECT.",
            content,
        )

    def test_cap_exactly_two_critiques_c1_c2(self):
        content = self._content()
        self.assertIn(
            "a FIXED cap of exactly TWO advisor critiques\n"
            "total, never three.",
            content,
        )
        self.assertIn(
            "route the\nplan STRAIGHT to the per-id human resolution "
            "pass",
            content,
        )

    def test_c2_unreviewed_never_a_third_critique(self):
        content = self._content()
        self.assertIn(
            "UNREVIEWED (no third critique exists to accept or reject "
            "it) and route the",
            content,
        )

    def test_decision_id_schema_fields(self):
        content = self._content()
        self.assertIn("`proposal_id`: identifies which proposal", content)
        self.assertIn(
            "`decision_ids`: an exhaustive, ordered manifest of the "
            "plan's discrete",
            content,
        )
        self.assertIn(
            "a required `reason`, and — for every `REJECT` — a\n"
            "  required `alternative`.",
            content,
        )

    def test_exact_coverage_check_malformed(self):
        content = self._content()
        self.assertIn(
            "- An exact-coverage check applies: a verdict missing an "
            "id, or carrying an\n  id not in the current manifest, is "
            "MALFORMED output, not a valid\n  critique.",
            content,
        )

    def test_p3_fixed_inline_economy_rule(self):
        content = self._content()
        self.assertIn(
            "**Economy rule — cosmetic REJECTs never gate another "
            "round.**",
            content,
        )
        self.assertIn(
            "a `P3` REJECT NEVER by itself\ntriggers `C2`", content
        )

    def test_retry_then_force_extends_section_7_4(self):
        content = self._content()
        self.assertIn(
            "this\nsection explicitly EXTENDS section 7.4's Phase-2-"
            "worker retry-then-force\nprotocol to this judge role",
            content,
        )

    def test_every_retry_counted_as_invocation(self):
        content = self._content()
        self.assertIn(
            "Each retry is itself another provider CLI invocation and "
            "counts against the\ndispatch tally exactly as section 7.6 "
            "already defines",
            content,
        )

    def test_exchange_artifact_two_artifacts_never_one(self):
        content = self._content()
        self.assertIn(
            "WHEN the exchange record is written, THE SYSTEM SHALL "
            "maintain TWO\nartifacts, never one:",
            content,
        )
        self.assertIn("## Plan consensus record", content)
        self.assertIn(
            "docs/specs/consensus/<spec-basename>-exchange.md`, holding "
            "the full raw",
            content,
        )

    def test_provider_text_always_fenced(self):
        content = self._content()
        self.assertIn(
            "never rendered as live markdown headings or bullets, so\n"
            "   provider text can NEVER inject a heading, a "
            "clarification-marker\n   marker, or any other structurally-"
            "significant token into a normative\n   file.",
            content,
        )

    def test_mid_cap_outstanding_reject_terminates_unresolved(self):
        content = self._content()
        self.assertIn(
            "THE SYSTEM SHALL terminate the escalation as\nUNRESOLVED "
            "(not as a completed cap-out, not as a Claude-only degrade)",
            content,
        )

    def test_economy_no_added_cost_to_clean_plan(self):
        content = self._content()
        self.assertIn("### 10.7 Economy — no cost added to a clean plan",
                       content)


class TestSequentialCrossModelReviewPins(unittest.TestCase):
    """provider-judges.md section 11 — automatic sequential slot rule,
    findings-review-doubles-as-delta, dual-only-in-command."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )

    def _content(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def test_section_11_heading(self):
        content = self._content()
        self.assertIn(
            "## 11. Sequential cross-model review + dualverify "
            "exception — 2026-07-22 (spec cross-model-consensus)",
            content,
        )

    def test_codex_takes_single_slot_automatically(self):
        content = self._content()
        self.assertIn(
            "route the adversarial-verifier slot to codex AUTOMATICALLY\n"
            "(gates permitting)",
            content,
        )
        self.assertIn(
            "still the EXISTING one-adversarial-verifier\npanel-slot "
            "ceiling",
            content,
        )

    def test_findings_review_doubles_as_delta_reverify(self):
        content = self._content()
        self.assertIn(
            "**Findings-review doubles as the delta re-verify.**",
            content,
        )
        self.assertIn(
            "the findings-review\ndoubles as the delta re-verify",
            content,
        )

    def test_dual_verifier_only_inside_dualverify_command(self):
        content = self._content()
        self.assertIn(
            "it exists ONLY behind an\nexplicit command "
            "(`/forge:dualverify`)",
            content,
        )

    def test_reconciliation_through_existing_filter_not_synthesis(self):
        content = self._content()
        self.assertIn(
            "THE SYSTEM SHALL reconcile\nfinding-by-finding through the "
            "EXISTING verifier-finding filter/",
            content,
        )
        self.assertIn("NOT via\nfree-form \"kernel synthesis.\"", content)


class TestAttributeRoutingMatricesPins(unittest.TestCase):
    """dispatch-and-routing.md — split BUILDER/JUDGE matrices, tier-keys-
    only citation, five-step precedence chain in order."""

    ROUTING_PATH = (
        REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md"
    )
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    def _content(self):
        return _cached_read_text(self.ROUTING_PATH)

    def test_section_heading(self):
        content = self._content()
        self.assertIn(
            "## Attribute routing matrices — 2026-07-22 (spec "
            "cross-model-consensus)",
            content,
        )

    def test_two_separate_matrices_never_one_shared_table(self):
        content = self._content()
        self.assertIn(
            "THE SYSTEM SHALL maintain TWO separate default-\nrouting "
            "matrices, never one shared table",
            content,
        )
        self.assertIn("**BUILDER matrix**", content)
        self.assertIn("**JUDGE matrix**", content)

    def test_tier_keys_only_never_slugs(self):
        content = self._content()
        self.assertIn(
            "Reference ONLY tier keys (`codex-tier-mechanical`, "
            "`codex-tier-balanced`,\n`codex-tier-judgment`) in both "
            "matrices",
            content,
        )
        self.assertIn("NEVER a model slug or nickname", content)

    def test_precedence_chain_five_steps_in_order(self):
        content = self._content()
        i0 = content.find("**Precedence chain**, applied in this exact "
                           "order for BOTH matrices:")
        self.assertGreater(i0, -1)
        i1 = content.find(
            "1. Human-written routing override (explicit routing note "
            "on the task)\n   always wins", i0)
        i2 = content.find(
            "2. Sensitive-domain BUILDER carve-out (above)", i1)
        i3 = content.find(
            "3. The four-layer provider gate (`provider-judges.md` "
            "section 1a) plus", i2)
        i4 = content.find(
            "4. The active profile's resolved `role-*` assignment", i3)
        i5 = content.find(
            "5. Task-shape tie-break WITHIN the profile's allowed pool",
            i4)
        for i in (i1, i2, i3, i4, i5):
            self.assertGreater(i, -1)
        self.assertTrue(i0 < i1 < i2 < i3 < i4 < i5)

    def test_checkpoint_pressure_removed_as_tie_break(self):
        content = self._content()
        self.assertIn(
            "\"Checkpoint budget pressure\" is REMOVED as a tie-break "
            "input",
            content,
        )

    def test_table_breaks_ties_never_overrides_a_floor(self):
        content = self._content()
        self.assertIn(
            "The table breaks ties only,\nnever overrides a floor",
            content,
        )

    def test_conventions_toc_entry(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Attribute routing matrices — 2026-07-22 (spec "
            "cross-model-consensus)",
            content,
        )

    def test_conventions_shards_manifest_row(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            "`Attribute routing matrices — 2026-07-22 (spec "
            "cross-model-consensus)` -> `docs/conventions/"
            "dispatch-and-routing.md`",
            content,
        )


class TestConsensusEscalationLabelsPins(unittest.TestCase):
    """telemetry-and-labels.md — consensus dispatch label format, distinct
    section name from the sibling's rollout-telemetry section, every
    invocation (incl. retries) gets its own tally line."""

    TELEMETRY_LABELS_PATH = (
        REPO_ROOT / "docs" / "conventions" / "telemetry-and-labels.md"
    )
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    def _content(self):
        return _cached_read_text(self.TELEMETRY_LABELS_PATH)

    def test_section_heading(self):
        content = self._content()
        self.assertIn(
            "## Consensus escalation labels — 2026-07-22", content
        )

    def test_not_named_rollout_telemetry(self):
        """This task's section and the sibling task's "Consensus rollout
        telemetry" section are DISTINCT sections coexisting in this file
        post-merge — one heading each, never merged into one."""
        content = self._content()
        self.assertEqual(
            content.count("## Consensus escalation labels — 2026-07-22"), 1)
        self.assertEqual(
            content.count("## Consensus rollout telemetry — 2026-07-22"), 1)

    def test_label_format_round_marker(self):
        content = self._content()
        self.assertIn(
            "`<Persona> — plan-refuter — <provider>/\n<model-slug> — "
            "<plan name> — round <Cn>`",
            content,
        )
        self.assertIn(
            "e.g. `Blue — plan-refuter —\ncodex/gpt-5.6-sol — "
            "cross-model-consensus — round C2`.",
            content,
        )

    def test_round_marker_is_c1_or_c2_never_r1_p1(self):
        content = self._content()
        self.assertIn(
            "`round <Cn>` is `C1` or `C2` exactly", content
        )

    def test_every_invocation_including_retries_own_tally_line(self):
        content = self._content()
        self.assertIn(
            "THE\nSYSTEM SHALL emit one tally line per invocation, "
            "never one line per\ncritique",
            content,
        )

    def test_clean_plan_costs_exactly_one_dispatch(self):
        content = self._content()
        self.assertIn(
            "matching the\n\"a clean plan costs exactly one advisor "
            "dispatch, ever\" floor",
            content,
        )

    def test_conventions_toc_entry(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn("- Consensus escalation labels — 2026-07-22",
                       content)

    def test_conventions_shards_manifest_row(self):
        content = _read_path(self.CONVENTIONS_PATH)
        self.assertIn(
            "`Consensus escalation labels — 2026-07-22` -> "
            "`docs/conventions/telemetry-and-labels.md`",
            content,
        )


if __name__ == "__main__":
    unittest.main()


class TestSweepGapPins(unittest.TestCase):
    """Round-2 pins for the four load-bearing rules Terra's sequential
    sweep (2026-07-22) found unpinned. Fixed-inline per the marginal-gain
    stop rules; the prescriptions are the sweep's own."""

    def _judges(self):
        return _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "provider-judges.md")

    def _routing(self):
        return _cached_read_text(
            REPO_ROOT / "docs" / "conventions" / "dispatch-and-routing.md")

    def test_checklist_trigger_not_nominal_tier(self):
        content = self._judges()
        self.assertIn("gated by the SAME checklist trigger", content)
        self.assertIn("never\nnominal `tier: full` status alone", content)

    def test_artifact_append_only_and_crash_resume(self):
        content = self._judges()
        self.assertIn("is append-only: a\n   resumed or re-run escalation "
                      "appends a new dated section, it never edits\n   or "
                      "removes a prior critique's record", content)
        self.assertIn("**Crash/resume.**", content)
        self.assertIn("the kernel reads the ledger's last CLOSED critique",
                      content)

    def test_reconciliation_union_one_pass_block(self):
        content = self._judges()
        self.assertIn("union all non-conflicting\nsurviving findings from "
                      "both verifiers", content)
        self.assertIn("exactly ONE clarification pass", content)
        self.assertIn("unresolved\nAND outcome-affecting after that pass",
                      content)

    def test_no_model_slug_in_routing_matrices_executable(self):
        section = self._routing().split(
            "## Attribute routing matrices — 2026-07-22", 1)[1]
        section = section.split("\n## ", 1)[0]
        # executable guard, not prose: a literal slug in either matrix
        # would silently pin routing to a superseded model identity
        import re
        self.assertIsNone(re.search(r"gpt-\d", section))
        self.assertNotIn("codex/gpt", section)


if __name__ == "__main__":
    unittest.main()
