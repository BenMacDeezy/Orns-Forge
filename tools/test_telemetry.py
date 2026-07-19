"""Tests for tools/telemetry.py (fg-a10101): aggregate Routing record + Attempt
log data across .forge/queue/tasks/*.md into per-agent/per-tier/verify-mode
telemetry. Fixtures are inline task-file strings (real Attempt-log/Routing-
record vocabulary observed in this repo's own queue, e.g. fg-9e0101,
fg-9e0103, fg-9f0103, fg-9e0201, fg-9b0201-204, fg-9d0101), each written to
its own tmp dir per test.
"""
import json
import os
import pathlib
import tempfile
import unittest

from telemetry import (
    RECOMMEND_MIN_DISPATCHES,
    RECOMMEND_MIN_FAIL_RATE,
    aggregate,
    compute_recommendations,
    main,
    parse_attempt_log,
    parse_routing_record,
    render_recommendations,
    render_table,
    _EFFORT_LADDER,
    _MODEL_LADDER,
    _find_slug,
    _next_tier_up,
)


def _task(id_, tier="standard", routing="(pending)", attempt_log="(pending)",
          state="done"):
    return f"""---
id: {id_}
title: "Fixture task {id_}"
state: {state}
tier: {tier}
priority: 1
spec: null
blocks: []
blocked-by: []
claimed-by: null
parallel-safe: true
created: 2026-07-18T00:00:00Z
updated: 2026-07-18T00:00:00Z
schema-version: 1
---

## Acceptance criteria
WHEN a fixture runs, THE SYSTEM SHALL do the fixture thing.

## Execution plan
(pending)

## Routing record
{routing}

## Attempt log
{attempt_log}

## Outcome
(pending)
"""


def _write(task_dir, id_, **kw):
    (pathlib.Path(task_dir) / f"{id_}-fixture.md").write_text(
        _task(id_, **kw), encoding="utf-8")


class TelemetryTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.task_dir = self._tmp

    def tearDown(self):
        pass  # tempfile dirs are left for the OS to reap; no repo state touched


class TestCleanSingleAttemptPass(TelemetryTestCase):
    def test_clean_pass_counts_dispatch_and_first_attempt_pass(self):
        _write(
            self.task_dir, "fg-t001",
            routing="attempt 1: forge-worker — sonnet/high — well-specified building",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T10:00:00Z (test fixture)\n\n"
                "attempt 1 verify: sonnet/high verifier -> PASS first attempt. "
                "All criteria held."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["tasks_scanned"], 1)
        self.assertEqual(report["agent_dispatch_counts"].get("forge-worker"), 1)
        self.assertEqual(report["first_attempt"], {"pass": 1, "total": 1})
        self.assertEqual(report["bounces"]["total"], 0)
        self.assertEqual(report["verify_mode_counts"].get("verifier"), 1)
        self.assertEqual(report["attempt_lines_unparsed"], 0)
        self.assertGreaterEqual(report["attempt_lines_parsed"], 2)


class TestFailBounceMechanicalHaikuReVerifyPass(TelemetryTestCase):
    def test_mechanical_bounce_then_reverify_pass(self):
        _write(
            self.task_dir, "fg-t002",
            routing="attempt 1: forge-worker — sonnet/high — orchestration semantics",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T05:10:00Z (batch 2)\n\n"
                "attempt 1 verify: sonnet/high verifier -> FAIL (MECHANICAL): "
                "sliding window unreachable — dead eligibility precondition.\n\n"
                "attempt 2 (bounce, haiku/low per the NEW mechanical-bounce rule "
                "— its first live exercise): both sentences reworded per verbatim "
                "FAIL NOTES.\n\n"
                "attempt 2 re-verify: sonnet/high focused -> PASS. Kernel re-check clean."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["first_attempt"], {"pass": 0, "total": 1})
        self.assertEqual(report["bounces"]["total"], 1)
        self.assertEqual(report["bounces"]["MECHANICAL"], 1)
        self.assertEqual(report["bounces"].get("JUDGMENT", 0), 0)
        self.assertEqual(report["attempt_lines_unparsed"], 0)


