"""Tests for tools/benchmark/metrics.py (fg-a10405, design D6:
docs/plans/2026-07-18-ab-benchmark-design.md lines ~196-211).

Fixtures build RunRecord / ScorecardRecord dicts inline per the contract
documented in metrics.py's module docstring, mirroring tools/test_telemetry.py's
class-per-scenario / descriptive-method-name style.
"""
import json
import pathlib
import tempfile
import unittest

from metrics import (
    ARM_A_ATTEMPT_KINDS,
    ARM_B_ATTEMPT_KINDS,
    PROXY_WEIGHTS,
    MetricsInputError,
    build_pair_rows,
    compute_caught,
    compute_defects,
    compute_tokens,
    compute_turns,
    load_json_records,
    main,
    parse_model_tier,
    render_table,
)


def _run_record(task_id="B1", arm="A", run_id="b1-a-0001",
                 model_tier="sonnet/high", wall_clock_seconds=100.0,
                 attempts=None):
    return {
        "task_id": task_id,
        "arm": arm,
        "run_id": run_id,
        "model_tier": model_tier,
        "wall_clock_seconds": wall_clock_seconds,
        "attempts": attempts if attempts is not None else [],
    }


def _scorecard(task_id="B1", arm="A", run_id="b1-a-0001",
               checklist_results=None, additional_defects=None):
    return {
        "task_id": task_id,
        "arm": arm,
        "run_id": run_id,
        "checklist_results": checklist_results if checklist_results is not None else [],
        "additional_defects": additional_defects if additional_defects is not None else [],
    }


# ---------------------------------------------------------------------------
# compute_turns
# ---------------------------------------------------------------------------

class TestComputeTurns(unittest.TestCase):
    def test_arm_a_counts_dispatch_verify_bounce_reverify_lines(self):
        rec = _run_record(arm="A", attempts=[
            {"kind": "dispatch"},
            {"kind": "verify", "verdict": "FAIL"},
            {"kind": "bounce"},
            {"kind": "re-verify", "verdict": "PASS"},
        ])
        self.assertEqual(compute_turns(rec), 4)

    def test_arm_b_counts_turn_entries(self):
        rec = _run_record(arm="B", attempts=[{"kind": "turn"}] * 5)
        self.assertEqual(compute_turns(rec), 5)

    def test_arm_b_rejects_verify_kind_never_summed_as_arm_a_shape(self):
        rec = _run_record(arm="B", attempts=[{"kind": "verify"}])
        with self.assertRaises(MetricsInputError):
            compute_turns(rec)

    def test_arm_a_rejects_turn_kind(self):
        rec = _run_record(arm="A", attempts=[{"kind": "turn"}])
        with self.assertRaises(MetricsInputError):
            compute_turns(rec)

    def test_unknown_arm_rejected(self):
        rec = _run_record(arm="C", attempts=[])
        with self.assertRaises(MetricsInputError):
            compute_turns(rec)


# ---------------------------------------------------------------------------
# parse_model_tier
# ---------------------------------------------------------------------------

class TestParseModelTier(unittest.TestCase):
    def test_parses_valid_tier(self):
        self.assertEqual(parse_model_tier("sonnet/high"), ("sonnet", "high"))

    def test_rejects_malformed_tier(self):
        with self.assertRaises(MetricsInputError):
            parse_model_tier("sonnet-high")

    def test_rejects_unknown_model(self):
        with self.assertRaises(MetricsInputError):
            parse_model_tier("gpt4/high")


# ---------------------------------------------------------------------------
# compute_tokens -- measured vs proxy vs unavailable; never invented
# ---------------------------------------------------------------------------

class TestComputeTokensMeasured(unittest.TestCase):
    def test_all_attempts_reported_sums_exactly(self):
        rec = _run_record(attempts=[
            {"kind": "dispatch", "tokens": 1000},
            {"kind": "verify", "tokens": 2500},
        ])
        result = compute_tokens(rec)
        self.assertEqual(result["regime"], "measured")
        self.assertEqual(result["value"], 3500)
        self.assertTrue(result["complete"])

    def test_partial_reporting_sums_only_known_and_flags_incomplete(self):
        rec = _run_record(attempts=[
            {"kind": "dispatch", "tokens": 1000},
            {"kind": "verify", "tokens": None},
        ])
        result = compute_tokens(rec)
        self.assertEqual(result["regime"], "measured")
        self.assertEqual(result["value"], 1000)
        self.assertFalse(result["complete"])
        self.assertIn("missing", result["note"].lower())


