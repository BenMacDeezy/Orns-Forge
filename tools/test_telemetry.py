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
    compute_pairing_stats,
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


class TestTokenCaptureSuffix(TelemetryTestCase):
    # fg-a10212 (docs/conventions.md "Token capture — 2026-07-19", amending
    # "Telemetry vocabulary — 2026-07"): an OPTIONAL trailing `[tokens: ...]`
    # suffix on dispatch/verify/re-verify/bounce Attempt-log lines, backward-
    # compatible with every no-suffix line that predates this amendment.

    def test_no_suffix_dispatch_line_parses_exactly_as_before(self):
        stats = parse_attempt_log(
            "attempt 1: dispatched 2026-07-18T10:00:00Z (test fixture)"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(stats["unparsed"], 0)
        self.assertEqual(stats["dispatches"], [{"attempt": 1, "tokens": None}])

    def test_numeric_tokens_suffix_on_dispatch_line(self):
        stats = parse_attempt_log(
            "attempt 1: dispatched 2026-07-18T10:00:00Z (ok) [tokens: 4521]"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(stats["dispatches"], [{"attempt": 1, "tokens": 4521}])

    def test_unreported_tokens_suffix_on_dispatch_line(self):
        stats = parse_attempt_log(
            "attempt 1: dispatched 2026-07-18T10:00:00Z (ok) [tokens: unreported]"
        )
        self.assertEqual(
            stats["dispatches"], [{"attempt": 1, "tokens": "unreported"}]
        )

    def test_numeric_tokens_suffix_on_verify_line(self):
        stats = parse_attempt_log(
            "attempt 1 verify: sonnet/high -> PASS first attempt. [tokens: 9001]"
        )
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(len(stats["verify_verdicts"]), 1)
        self.assertEqual(stats["verify_verdicts"][0]["verdict"], "PASS")
        self.assertEqual(stats["verify_verdicts"][0]["tokens"], 9001)

    def test_numeric_tokens_suffix_on_reverify_line(self):
        stats = parse_attempt_log(
            "attempt 2 re-verify: sonnet/high focused -> PASS. [tokens: 1200]"
        )
        self.assertEqual(stats["verify_verdicts"][0]["kind"], "re-verify")
        self.assertEqual(stats["verify_verdicts"][0]["tokens"], 1200)

    def test_unreported_tokens_suffix_on_bounce_line(self):
        stats = parse_attempt_log(
            "attempt 2 (bounce, JUDGMENT sonnet/high): fixed per FAIL NOTES. "
            "[tokens: unreported]"
        )
        self.assertEqual(len(stats["bounces"]), 1)
        self.assertEqual(stats["bounces"][0]["tokens"], "unreported")
        # the bounce shape's own fields (tier/tag) are unaffected by the
        # trailing suffix strip
        self.assertEqual(stats["bounces"][0]["tag"], "JUDGMENT")

    def test_no_suffix_line_never_counts_as_unreported(self):
        # A line with NO suffix at all is legacy/pre-amendment data -- it
        # must never be conflated with a line that explicitly recorded
        # "[tokens: unreported]".
        _write(
            self.task_dir, "fg-tk001",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (no suffix at all)",
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["tokens"]["unreported"], 0)
        self.assertEqual(report["tokens"]["lines_with_tokens"], 0)
        self.assertEqual(report["tokens"]["measured"]["total"], 0)

    def test_malformed_suffix_non_numeric_falls_to_unparsed(self):
        stats = parse_attempt_log(
            "attempt 1: dispatched 2026-07-18T10:00:00Z (ok) [tokens: abc]"
        )
        self.assertEqual(stats["dispatches"], [])
        self.assertEqual(stats["unparsed"], 1)
        self.assertEqual(stats["parsed"], 0)

    def test_malformed_suffix_empty_value_falls_to_unparsed(self):
        stats = parse_attempt_log(
            "attempt 1 verify: sonnet/high -> PASS. [tokens: ]"
        )
        self.assertEqual(stats["verify_verdicts"], [])
        self.assertEqual(stats["unparsed"], 1)

    def test_malformed_suffix_never_silently_partial_parses(self):
        # A malformed suffix must fail the WHOLE line -- the verdict/tier
        # that would otherwise have parsed cleanly must NOT sneak through.
        stats = parse_attempt_log(
            "attempt 1 verify: sonnet/high -> FAIL (MECHANICAL): reason. "
            "[tokens: -5]"
        )
        self.assertEqual(stats["verify_verdicts"], [])
        self.assertEqual(stats["unparsed"], 1)

    def test_aggregate_sums_measured_tokens_per_layer_and_slug(self):
        _write(
            self.task_dir, "fg-tk002",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok) [tokens: 1000]\n\n"
                "attempt 1 verify: sonnet/high -> FAIL (MECHANICAL): reason. "
                "[tokens: 2000]\n\n"
                "attempt 2 (bounce, MECHANICAL sonnet/high): fixed. "
                "[tokens: 300]\n\n"
                "attempt 2 re-verify: sonnet/high -> PASS. [tokens: 500]"
            ),
        )
        _write(
            self.task_dir, "fg-tk003",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok) [tokens: unreported]\n\n"
                "attempt 1 verify: sonnet/high -> PASS. [tokens: 700]"
            ),
        )
        report = aggregate(self.task_dir)
        tok = report["tokens"]
        # build: 1000 (tk002) + 0 unreported (tk003) = 1000
        # verify: 2000 + 500 (tk002, both verify-kind lines) + 700 (tk003) = 3200
        # bounce: 300 (tk002)
        self.assertEqual(tok["measured"]["build"], 1000)
        self.assertEqual(tok["measured"]["verify"], 3200)
        self.assertEqual(tok["measured"]["bounce"], 300)
        self.assertEqual(tok["measured"]["total"], 4500)
        self.assertEqual(tok["unreported"], 1)
        self.assertEqual(tok["lines_with_tokens"], 6)
        self.assertEqual(
            tok["per_slug"]["forge-worker"],
            {"build": 1000, "verify": 3200, "bounce": 300, "total": 4500},
        )

    def test_render_table_shows_measured_tokens_labeled_not_estimate(self):
        _write(
            self.task_dir, "fg-tk004",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log=(
                "attempt 1: dispatched 2026-07-18T00:00:00Z (ok) [tokens: 1500]\n\n"
                "attempt 1 verify: sonnet/high -> PASS. [tokens: 2500]"
            ),
        )
        report = aggregate(self.task_dir)
        table = render_table(report)
        self.assertIn("MEASURED", table)
        self.assertIn("legacy relative-cost estimate", table)
        self.assertIn("build 1500", table)
        self.assertIn("verify 2500", table)
        self.assertIn("total 4000", table)
        self.assertIn("forge-worker", table)

    def test_render_table_no_tokens_recorded_says_so_plainly(self):
        _write(
            self.task_dir, "fg-tk005",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (no suffix)",
        )
        report = aggregate(self.task_dir)
        table = render_table(report)
        self.assertIn(
            "(none recorded -- no Attempt-log line carries a "
            "[tokens: ...] suffix yet)",
            table,
        )

    def test_json_output_includes_tokens_field(self):
        _write(
            self.task_dir, "fg-tk006",
            routing="attempt 1: forge-worker — sonnet/high — well-specified",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (ok) [tokens: 42]",
        )
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--json", "--dir", self.task_dir])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["tokens"]["measured"]["build"], 42)
        self.assertEqual(data["tokens"]["per_slug"]["forge-worker"]["build"], 42)


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