class TestFailBounceJudgmentOriginalTier(TelemetryTestCase):
    def test_judgment_bounce_keeps_original_tier(self):
        _write(
            self.task_dir, "fg-t003",
            routing="attempt 1: forge-worker — sonnet/high — verification-protocol change",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T06:15:00Z (single-task wave)\n\n"
                "attempt 1 verify: opus/high -> FAIL (JUDGMENT): qualification leak "
                "in the docs/ whitelist.\n\n"
                "attempt 2 (bounce, sonnet/high — JUDGMENT keeps original tier per "
                "the mechanical-bounce rule): content-based disqualifier added.\n\n"
                "attempt 2 re-verify: opus/high focused -> PASS. All attack vectors disqualify."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["bounces"]["total"], 1)
        self.assertEqual(report["bounces"]["JUDGMENT"], 1)
        self.assertEqual(report["bounces"].get("MECHANICAL", 0), 0)
        # the bounce redispatch line names the tier that keeps working
        bounce_stats = parse_attempt_log(
            "attempt 2 (bounce, sonnet/high — JUDGMENT keeps original tier per "
            "the mechanical-bounce rule): fixed."
        )
        self.assertEqual(bounce_stats["bounces"][0]["tier"], "sonnet/high")
        self.assertEqual(bounce_stats["bounces"][0]["tag"], "JUDGMENT")


class TestPassAfterFilterCountsAsFail(TelemetryTestCase):
    """Telemetry-honesty regression (2026-07-18 pin audit): a verify recorded
    as PASS-after-filter must count as FAIL.  Without the explicit pre-check,
    VERDICT_RE's \\b matches the S/- boundary in "PASS-after-filter" and the
    line silently misparses as PASS."""

    def test_pass_after_filter_line_parses_as_fail(self):
        stats = parse_attempt_log(
            "attempt 1 verify: sonnet/high -> PASS-after-filter: all findings "
            "FILTERED (kernel spot-check disproved each)."
        )
        self.assertEqual(len(stats["verify_verdicts"]), 1)
        self.assertEqual(stats["verify_verdicts"][0]["verdict"], "FAIL")
        self.assertEqual(stats["verify_verdicts"][0]["tier"], "sonnet/high")

    def test_plain_pass_still_parses_as_pass(self):
        stats = parse_attempt_log(
            "attempt 1 verify: sonnet/high -> PASS. All criteria green."
        )
        self.assertEqual(stats["verify_verdicts"][0]["verdict"], "PASS")

    def test_pass_after_filter_counts_against_first_attempt(self):
        _write(
            self.task_dir, "fg-t099",
            routing="attempt 1: forge-worker — sonnet/high — doc change",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T07:00:00Z (single)\n\n"
                "attempt 1 verify: sonnet/high -> PASS-after-filter: sole "
                "finding FILTERED (kernel disproved the repro)."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["first_attempt"], {"pass": 0, "total": 1})


class TestModeThreeFinderClosure(TelemetryTestCase):
    def test_finder_kernel_synthesis_routes_as_kernel_synthesis_mode(self):
        _write(
            self.task_dir, "fg-t004",
            routing="attempt 1: finder — verification: kernel synthesis (mode 3) — "
                    "sonnet/high — fresh-eyes precedent",
            attempt_log="attempt 1: dispatched 2026-07-18T00:01:17Z (gap-sweep wave 2; "
                        "disjoint scopes)",
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["agent_dispatch_counts"].get("finder"), 1)
        self.assertEqual(report["verify_mode_counts"].get("kernel-synthesis"), 1)
        # a finder closure has no separate verifier spawn, so it never
        # contributes to the first-attempt PASS/FAIL denominator
        self.assertEqual(report["first_attempt"], {"pass": 0, "total": 0})


class TestLowRiskAndSamplingAudit(TelemetryTestCase):
    def test_low_risk_qualified_line_routes_as_low_risk_mode(self):
        _write(
            self.task_dir, "fg-t005",
            routing="attempt 1: forge-worker — sonnet/high — well-specified docs-only change",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (docs fix)\n\n"
                "attempt 1 verify: low-risk verify: qualified — docs-only, "
                "pin-covered; haiku/low -> PASS. Gates green, pins present-and-passing."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["verify_mode_counts"].get("low-risk"), 1)
        self.assertEqual(report["first_attempt"], {"pass": 1, "total": 1})

    def test_sampling_audit_line_routes_as_sampling_mode(self):
        _write(
            self.task_dir, "fg-t006",
            routing="attempt 1: forge-worker — sonnet/high — well-specified docs-only change",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (docs fix)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. sampling audit — 5th "
                "qualifying task routed to full verification anyway."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["verify_mode_counts"].get("sampling"), 1)