class TestComputeTokensProxy(unittest.TestCase):
    def test_no_tokens_reported_falls_back_to_turn_proxy(self):
        rec = _run_record(model_tier="sonnet/high", attempts=[
            {"kind": "dispatch", "tokens": None},
            {"kind": "verify", "tokens": None},
        ])
        result = compute_tokens(rec)
        self.assertEqual(result["regime"], "proxy")
        # 2 turns * sonnet/high weight (12.5, audit A.3 table)
        self.assertEqual(result["value"], 2 * PROXY_WEIGHTS[("sonnet", "high")])
        self.assertIn("ESTIMATE", result["note"])

    def test_proxy_labeled_never_marked_complete(self):
        rec = _run_record(model_tier="haiku/low", attempts=[{"kind": "dispatch", "tokens": None}])
        result = compute_tokens(rec)
        self.assertFalse(result["complete"])

    def test_missing_model_tier_is_unavailable_not_invented(self):
        rec = _run_record(model_tier=None, attempts=[{"kind": "dispatch", "tokens": None}])
        result = compute_tokens(rec)
        self.assertEqual(result["regime"], "unavailable")
        self.assertIsNone(result["value"])

    def test_empty_attempts_and_no_tokens_is_unavailable_zero_turns(self):
        rec = _run_record(model_tier="sonnet/high", attempts=[])
        result = compute_tokens(rec)
        # zero turns * weight is a real, honest zero -- not a missing-data case
        self.assertEqual(result["regime"], "proxy")
        self.assertEqual(result["value"], 0)

    def test_unknown_model_effort_combo_raises(self):
        rec = _run_record(model_tier="opus/ultra", attempts=[{"kind": "dispatch", "tokens": None}])
        with self.assertRaises(MetricsInputError):
            compute_tokens(rec)


# ---------------------------------------------------------------------------
# compute_defects
# ---------------------------------------------------------------------------

class TestComputeDefects(unittest.TestCase):
    def test_defect_present_checklist_items_counted_with_severity(self):
        sc = _scorecard(checklist_results=[
            {"item_id": "b1-conserve-total", "status": "defect-present", "severity": "important"},
            {"item_id": "b1-regression-test", "status": "satisfied", "severity": None},
        ])
        defects = compute_defects(sc)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["item_id"], "b1-conserve-total")
        self.assertEqual(defects[0]["severity"], "important")
        self.assertEqual(defects[0]["source"], "checklist")

    def test_na_items_excluded(self):
        sc = _scorecard(checklist_results=[
            {"item_id": "x", "status": "n/a", "severity": None},
        ])
        self.assertEqual(compute_defects(sc), [])

    def test_additional_defects_counted(self):
        sc = _scorecard(additional_defects=[
            {"description": "unrelated crash found", "severity": "minor"},
        ])
        defects = compute_defects(sc)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["source"], "additional")
        self.assertIsNone(defects[0]["item_id"])

    def test_defect_present_without_severity_raises(self):
        sc = _scorecard(checklist_results=[
            {"item_id": "x", "status": "defect-present", "severity": None},
        ])
        with self.assertRaises(MetricsInputError):
            compute_defects(sc)

    def test_invalid_status_raises(self):
        sc = _scorecard(checklist_results=[{"item_id": "x", "status": "maybe"}])
        with self.assertRaises(MetricsInputError):
            compute_defects(sc)

    def test_invalid_severity_raises(self):
        sc = _scorecard(additional_defects=[{"description": "d", "severity": "catastrophic"}])
        with self.assertRaises(MetricsInputError):
            compute_defects(sc)