class TestOpusMaxTierParses(TelemetryTestCase):
    """docs/conventions.md, Telemetry vocabulary: `max` is a valid effort
    value (kernel ROUTE+DISPATCH's Critical/forensic row routes at
    opus/max) -- TIER_RE must recognize it so opus/max lines parse and
    count instead of silently falling out of the (slug, tier) pairing
    stats (the `not first_entry["tier"]` skip in compute_pairing_stats
    treats an unmatched tier exactly like a tier-less legacy line)."""

    def test_parse_routing_record_extracts_opus_max_tier(self):
        parsed = parse_routing_record(
            "attempt 1: forge-security — opus/max — critical forensic "
            "final gate on a big merge"
        )
        self.assertEqual(
            parsed["entries"], [{"slug": "forge-security", "tier": "opus/max"}]
        )

    def test_opus_max_pairing_is_counted_not_dropped(self):
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-m00{i}", "forge-security", "opus/max")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-m10{i}", "forge-security", "opus/max")

        pairings = compute_pairing_stats(self.task_dir)
        self.assertIn(("forge-security", "opus/max"), pairings)
        self.assertEqual(pairings[("forge-security", "opus/max")]["dispatches"], 5)
        self.assertEqual(
            pairings[("forge-security", "opus/max")]["fail_or_bounce"], 3
        )

    def test_opus_max_never_recommended_as_a_next_tier(self):
        """A qualifying opus/max pairing reports the ceiling (None), same as
        opus/high -- `max` is parsed/counted but _EFFORT_LADDER deliberately
        excludes it, so it can never appear as a `next_tier` recommendation
        target."""
        for i in range(3):
            _fail_bounce_task(self.task_dir, f"fg-n00{i}", "forge-security", "opus/max")
        for i in range(2):
            _clean_pass_task(self.task_dir, f"fg-n10{i}", "forge-security", "opus/max")

        recs = compute_recommendations(self.task_dir)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["tier"], "opus/max")
        self.assertIsNone(recs[0]["next_tier"])
        self.assertNotIn("max", str(recs[0]["next_tier"]))


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