class TestEscalateLine(TelemetryTestCase):
    def test_escalate_verdict_counted_and_excluded_from_first_attempt(self):
        _write(
            self.task_dir, "fg-t007",
            routing="attempt 1: forge-worker — sonnet/high — well-specified docs-only change",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (docs fix)\n\n"
                "attempt 1 verify: haiku/low -> VERDICT: ESCALATE. Found unpinned "
                "behavioral change, escalating to full verification."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["escalate_count"], 1)
        # ESCALATE is not PASS or FAIL, so it never counts as a bounce and
        # never enters the first-attempt PASS-rate denominator
        self.assertEqual(report["first_attempt"], {"pass": 0, "total": 0})
        self.assertEqual(report["bounces"]["total"], 0)


class TestJudgeYieldLines(TelemetryTestCase):
    # fg-a10901 (docs/conventions.md "Verification economics — 2026-07-18"):
    # judge-yield lines pin the raised -> survived -> changed funnel per judge.

    def test_judge_yield_line_parses(self):
        stats = parse_attempt_log(
            "judge-yield: forge-reviewer raised=3 survived=1 changed=0"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(
            stats["judge_yields"],
            [{"slug": "forge-reviewer", "raised": 3, "survived": 1, "changed": 0}],
        )

    def test_judge_yield_aggregates_across_tasks(self):
        _write(
            self.task_dir, "fg-t101",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. Green.\n\n"
                "judge-yield: forge-verifier raised=2 survived=2 changed=1\n\n"
                "judge-yield: forge-security raised=1 survived=0 changed=0"
            ),
        )
        _write(
            self.task_dir, "fg-t102",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. Green.\n\n"
                "judge-yield: forge-verifier raised=4 survived=1 changed=1"
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(
            report["judge_yield"]["forge-verifier"],
            {"raised": 6, "survived": 3, "changed": 2, "verdicts": 2},
        )
        self.assertEqual(
            report["judge_yield"]["forge-security"],
            {"raised": 1, "survived": 0, "changed": 0, "verdicts": 1},
        )
        table = render_table(report)
        self.assertIn("Judge yield", table)
        self.assertIn("forge-verifier", table)
        self.assertIn("6 -> 3 -> 2", table)

    def test_malformed_judge_yield_counts_unparsed_never_silent_zero(self):
        stats = parse_attempt_log(
            "judge-yield: forge-reviewer raised=3 survived=one changed=0"
        )
        self.assertEqual(stats["judge_yields"], [])
        self.assertEqual(stats["unparsed"], 1)


class TestJudgeYieldSeveritySuffix(TelemetryTestCase):
    # fg-a10911 (docs/conventions.md "Finding severity + confidence —
    # 2026-07-18 (fg-a10911)"): the judge-yield line grows an OPTIONAL
    # trailing `p0=A p1=B p2=C p3=D` suffix, backward-compatible with the
    # fg-a10901 no-suffix shape.

    def test_no_suffix_line_still_parses_exactly_as_before(self):
        # Backward compatibility: the base shape (no suffix at all) is
        # unaffected by the extension -- same dict shape as pre-fg-a10911.
        stats = parse_attempt_log(
            "judge-yield: forge-reviewer raised=3 survived=1 changed=0"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(
            stats["judge_yields"],
            [{"slug": "forge-reviewer", "raised": 3, "survived": 1, "changed": 0}],
        )

    def test_suffix_line_parses_severity_counts(self):
        stats = parse_attempt_log(
            "judge-yield: forge-verifier raised=4 survived=2 changed=1 "
            "p0=1 p1=1 p2=1 p3=1"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(
            stats["judge_yields"],
            [
                {
                    "slug": "forge-verifier",
                    "raised": 4,
                    "survived": 2,
                    "changed": 1,
                    "severity": {"p0": 1, "p1": 1, "p2": 1, "p3": 1},
                }
            ],
        )

    def test_malformed_suffix_counts_unparsed_not_silent_partial(self):
        # A suffix present but missing a p-level must fail the WHOLE line --
        # never a silent partial parse of just raised/survived/changed.
        stats = parse_attempt_log(
            "judge-yield: forge-reviewer raised=3 survived=1 changed=0 "
            "p0=1 p1=2 p2=3"
        )
        self.assertEqual(stats["judge_yields"], [])
        self.assertEqual(stats["unparsed"], 1)

    def test_malformed_suffix_non_numeric_counts_unparsed(self):
        stats = parse_attempt_log(
            "judge-yield: forge-reviewer raised=3 survived=1 changed=0 "
            "p0=one p1=2 p2=3 p3=0"
        )
        self.assertEqual(stats["judge_yields"], [])
        self.assertEqual(stats["unparsed"], 1)

    def test_aggregate_sums_severity_across_tasks(self):
        _write(
            self.task_dir, "fg-t201",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. Green.\n\n"
                "judge-yield: forge-verifier raised=4 survived=2 changed=1 "
                "p0=1 p1=1 p2=1 p3=1"
            ),
        )
        _write(
            self.task_dir, "fg-t202",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. Green.\n\n"
                "judge-yield: forge-verifier raised=2 survived=1 changed=0 "
                "p0=0 p1=1 p2=1 p3=0"
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(
            report["judge_yield"]["forge-verifier"],
            {
                "raised": 6,
                "survived": 3,
                "changed": 1,
                "verdicts": 2,
                "severity": {"p0": 1, "p1": 2, "p2": 2, "p3": 1},
            },
        )
        table = render_table(report)
        self.assertIn("6 -> 3 -> 1", table)
        self.assertIn("P0=1 P1=2 P2=2 P3=1", table)

    def test_no_suffix_bucket_has_no_severity_key_backward_compat(self):
        # A slug whose judge-yield lines never carried the suffix must keep
        # the exact pre-fg-a10911 bucket shape -- no "severity" key at all,
        # matching the existing test_judge_yield_aggregates_across_tasks pin.
        _write(
            self.task_dir, "fg-t203",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 1 verify: sonnet/high -> PASS. Green.\n\n"
                "judge-yield: forge-security raised=1 survived=1 changed=0"
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(
            report["judge_yield"]["forge-security"],
            {"raised": 1, "survived": 1, "changed": 0, "verdicts": 1},
        )


class TestMalformedAttemptLogLine(TelemetryTestCase):
    def test_malformed_line_lands_in_unparsed_tally_not_a_crash(self):
        _write(
            self.task_dir, "fg-t008",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok)\n\n"
                "attempt 2: something truncated with no recognizable shape at all\n\n"
                "attempt 3 verify sonnet high FAIL missing the colon after verify"
            ),
        )
        # must not raise
        report = aggregate(self.task_dir)
        self.assertEqual(report["attempt_lines_parsed"], 1)
        self.assertEqual(report["attempt_lines_unparsed"], 2)
        # rendering must also not raise on a report containing unparsed lines
        table = render_table(report)
        self.assertIn("1 attempt-lines parsed, 2 unparsed", table)

    def test_parse_attempt_log_directly_never_raises_on_garbage(self):
        garbage = "attempt : dispatched\nattempt abc verify: nonsense\n)))(((\n"
        stats = parse_attempt_log(garbage)  # must not raise
        self.assertGreaterEqual(stats["unparsed"], 1)


class TestEmptyQueueDir(TelemetryTestCase):
    def test_empty_dir_produces_clean_empty_report(self):
        empty_dir = tempfile.mkdtemp()
        report = aggregate(empty_dir)
        self.assertEqual(report["tasks_scanned"], 0)
        self.assertEqual(report["attempt_lines_parsed"], 0)
        self.assertEqual(report["attempt_lines_unparsed"], 0)
        self.assertEqual(report["agent_dispatch_counts"], {})
        self.assertEqual(report["first_attempt"], {"pass": 0, "total": 0})
        self.assertEqual(report["bounces"]["total"], 0)
        self.assertEqual(report["escalate_count"], 0)
        # must render without raising, and still print the coverage line
        table = render_table(report)
        self.assertIn("0 attempt-lines parsed, 0 unparsed", table)

    def test_nonexistent_dir_does_not_crash(self):
        report = aggregate(pathlib.Path(tempfile.mkdtemp()) / "does-not-exist")
        self.assertEqual(report["tasks_scanned"], 0)


class TestRoutingRecordAgentExtraction(TelemetryTestCase):
    def test_distinguishes_forge_ui_from_forge_ui_verifier_and_forge_worker(self):
        _write(self.task_dir, "fg-t009",
               routing="attempt 1: forge-worker — sonnet/high — implements the task",
               attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)")
        _write(self.task_dir, "fg-t010",
               routing="attempt 1: forge-ui — sonnet/high — frontend/UI work",
               attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)")
        _write(self.task_dir, "fg-t011",
               routing="attempt 1: forge-ui-verifier — sonnet/high — visual gate routing",
               attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)")

        report = aggregate(self.task_dir)
        counts = report["agent_dispatch_counts"]
        self.assertEqual(counts.get("forge-worker"), 1)
        self.assertEqual(counts.get("forge-ui"), 1)
        self.assertEqual(counts.get("forge-ui-verifier"), 1)
        # forge-ui-verifier's dispatch must never also be double-counted as
        # a forge-ui dispatch (substring collision check)
        self.assertEqual(counts.get("forge-ui"), 1)

    def test_parse_routing_record_directly_extracts_slug_and_tier(self):
        parsed = parse_routing_record(
            "attempt 1: forge-verifier — opus/high — equal-or-higher tier"
        )
        self.assertEqual(parsed["entries"], [{"slug": "forge-verifier", "tier": "opus/high"}])

    def test_gate_inline_and_delegation_gate_lines_do_not_crash(self):
        parsed = parse_routing_record(
            "GATE: execute inline. None of the three delegate criteria hold."
        )
        self.assertTrue(parsed["gates_inline"])
        parsed2 = parse_routing_record(
            "Delegation GATE: full-tier precondition satisfied — spec"
        )
        # no known slug/tier in this legacy line shape -- must not crash,
        # and must not fabricate a slug
        self.assertEqual(parsed2["entries"][0]["slug"], None)


class TestTierAndCoverageAlwaysReported(TelemetryTestCase):
    def test_tier_counts_and_coverage_line_present_for_mixed_batch(self):
        _write(self.task_dir, "fg-t012", tier="trivial",
               routing="GATE: execute inline. Single-file doc edit.",
               attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (trivial fix)")
        _write(self.task_dir, "fg-t013", tier="standard",
               routing="attempt 1: forge-worker — sonnet/high — well-specified",
               attempt_log=(
                   "attempt 1: dispatched 2026-07-18T00:00:00Z (wave)\n\n"
                   "attempt 1 verify: sonnet/high -> PASS first attempt."
               ))
        report = aggregate(self.task_dir)
        self.assertEqual(report["tier_counts"].get("trivial"), 1)
        self.assertEqual(report["tier_counts"].get("standard"), 1)
        self.assertEqual(report["verify_mode_counts"].get("gates-inline"), 1)
        table = render_table(report)
        self.assertIn("attempt-lines parsed", table)
        self.assertIn("unparsed", table)


class TestCLI(TelemetryTestCase):
    def test_main_json_flag_prints_valid_json_with_dir_override(self):
        _write(self.task_dir, "fg-t014",
               routing="attempt 1: forge-worker — sonnet/high — well-specified",
               attempt_log=(
                   "attempt 1: dispatched 2026-07-18T00:00:00Z (wave)\n\n"
                   "attempt 1 verify: sonnet/high -> PASS first attempt."
               ))
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--json", "--dir", self.task_dir])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["tasks_scanned"], 1)

    def test_main_table_mode_exits_zero_and_prints_coverage(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--dir", self.task_dir])
        self.assertEqual(rc, 0)
        self.assertIn("attempt-lines parsed", buf.getvalue())

    def test_main_never_transitions_a_task_file(self):
        _write(self.task_dir, "fg-t015",
               routing="attempt 1: forge-worker — sonnet/high — well-specified",
               attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)")
        path = pathlib.Path(self.task_dir) / "fg-t015-fixture.md"
        before = path.read_text(encoding="utf-8")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            main(["--dir", self.task_dir])
            main(["--json", "--dir", self.task_dir])
        after = path.read_text(encoding="utf-8")
        self.assertEqual(before, after)


def _fail_bounce_task(task_dir, id_, slug_line, tier):
    """A task whose attempt-1 verify FAILed and got bounced (re-verify PASS) --
    counts toward the FAIL-or-bounce numerator for its (slug, tier) pairing."""
    _write(
        task_dir, id_,
        routing=f"attempt 1: {slug_line} — {tier} — well-specified building",
        attempt_log=(
            "attempt 1: dispatched 2026-07-18T00:00:00Z (fixture)\n\n"
            f"attempt 1 verify: {tier} verifier -> FAIL (MECHANICAL): "
            "fixture failure reason.\n\n"
            f"attempt 2 (bounce, {tier}): fixed per FAIL NOTES.\n\n"
            f"attempt 2 re-verify: {tier} focused -> PASS."
        ),
    )


def _clean_pass_task(task_dir, id_, slug_line, tier):
    """A task whose attempt-1 verify PASSed clean -- does not count toward
    the FAIL-or-bounce numerator."""
    _write(
        task_dir, id_,
        routing=f"attempt 1: {slug_line} — {tier} — well-specified building",
        attempt_log=(
            "attempt 1: dispatched 2026-07-18T00:00:00Z (fixture)\n\n"
            f"attempt 1 verify: {tier} verifier -> PASS first attempt."
        ),
    )


class TestRecommendQualifyingPairing(TelemetryTestCase):
    """fg-a10102: 5 dispatches at forge-worker sonnet/medium, 3 bounced (60%)
    -- qualifies (>=5 dispatches, >=40% first-attempt FAIL-or-bounce rate),
    and the model ladder recommends the next tier up (opus, same effort)."""

    def test_five_dispatches_three_bounced_qualifies_and_recommends_next_tier(self):
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-q00{i}", "forge-worker", "sonnet/medium")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-q10{i}", "forge-worker", "sonnet/medium")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["slug"], "forge-worker")
        self.assertEqual(rec["tier"], "sonnet/medium")
        self.assertEqual(rec["dispatches"], 5)
        self.assertEqual(rec["fail_or_bounce"], 3)
        self.assertAlmostEqual(rec["rate"], 0.6)
        self.assertEqual(rec["next_tier"], "opus/medium")

        table = render_recommendations(recs)
        self.assertIn("forge-worker", table)
        self.assertIn("sonnet/medium", table)
        self.assertIn("3/5", table)
        self.assertIn("opus/medium", table)


class TestRecommendUnderThreshold(TelemetryTestCase):
    """4 dispatches (all bounced, 100% rate) -- never reaches the >=5
    dispatch floor, so it must NOT qualify regardless of how bad the rate is."""

    def test_four_dispatches_all_bounced_does_not_qualify(self):
        for i in range(4):
            _fail_bounce_task(self.task_dir, f"fg-u00{i}", "forge-ui", "sonnet/high")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(recs, [])
        table = render_recommendations(recs)
        self.assertIn("no recommendations", table)
        self.assertIn(str(RECOMMEND_MIN_DISPATCHES), table)
        self.assertIn("40", table)


class TestRecommendGoodRate(TelemetryTestCase):
    """5 dispatches, only 1 bounced (20%) -- below the 40% floor, must not
    qualify even though the dispatch count alone would clear the threshold."""

    def test_five_dispatches_one_bounced_does_not_qualify(self):
        _fail_bounce_task(self.task_dir, "fg-g000", "forge-worker", "sonnet/high")
        for i in range(4):
            _clean_pass_task(self.task_dir, f"fg-g10{i}", "forge-worker", "sonnet/high")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(recs, [])


class TestRecommendOpusCeiling(TelemetryTestCase):
    """5 dispatches at opus/high (the routed ceiling), 3 bounced (60%) --
    qualifies on the numbers, but the next-tier-up ladder has nowhere left
    to go (fable is never recommended, per the conventions fable rule), so
    the recommendation reports the ceiling instead of a bogus next tier."""

    def test_opus_high_qualifying_pairing_reports_ceiling_not_fable(self):
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-c00{i}", "forge-debugger", "opus/high")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-c10{i}", "forge-debugger", "opus/high")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["slug"], "forge-debugger")
        self.assertEqual(rec["tier"], "opus/high")
        self.assertIsNone(rec["next_tier"])
        self.assertNotIn("fable", str(rec).lower())

        table = render_recommendations(recs)
        self.assertNotIn("fable", table.lower())
        self.assertIn("already at ceiling", table)
        self.assertIn("investigate task-class instead", table)

    def test_opus_medium_qualifying_pairing_recommends_effort_bump(self):
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-e00{i}", "forge-architect", "opus/medium")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-e10{i}", "forge-architect", "opus/medium")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["next_tier"], "opus/high")