# ---------------------------------------------------------------------------
# compute_caught -- D6: "defects appearing in a verifier FAIL note AND
# absent from final diff"
# ---------------------------------------------------------------------------

class TestComputeCaught(unittest.TestCase):
    def test_defect_flagged_fail_and_fixed_before_final_diff_is_caught(self):
        run = _run_record(arm="A", attempts=[
            {"kind": "dispatch"},
            {"kind": "verify", "verdict": "FAIL", "fail_item_ids": ["b1-conserve-total"]},
            {"kind": "bounce"},
            {"kind": "re-verify", "verdict": "PASS", "fail_item_ids": []},
        ])
        final_sc = _scorecard(checklist_results=[
            {"item_id": "b1-conserve-total", "status": "satisfied", "severity": None},
        ])
        self.assertEqual(compute_caught(run, final_sc), ["b1-conserve-total"])

    def test_defect_flagged_fail_but_still_in_final_diff_is_not_caught(self):
        run = _run_record(arm="A", attempts=[
            {"kind": "verify", "verdict": "FAIL", "fail_item_ids": ["b1-conserve-total"]},
        ])
        final_sc = _scorecard(checklist_results=[
            {"item_id": "b1-conserve-total", "status": "defect-present", "severity": "important"},
        ])
        # still present in the final (blinded) diff -> escaped, not caught
        self.assertEqual(compute_caught(run, final_sc), [])

    def test_never_flagged_is_not_caught(self):
        run = _run_record(arm="A", attempts=[{"kind": "verify", "verdict": "PASS", "fail_item_ids": []}])
        final_sc = _scorecard(checklist_results=[])
        self.assertEqual(compute_caught(run, final_sc), [])

    def test_rejects_arm_b_run_record(self):
        run = _run_record(arm="B", attempts=[{"kind": "turn"}])
        sc = _scorecard(arm="B")
        with self.assertRaises(MetricsInputError):
            compute_caught(run, sc)


# ---------------------------------------------------------------------------
# build_pair_rows -- joins run records + scorecards; never sums across arms
# ---------------------------------------------------------------------------