class TestFindSlugScopedToDispatchTargetToken(TelemetryTestCase):
    """_find_slug via parse_routing_record must only search the
    dispatch-target token immediately after "attempt N:" -- not the whole
    line -- so a slug merely mentioned in the rationale text never shadows
    the actually-dispatched slug. Confirmed live repro: a line dispatching
    forge-ui but mentioning forge-ui-verifier in its rationale was
    misattributed to forge-ui-verifier."""

    def test_slug_mentioned_only_in_rationale_does_not_shadow_dispatch_target(self):
        parsed = parse_routing_record(
            "attempt 1: forge-ui - sonnet/medium - matches forge-ui-verifier "
            "suggested pattern from a related PR"
        )
        self.assertEqual(parsed["entries"][0]["slug"], "forge-ui")

    def test_aggregate_attributes_dispatch_to_target_not_rationale_mention(self):
        _write(
            self.task_dir, "fg-t016",
            routing="attempt 1: forge-ui - sonnet/medium - matches "
                    "forge-ui-verifier suggested pattern from a related PR",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)",
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["agent_dispatch_counts"].get("forge-ui"), 1)
        self.assertIsNone(report["agent_dispatch_counts"].get("forge-ui-verifier"))


class TestLegacyVerifyPhrasingParses(TelemetryTestCase):
    """fg-a11023 (restates docs/audits/2026-07-18-protocol-overhead-audit.md
    Recommendation 2, Finding 2): a large block of tasks predating the
    canonical "attempt N verify:"/"attempt N verdict:" phrasing instead
    wrote "attempt N: verifier PASS|FAIL (tier) TIMESTAMP; integrated" --
    VERIFY_RE's exact-form requirement silently drops these clean,
    well-evidenced first-attempt verdicts from telemetry entirely (they
    land in the unparsed tally instead of first_attempt/verify_verdicts).
    Live repro lines below are the ACTUAL committed Attempt-log text from
    fg-9a0101/fg-9a0301/fg-9a0303/fg-9b0101/fg-9b0302/fg-9b0304 (clean
    PASS), fg-9b0303 (tier tucked inside a longer parenthetical), and
    fg-9a0304/fg-9b0102 (a bounce-and-retry narrated in one physical
    line, where the re-verify's own PASS/FAIL must still be recognized)."""

    def test_clean_legacy_verifier_pass_line_parses(self):
        stats = parse_attempt_log(
            "attempt 1: verifier PASS (opus/high) 2026-07-17T23:08:51Z; "
            "integrated. Originally dispatched 2026-07-17T22:57:38Z "
            "(parallel wave, worktree isolation waived)"
        )
        self.assertEqual(stats["unparsed"], 0)
        self.assertEqual(stats["parsed"], 1)
        self.assertEqual(len(stats["verify_verdicts"]), 1)
        v = stats["verify_verdicts"][0]
        self.assertEqual(v["attempt"], 1)
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["tier"], "opus/high")

    def test_legacy_fail_with_tier_inside_longer_parenthetical(self):
        # fg-9b0303's live line: the tier shares a paren with extra prose
        # ("sonnet/high, rule-3 doc-pin gap") instead of standing alone.
        stats = parse_attempt_log(
            "attempt 1: verifier FAIL (sonnet/high, rule-3 doc-pin gap); "
            "attempt 2 (haiku/low) closed via prescription; kernel closure "
            "check 2026-07-18T00:37:20Z; integrated."
        )
        self.assertEqual(stats["unparsed"], 0)
        v = stats["verify_verdicts"][0]
        self.assertEqual(v["verdict"], "FAIL")
        self.assertEqual(v["tier"], "sonnet/high")

    def test_legacy_bounce_and_reverify_narrated_in_one_line_recognizes_reverify(self):
        # fg-9a0304's live line: no canonical "attempt N verify:" marker at
        # all -- the re-verify's own PASS is what must be recognized.
        stats = parse_attempt_log(
            "attempt 2: bounce dispatched, closed all findings; re-verify "
            "PASS (sonnet/high) 2026-07-17T23:38:38Z; integrated"
        )
        self.assertEqual(stats["unparsed"], 0)
        v = stats["verify_verdicts"][0]
        self.assertEqual(v["attempt"], 2)
        self.assertEqual(v["kind"], "re-verify")
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["tier"], "sonnet/high")

    def test_legacy_first_fail_in_a_two_event_line_still_recognized(self):
        # fg-9b0102's live line narrates attempt-1 FAIL/bounce AND attempt-2
        # re-verify PASS in one physical line; the FIRST recognizable
        # verdict (attempt 1 FAIL) must not be silently dropped.
        stats = parse_attempt_log(
            "attempt 1: verifier FAIL (opus/high), bounced; attempt 2: "
            "re-verify PASS (sonnet/high) 2026-07-18T00:29:52Z; integrated."
        )
        self.assertEqual(stats["unparsed"], 0)
        v = stats["verify_verdicts"][0]
        self.assertEqual(v["attempt"], 1)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertEqual(v["tier"], "opus/high")

    def test_aggregate_counts_legacy_pass_as_first_attempt_pass(self):
        _write(
            self.task_dir, "fg-t018",
            routing="attempt 1: forge-worker — sonnet/high — legacy-era task",
            attempt_log=(
                "attempt 1: verifier PASS (opus/high) 2026-07-17T23:08:51Z; "
                "integrated."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["attempt_lines_unparsed"], 0)
        self.assertEqual(report["first_attempt"], {"pass": 1, "total": 1})


class TestLegacyBouncePhrasingParses(TelemetryTestCase):
    """fg-a11023 (Finding 1): the canonical "attempt N (bounce, TAG): ..."
    marker was introduced partway through the project; earlier tasks
    narrate a bounce as prose ending in a "FAIL (bounce N/M)" parenthetical
    marker instead -- an adjacent form of the same "(bounce...)" idiom
    BOUNCE_RE already recognizes, just placed differently. Live repro is
    the ACTUAL committed fg-a100 Attempt-log line."""

    def test_legacy_fail_bounce_marker_parses_as_a_bounce(self):
        stats = parse_attempt_log(
            "forge-verifier/opus reproduced all 4 criteria behaviorally BUT "
            "reported constitution rules 1 & 3 = `no`. Kernel done bar: any "
            "constitution `no` fails verification → FAIL (bounce 1/2). "
            "Fix required: add an automated regression test."
        )
        self.assertEqual(stats["unparsed"], 0)
        self.assertEqual(len(stats["bounces"]), 1)
        self.assertEqual(stats["bounces"][0]["attempt"], 1)

    def test_bounce_pre_check_mechanism_mention_is_not_misclassified(self):
        # "(bounce pre-check)" names the verifier finding-filter mechanism,
        # not an actual bounce event -- must not be swept up by the new
        # legacy-bounce pattern (real committed fg-a10205 line).
        stats = parse_attempt_log(
            "kernel filter (bounce pre-check): SURVIVES — location "
            "confirmed at SKILL.md:19 verbatim; MDN fact independently "
            "correct; pins anchor rule headings only, fix collides with "
            "nothing."
        )
        self.assertEqual(stats["parsed"], 0)
        self.assertEqual(stats["unparsed"], 1)
        self.assertEqual(len(stats["bounces"]), 0)

    def test_aggregate_counts_legacy_bounce(self):
        _write(
            self.task_dir, "fg-t019",
            routing="attempt 1: forge-worker — sonnet/high — legacy-era task",
            attempt_log=(
                "forge-verifier/opus reported constitution rules 1 & 3 = "
                "`no`. Kernel done bar: any constitution `no` fails "
                "verification → FAIL (bounce 1/2)."
            ),
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["attempt_lines_unparsed"], 0)
        self.assertEqual(report["bounces"]["total"], 1)


class TestDispatchTierIgnoresStaleRationaleMention(TelemetryTestCase):
    """fg-a11029: this task's own acceptance-criteria repro line --
    `attempt 1: forge-spec-writer - previously bounced from opus/high;
    retry at sonnet/low` -- is a LEGACY/malformed Routing record entry
    with only ONE field separator: it never wrote a delimited tier field
    at all (unlike the canonical `attempt N: <slug> — <tier> —
    <rationale>` 3-field shape). Because a properly-delimited 3-field line
    already puts its real tier BEFORE any tier the rationale might
    separately mention (fields read left to right), plain first-match
    search was never actually wrong for THAT shape -- verified directly:
    scoping `_find_tier` to `_dispatch_target_text` (the literal Execution
    plan wording, reusing the SLUG-scoped substring verbatim) would in
    fact regress the already-passing
    test_parse_routing_record_directly_extracts_slug_and_tier, since the
    slug field never contains a tier at all (always None).

    The real, reproducible bug is specific to this missing-tier-field
    shape: first-match search over the whole line finds the STALE
    "opus/high" mention (from "previously bounced from...") before the
    real, current "retry at sonnet/low" tier. The fix (`_dispatch_tier`)
    detects this one-separator shape and prefers the LAST tier mention in
    the rationale instead of the first, matching its own "previously X;
    retry at Y" temporal convention -- while a properly 3-field-delimited
    line keeps ordinary field-scoped, first-match extraction (unaffected
    by anything the rationale separately mentions)."""

    def test_live_acceptance_criteria_repro_extracts_the_current_tier(self):
        parsed = parse_routing_record(
            "attempt 1: forge-spec-writer - previously bounced from "
            "opus/high; retry at sonnet/low"
        )
        self.assertEqual(parsed["entries"][0]["tier"], "sonnet/low")
        self.assertNotEqual(parsed["entries"][0]["tier"], "opus/high")

    def test_clean_three_field_line_still_extracts_its_own_tier(self):
        # Non-regression: the existing canonical-form test's exact line.
        parsed = parse_routing_record(
            "attempt 1: forge-verifier — opus/high — equal-or-higher tier"
        )
        self.assertEqual(
            parsed["entries"], [{"slug": "forge-verifier", "tier": "opus/high"}]
        )

    def test_three_field_line_is_unaffected_by_a_rationale_mentioning_another_tier(self):
        # A properly-delimited line already isolates its own tier field
        # positionally BEFORE the rationale -- confirms the fix doesn't
        # need (and doesn't apply) last-match preference here.
        parsed = parse_routing_record(
            "attempt 1: forge-spec-writer — sonnet/low — previously bounced "
            "from opus/high; retry at sonnet/low"
        )
        self.assertEqual(parsed["entries"][0]["tier"], "sonnet/low")

    def test_aggregate_attributes_the_current_tier_not_the_stale_mention(self):
        _write(
            self.task_dir, "fg-t020",
            routing="attempt 1: forge-spec-writer - previously bounced from "
                    "opus/high; retry at sonnet/low",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (retry)",
        )
        pairings = compute_pairing_stats(self.task_dir)
        self.assertIn(("forge-spec-writer", "sonnet/low"), pairings)
        self.assertNotIn(("forge-spec-writer", "opus/high"), pairings)


class TestDispatchTierIsASupersetOfHeadOnLiveLines(TelemetryTestCase):
    """Regression pin (verifier BOUNCE on the fg-a11029 batch, 2026-07-19):
    the field-scoped extraction above must be a STRICT SUPERSET of HEAD's
    plain whole-line, first-match `_find_tier(line)` -- it may only REFINE
    a correct baseline answer, never trade one away for a scoped miss.
    The first version of this fix regressed 7 live Routing-record lines
    from a correct tier to None while fixing zero real lines (the
    "previously bounced ... retry at ..." shape this fix targets exists
    only in fg-a11029's own synthetic acceptance-criteria repro, never in
    a real committed Routing record). These four are the ACTUAL live
    lines cited in that finding, byte-for-byte from this repo's own
    queue at the time of the bounce."""

    def test_tier_stated_with_no_separator_before_it_at_all(self):
        # fg-a10909's live line: the tier sits INSIDE the dispatch-target
        # token itself (no separator between slug and tier at all) --
        # HEAD finds it via plain whole-line search; the one-separator
        # branch's post-target-only search must fall back to that
        # baseline rather than reporting None.
        parsed = parse_routing_record(
            "attempt 1: forge-worker sonnet/medium or Grud if fully "
            "specified at dispatch; verify gates-inline (docs-only, "
            "pin-covered) per Low-risk predicate — NORMATIVE-prose "
            "caveat: the conventions edit itself takes a real verifier "
            "per the Low-risk disqualifier."
        )
        self.assertEqual(parsed["entries"][0]["tier"], "sonnet/medium")

    def test_extra_field_between_slug_and_tier_kernel_synthesis_mode_3(self):
        # fg-9b0201/9b0202/9b0203/9b0204's live shape: a "verification:
        # kernel synthesis (mode 3)" field sits BETWEEN slug and tier, so
        # field 2 (between separators 1 and 2) is NOT the tier field for
        # this line shape -- must fall back to the whole-line baseline.
        parsed = parse_routing_record(
            "attempt 1: finder — verification: kernel synthesis (mode 3) "
            "— sonnet/high — fresh-eyes precedent"
        )
        self.assertEqual(parsed["entries"][0]["tier"], "sonnet/high")

    def test_spurious_separator_shaped_em_dash_inside_a_parenthetical(self):
        # fg-a10901's live line: an em-dash INSIDE a parenthetical aside
        # ("(likely — pipelining...)") reads as a second field separator,
        # so field 2 stops well before the real "verify opus/high" tier
        # clause -- must fall back to the whole-line baseline.
        parsed = parse_routing_record(
            "attempt 1: forge-spec-writer -> spec draft for human "
            "ratification at the gate; then forge-architect if the "
            "kernel-loop delta exceeds a mechanical stub change (likely "
            "— pipelining alters the loop's wait discipline); verify "
            "opus/high (touches the dispatch loop + the verification "
            "safety floor)."
        )
        self.assertEqual(parsed["entries"][0]["tier"], "opus/high")

    def test_two_arrow_dispatch_chain_before_the_real_tier(self):
        # fg-a10902's live line: TWO "->" arrows in a dispatch chain
        # (forge-researcher -> forge-spec-writer -> ...) both read as
        # field separators, so field 2 is just "forge-spec-writer" -- the
        # real "verify opus/high" tier is well past both -- must fall
        # back to the whole-line baseline.
        parsed = parse_routing_record(
            "attempt 1: forge-researcher (Phase 0, CLI contracts) -> "
            "forge-spec-writer -> spec draft for human gate; then "
            "forge-architect (profile overlay + dispatch design); "
            "verify opus/high (touches routing + trust surface)."
        )
        self.assertEqual(parsed["entries"][0]["tier"], "opus/high")

    def test_aggregate_pairing_count_matches_head_on_the_live_queue(self):
        # compute_pairing_stats over the real, live task-directory copies
        # of all four flagged tasks must recover the SAME (slug, tier)
        # pairings HEAD would -- none of the four collapse to a
        # tier=None entry (which compute_pairing_stats skips outright,
        # silently shrinking the pairing count -- the reported
        # 11->10-pairings/forge-researcher-disappears regression).
        _write(
            self.task_dir, "fg-x001",
            routing="attempt 1: forge-worker sonnet/medium or Grud if "
                    "fully specified at dispatch; verify gates-inline "
                    "(docs-only, pin-covered) per Low-risk predicate — "
                    "NORMATIVE-prose caveat: the conventions edit itself "
                    "takes a real verifier per the Low-risk disqualifier.",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (x)",
        )
        _write(
            self.task_dir, "fg-x002",
            routing="attempt 1: forge-researcher (Phase 0, CLI contracts) "
                    "-> forge-spec-writer -> spec draft for human gate; "
                    "then forge-architect (profile overlay + dispatch "
                    "design); verify opus/high (touches routing + trust "
                    "surface).",
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (x)",
        )
        pairings = compute_pairing_stats(self.task_dir)
        self.assertIn(("forge-worker", "sonnet/medium"), pairings)
        self.assertIn(("forge-researcher", "opus/high"), pairings)


class TestArrowSeparatorDispatchTarget(TelemetryTestCase):
    """fg-a10928: ATTEMPT_TARGET_RE only recognized "\\s[-—]\\s" (hyphen/em-
    dash, whitespace both sides) as the field separator after "attempt N:".
    A routing line using "->" as its separator fell through to whole-line
    search, so _find_slug picked up a slug merely MENTIONED in the
    rationale text (forge-ui-verifier) instead of the actual dispatch
    target (forge-spec-writer). Live repro: this is the EXACT Routing
    record line committed at
    .forge/queue/tasks/fg-a10602-iris-design-conformance.md line 26."""

    _LIVE_LINE = (
        "attempt 1: forge-spec-writer -> part of the fg-a10601 spec; then "
        "forge-worker for the agent-contract change; verify "
        "forge-ui-verifier-adjacent at opus/high (changes the UI "
        "acceptance bar)"
    )

    def test_live_fg_a10602_line_parses_to_dispatch_target_not_rationale_mention(self):
        parsed = parse_routing_record(self._LIVE_LINE)
        self.assertEqual(parsed["entries"][0]["slug"], "forge-spec-writer")
        self.assertNotEqual(parsed["entries"][0]["slug"], "forge-ui-verifier")

    def test_aggregate_attributes_arrow_dispatch_to_target_not_rationale_mention(self):
        _write(
            self.task_dir, "fg-t017",
            routing=self._LIVE_LINE,
            attempt_log="attempt 1: dispatched 2026-07-18T00:00:00Z (wave)",
        )
        report = aggregate(self.task_dir)
        self.assertEqual(report["agent_dispatch_counts"].get("forge-spec-writer"), 1)
        self.assertIsNone(report["agent_dispatch_counts"].get("forge-ui-verifier"))


if __name__ == "__main__":
    unittest.main()