class TestRecommendEmptyQueue(TelemetryTestCase):
    def test_empty_dir_produces_no_recommendations_with_thresholds(self):
        empty_dir = tempfile.mkdtemp()
        recs = compute_recommendations(empty_dir)
        self.assertEqual(recs, [])
        table = render_recommendations(recs)
        self.assertIn("no recommendations", table)
        # honesty rule: the thresholds print even when nothing qualifies
        self.assertIn(str(RECOMMEND_MIN_DISPATCHES), table)
        self.assertIn("40", table)


class TestRecommendCLI(TelemetryTestCase):
    def test_main_recommend_flag_prints_qualifying_pairing(self):
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-m00{i}", "forge-worker", "haiku/low")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-m10{i}", "forge-worker", "haiku/low")

        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--recommend", "--dir", self.task_dir])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("forge-worker", out)
        self.assertIn("haiku/low", out)
        self.assertIn("sonnet/low", out)  # next tier up the model ladder

    def test_main_recommend_never_transitions_a_task_file(self):
        _fail_bounce_task(self.task_dir, "fg-m020", "forge-worker", "sonnet/high")
        path = pathlib.Path(self.task_dir) / "fg-m020-fixture.md"
        before = path.read_text(encoding="utf-8")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            main(["--recommend", "--dir", self.task_dir])
        after = path.read_text(encoding="utf-8")
        self.assertEqual(before, after)