class TestBuildPairRows(unittest.TestCase):
    def test_joins_run_record_and_scorecard_by_run_id(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-a-1", attempts=[
            {"kind": "dispatch", "tokens": 500},
        ])
        sc_a = _scorecard(task_id="B1", arm="A", run_id="b1-a-1", checklist_results=[
            {"item_id": "x", "status": "defect-present", "severity": "minor"},
        ])
        rows = build_pair_rows([run_a], [sc_a])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["task_id"], "B1")
        self.assertEqual(row["arm"], "A")
        self.assertEqual(row["run_id"], "b1-a-1")
        self.assertEqual(row["wall_clock_seconds"], 100.0)
        self.assertEqual(row["turns"], 1)
        self.assertEqual(row["defects_escaped_count"], 1)

    def test_missing_scorecard_leaves_defect_fields_none_not_zero(self):
        run_b = _run_record(task_id="B1", arm="B", run_id="b1-b-1", attempts=[{"kind": "turn"}])
        rows = build_pair_rows([run_b], [])
        row = rows[0]
        self.assertIsNone(row["defects_escaped_count"])
        self.assertIn("no scorecard", row["note"].lower())

    def test_arm_b_row_has_no_caught_field_value(self):
        run_b = _run_record(task_id="B1", arm="B", run_id="b1-b-1", attempts=[{"kind": "turn"}])
        sc_b = _scorecard(task_id="B1", arm="B", run_id="b1-b-1", checklist_results=[
            {"item_id": "x", "status": "defect-present", "severity": "minor"},
        ])
        rows = build_pair_rows([run_b], [sc_b])
        row = rows[0]
        self.assertIsNone(row["defects_caught_count"])

    def test_arm_a_row_computes_caught_count(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-a-2", attempts=[
            {"kind": "verify", "verdict": "FAIL", "fail_item_ids": ["x"]},
            {"kind": "bounce"},
            {"kind": "re-verify", "verdict": "PASS", "fail_item_ids": []},
        ])
        sc_a = _scorecard(task_id="B1", arm="A", run_id="b1-a-2", checklist_results=[
            {"item_id": "x", "status": "satisfied", "severity": None},
        ])
        rows = build_pair_rows([run_a], [sc_a])
        self.assertEqual(rows[0]["defects_caught_count"], 1)

    def test_shared_per_pair_run_id_raises_not_silently_cross_joined(self):
        # Verifier repro (fg-a10405 bounce 1): runner.run_pair's raw output
        # shape emits ONE run_id per PAIR, shared across both arms. Before
        # the fix this let arm B silently inherit arm A's scorecard. Now it
        # must raise before any join is even attempted.
        run_a = _run_record(task_id="B1", arm="A", run_id="pair-7", attempts=[{"kind": "dispatch"}])
        run_b = _run_record(task_id="B1", arm="B", run_id="pair-7", attempts=[{"kind": "turn"}])
        sc_a = _scorecard(task_id="B1", arm="A", run_id="pair-7", checklist_results=[
            {"item_id": "x", "status": "defect-present", "severity": "minor"},
        ])
        with self.assertRaises(MetricsInputError) as ctx:
            build_pair_rows([run_a, run_b], [sc_a])
        self.assertIn("pair-7", str(ctx.exception))

    def test_arm_mismatched_scorecard_join_raises(self):
        # Unique run_ids (correct shape), but the scorecard for run_id "x"
        # claims arm B while the run record for "x" is arm A -- a
        # cross-arm join must never be silently accepted.
        run_a = _run_record(task_id="B1", arm="A", run_id="x", attempts=[{"kind": "dispatch"}])
        sc_wrong_arm = _scorecard(task_id="B1", arm="B", run_id="x", checklist_results=[
            {"item_id": "y", "status": "defect-present", "severity": "minor"},
        ])
        with self.assertRaises(MetricsInputError) as ctx:
            build_pair_rows([run_a], [sc_wrong_arm])
        self.assertIn("cross-arm", str(ctx.exception).lower())

    def test_orphaned_scorecard_raises_instead_of_silently_dropped(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-a-orphan-test",
                             attempts=[{"kind": "dispatch"}])
        sc_orphan = _scorecard(task_id="B1", arm="A", run_id="no-such-run-id",
                                checklist_results=[])
        with self.assertRaises(MetricsInputError) as ctx:
            build_pair_rows([run_a], [sc_orphan])
        self.assertIn("no-such-run-id", str(ctx.exception))

    def test_happy_path_per_arm_unique_ids_both_arms_join_correctly(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-happy-a", attempts=[
            {"kind": "verify", "verdict": "FAIL", "fail_item_ids": ["only-in-a"]},
        ])
        run_b = _run_record(task_id="B1", arm="B", run_id="b1-happy-b", attempts=[{"kind": "turn"}])
        sc_a = _scorecard(task_id="B1", arm="A", run_id="b1-happy-a", checklist_results=[
            {"item_id": "only-in-a", "status": "satisfied", "severity": None},
        ])
        sc_b = _scorecard(task_id="B1", arm="B", run_id="b1-happy-b", checklist_results=[
            {"item_id": "z", "status": "defect-present", "severity": "minor"},
        ])
        rows = build_pair_rows([run_a, run_b], [sc_a, sc_b])
        by_run_id = {r["run_id"]: r for r in rows}
        self.assertEqual(by_run_id["b1-happy-a"]["defects_caught_count"], 1)
        self.assertEqual(by_run_id["b1-happy-b"]["defects_escaped_count"], 1)
        self.assertIsNone(by_run_id["b1-happy-b"]["defects_caught_count"])

    def test_rows_never_carry_a_cross_arm_summed_field(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-a-3", attempts=[{"kind": "dispatch"}])
        run_b = _run_record(task_id="B1", arm="B", run_id="b1-b-3", attempts=[{"kind": "turn"}])
        rows = build_pair_rows([run_a, run_b], [])
        for row in rows:
            self.assertNotIn("combined_turns", row)
            self.assertNotIn("total_across_arms", row)


# ---------------------------------------------------------------------------
# render_table -- plain text + JSON, script-computable, no invented aggregate
# ---------------------------------------------------------------------------

class TestRenderTable(unittest.TestCase):
    def setUp(self):
        run_a = _run_record(task_id="B1", arm="A", run_id="b1-a-1", attempts=[
            {"kind": "dispatch", "tokens": 500},
        ])
        run_b = _run_record(task_id="B1", arm="B", run_id="b1-b-1", attempts=[
            {"kind": "turn"},
        ])
        self.rows = build_pair_rows([run_a, run_b], [])

    def test_text_table_contains_every_row(self):
        text = render_table(self.rows, fmt="text")
        self.assertIn("b1-a-1", text)
        self.assertIn("b1-b-1", text)

    def test_text_table_has_no_aggregate_or_total_line(self):
        text = render_table(self.rows, fmt="text")
        self.assertNotIn("TOTAL", text.upper().replace("ROTATIONAL", ""))

    def test_json_table_round_trips_and_matches_rows(self):
        text = render_table(self.rows, fmt="json")
        parsed = json.loads(text)
        self.assertEqual(len(parsed), 2)
        run_ids = {r["run_id"] for r in parsed}
        self.assertEqual(run_ids, {"b1-a-1", "b1-b-1"})

    def test_unknown_format_raises(self):
        with self.assertRaises(MetricsInputError):
            render_table(self.rows, fmt="csv")


# ---------------------------------------------------------------------------
# load_json_records / main CLI
# ---------------------------------------------------------------------------

class TestLoadJsonRecords(unittest.TestCase):
    def test_loads_list_of_dicts(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "runs.json"
            p.write_text(json.dumps([_run_record()]), encoding="utf-8")
            records = load_json_records(str(p))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["task_id"], "B1")

    def test_missing_file_raises_metrics_input_error(self):
        with self.assertRaises(MetricsInputError):
            load_json_records("does/not/exist.json")

    def test_non_list_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "bad.json"
            p.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
            with self.assertRaises(MetricsInputError):
                load_json_records(str(p))


class TestMainCli(unittest.TestCase):
    def test_main_prints_text_table_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            runs_path = pathlib.Path(d) / "runs.json"
            runs_path.write_text(json.dumps([_run_record(attempts=[{"kind": "dispatch"}])]),
                                  encoding="utf-8")
            rc = main(["--run-records", str(runs_path)])
            self.assertEqual(rc, 0)

    def test_main_json_flag_emits_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            runs_path = pathlib.Path(d) / "runs.json"
            runs_path.write_text(json.dumps([_run_record(attempts=[{"kind": "dispatch"}])]),
                                  encoding="utf-8")
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--run-records", str(runs_path), "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(len(parsed), 1)

    def test_main_missing_run_records_arg_returns_nonzero(self):
        rc = main([])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Attempt-kind vocab sanity (guards the module docstring contract)
# ---------------------------------------------------------------------------

class TestAttemptKindVocab(unittest.TestCase):
    def test_arm_kind_sets_are_disjoint(self):
        self.assertEqual(ARM_A_ATTEMPT_KINDS & ARM_B_ATTEMPT_KINDS, set())

    def test_proxy_weight_table_matches_audit_a3(self):
        # docs/audits/2026-07-18-protocol-overhead-audit.md, A.3 table
        self.assertEqual(PROXY_WEIGHTS[("haiku", "low")], 1)
        self.assertEqual(PROXY_WEIGHTS[("haiku", "medium")], 1.6)
        self.assertEqual(PROXY_WEIGHTS[("haiku", "high")], 2.5)
        self.assertEqual(PROXY_WEIGHTS[("sonnet", "low")], 5)
        self.assertEqual(PROXY_WEIGHTS[("sonnet", "medium")], 8)
        self.assertEqual(PROXY_WEIGHTS[("sonnet", "high")], 12.5)
        self.assertEqual(PROXY_WEIGHTS[("opus", "low")], 15)
        self.assertEqual(PROXY_WEIGHTS[("opus", "medium")], 24)
        self.assertEqual(PROXY_WEIGHTS[("opus", "high")], 37.5)


if __name__ == "__main__":
    unittest.main()