class TestNextTierUpNeverLeaksFable(TelemetryTestCase):
    """fg-a10502: _next_tier_up must never emit fable/* as a recommended
    next tier, across the FULL documented escalation grammar -- including
    when the routed input tier is itself fable/* (a human-authorized
    escalation dispatch). fable is human-authorized-only, never an
    automated recommendation target (docs/conventions.md, "Model
    vocabulary -- fable amendment")."""

    def test_next_tier_up_never_returns_fable_for_any_documented_input_tier(self):
        all_tiers = [
            f"{model}/{effort}"
            for model in (_MODEL_LADDER + ["fable"])
            for effort in _EFFORT_LADDER
        ]
        for tier in all_tiers:
            result = _next_tier_up(tier)
            self.assertNotIn(
                "fable",
                str(result),
                msg=f"_next_tier_up({tier!r}) leaked fable: {result!r}",
            )

    def test_next_tier_up_fable_input_yields_no_recommendation(self):
        # A fable/* input (human-authorized escalation dispatch) is already
        # past the automated ceiling -- there is nowhere higher to
        # recommend, so it must behave like an already-at-ceiling pairing
        # (None), never synthesize fable/<next-effort>.
        for effort in ("low", "medium", "high"):
            self.assertIsNone(_next_tier_up(f"fable/{effort}"))

    def test_end_to_end_fable_pairing_qualifies_but_recommends_no_fable(self):
        # Repro from the inquest finding: drive a fable/low pairing to
        # >=5 dispatches / >=40% first-attempt FAIL-or-bounce and confirm
        # render_recommendations never emits "recommend fable/...".
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-f00{i}", "forge-debugger", "fable/low")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-f10{i}", "forge-debugger", "fable/low")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["tier"], "fable/low")
        self.assertIsNone(rec["next_tier"])
        self.assertNotIn("fable", str(rec["next_tier"]).lower())

        table = render_recommendations(recs)
        self.assertNotIn("recommend fable", table.lower())
        self.assertIn("already at ceiling", table)


class TestFindSlugWordBoundary(TelemetryTestCase):
    """fg-a10503: _find_slug must match on word boundaries, not bare
    substring -- a token like "pathfinder" must never attribute to the
    "finder" slug."""

    def test_colliding_token_does_not_fabricate_slug_attribution(self):
        self.assertIsNone(
            _find_slug("attempt 1: pathfinder utility invoked, not an agent")
        )
        self.assertIsNone(_find_slug("ran typefinder helper script"))

    def test_real_slug_still_matches_on_word_boundary(self):
        self.assertEqual(
            _find_slug(
                "attempt 1: finder — verification: kernel synthesis (mode 3)"
            ),
            "finder",
        )

    def test_routing_record_does_not_fabricate_dispatch_from_colliding_token(self):
        parsed = parse_routing_record(
            "attempt 1: pathfinder — sonnet/high — utility script, not a dispatch"
        )
        self.assertIsNone(parsed["entries"][0]["slug"])

    def test_routing_record_real_finder_slug_still_attributes(self):
        parsed = parse_routing_record(
            "attempt 1: finder — verification: kernel synthesis (mode 3) — "
            "sonnet/high — fresh-eyes precedent"
        )
        self.assertEqual(parsed["entries"][0]["slug"], "finder")


if __name__ == "__main__":
    unittest.main()
