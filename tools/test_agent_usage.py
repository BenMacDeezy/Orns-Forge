"""Tests for tools/agent_usage.py (fg-b0304, spec-b71f3a "Usage tracking"
AC10-AC12): the rolling-window usage-index aggregator over
`.forge/agents/usage/<name>.jsonl`.

Covers: append format (one JSON object per line), rolling-window counting
at both edges (inside/outside/exact-edge), multi-agent aggregation,
malformed-line tolerance (skip, never crash), missing/empty usage dir,
the no-telemetry-import guarantee, and fixed `--now` determinism.

Every jsonl fixture is written to its own tmp dir per test (same pattern
tools/test_telemetry.py and tools/test_status.py use for isolation).
"""
import ast
import datetime as dt
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import agent_usage
from agent_usage import count_dispatches, load_usage, main

NOW = dt.datetime(2026, 7, 19, 12, 0, 0, tzinfo=dt.timezone.utc)
WINDOW_DAYS = 14
WINDOW_START = NOW - dt.timedelta(days=WINDOW_DAYS)  # 2026-07-05T12:00:00Z


def _write_jsonl(usage_dir, name, lines):
    """Write raw text lines (already-serialized or deliberately malformed
    strings) to usage_dir/<name>.jsonl, one per line."""
    path = pathlib.Path(usage_dir) / f"{name}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _record(ts, task="fg-b0304"):
    return json.dumps({"ts": ts, "task": task})


class AppendFormatTests(unittest.TestCase):
    """One JSON object per appended line -- the on-disk shape the kernel
    writes at every archive-tier dispatch."""

    def test_loads_multiple_appended_records_for_one_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "goblin-grunt", [
                _record("2026-07-10T00:00:00Z", task="fg-aaaa"),
                _record("2026-07-11T00:00:00Z", task="inline"),
                _record("2026-07-12T00:00:00Z", task="fg-bbbb"),
            ])
            usage = load_usage(tmp)
            self.assertIn("goblin-grunt", usage)
            self.assertEqual(len(usage["goblin-grunt"]), 3)
            # Sorted ascending regardless of on-disk order.
            self.assertEqual(usage["goblin-grunt"], sorted(usage["goblin-grunt"]))

    def test_agent_name_comes_from_filename_stem(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "page-librarian-helper", [
                _record("2026-07-10T00:00:00Z"),
            ])
            usage = load_usage(tmp)
            self.assertEqual(list(usage.keys()), ["page-librarian-helper"])

    def test_accepts_task_field_value_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "hex", [_record("2026-07-10T00:00:00Z", task="inline")])
            usage = load_usage(tmp)
            self.assertEqual(len(usage["hex"]), 1)


class WindowBoundaryTests(unittest.TestCase):
    """Rolling window [now - window_days, now], both ends inclusive."""

    def _counts_for(self, ts_list):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "grud", [_record(ts) for ts in ts_list])
            return count_dispatches(tmp, WINDOW_DAYS, now=NOW)

    def test_record_well_inside_window_counts(self):
        counts = self._counts_for(["2026-07-12T00:00:00Z"])
        self.assertEqual(counts.get("grud"), 1)

    def test_record_exactly_at_window_start_is_inclusive(self):
        ts = WINDOW_START.strftime("%Y-%m-%dT%H:%M:%SZ")
        counts = self._counts_for([ts])
        self.assertEqual(counts.get("grud"), 1)

    def test_record_one_second_before_window_start_is_excluded(self):
        ts = (WINDOW_START - dt.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        counts = self._counts_for([ts])
        self.assertNotIn("grud", counts)

    def test_record_exactly_at_now_is_inclusive(self):
        ts = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
        counts = self._counts_for([ts])
        self.assertEqual(counts.get("grud"), 1)

    def test_record_one_second_after_now_is_excluded(self):
        ts = (NOW + dt.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        counts = self._counts_for([ts])
        self.assertNotIn("grud", counts)

    def test_mixed_in_and_out_of_window_counts_only_inside(self):
        counts = self._counts_for([
            "2026-06-01T00:00:00Z",  # well before window
            "2026-07-06T00:00:00Z",  # inside
            "2026-07-15T00:00:00Z",  # inside
            "2026-08-01T00:00:00Z",  # after now
        ])
        self.assertEqual(counts.get("grud"), 2)

    def test_naive_ts_treated_as_utc(self):
        # No 'Z'/offset -- contract records are always UTC; a bare
        # ISO string still parses instead of being rejected.
        counts = self._counts_for(["2026-07-12T00:00:00"])
        self.assertEqual(counts.get("grud"), 1)

    def test_offset_ts_normalized_to_utc(self):
        # +02:00 offset -- 2026-07-12T02:00:00+02:00 == 00:00:00Z, inside.
        counts = self._counts_for(["2026-07-12T02:00:00+02:00"])
        self.assertEqual(counts.get("grud"), 1)


class MultiAgentAggregationTests(unittest.TestCase):
    def test_separate_files_produce_separate_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "goblin-grunt", [
                _record("2026-07-10T00:00:00Z"),
                _record("2026-07-11T00:00:00Z"),
                _record("2026-07-12T00:00:00Z"),
            ])
            _write_jsonl(tmp, "hex", [
                _record("2026-07-13T00:00:00Z"),
            ])
            counts = count_dispatches(tmp, WINDOW_DAYS, now=NOW)
            self.assertEqual(counts, {"goblin-grunt": 3, "hex": 1})

    def test_agent_with_zero_in_window_dispatches_is_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "stale-agent", [
                _record("2020-01-01T00:00:00Z"),  # long before the window
            ])
            counts = count_dispatches(tmp, WINDOW_DAYS, now=NOW)
            self.assertEqual(counts, {})


class MalformedLineToleranceTests(unittest.TestCase):
    def test_malformed_lines_skipped_valid_lines_still_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "flaky", [
                "not json at all",
                json.dumps({"task": "fg-cccc"}),          # missing ts
                json.dumps({"ts": "2026-07-12T00:00:00Z"}),  # missing task
                json.dumps({"ts": "2026-07-12T00:00:00Z", "task": ""}),  # empty task
                json.dumps({"ts": "not-a-timestamp", "task": "fg-dddd"}),
                json.dumps(["ts", "task"]),                # not an object
                _record("2026-07-12T00:00:00Z", task="fg-eeee"),  # valid
            ])
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                usage = load_usage(tmp)
            self.assertEqual(len(usage.get("flaky", [])), 1)
            self.assertIn("skipping malformed line", stderr.getvalue())

    def test_malformed_lines_never_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "flaky2", ["{{{not json", "", "   "])
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                usage = load_usage(tmp)  # must not raise
            self.assertEqual(usage, {})

    def test_all_malformed_file_yields_no_agent_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "all-bad", ["nope", "{}"])
            with redirect_stderr(io.StringIO()):
                usage = load_usage(tmp)
            self.assertNotIn("all-bad", usage)


class MissingEmptyDirTests(unittest.TestCase):
    def test_missing_dir_returns_empty_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "does-not-exist"
            self.assertEqual(load_usage(missing), {})
            self.assertEqual(count_dispatches(missing, WINDOW_DAYS, now=NOW), {})

    def test_empty_dir_returns_empty_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_usage(tmp), {})
            self.assertEqual(count_dispatches(tmp, WINDOW_DAYS, now=NOW), {})

    def test_cli_missing_dir_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(pathlib.Path(tmp) / "does-not-exist")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main([
                    "--usage-dir", missing,
                    "--window-days", str(WINDOW_DAYS),
                    "--now", "2026-07-19T12:00:00Z",
                ])
            self.assertEqual(rc, 0)
            self.assertIn("no dispatches in window", out.getvalue())

    def test_cli_empty_dir_exits_zero_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main([
                    "--usage-dir", tmp,
                    "--window-days", str(WINDOW_DAYS),
                    "--now", "2026-07-19T12:00:00Z",
                    "--json",
                ])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), {})


class NoTelemetryImportTests(unittest.TestCase):
    """AC11-AC12: this tool must not import from, or modify, telemetry.py.
    Parses the module's own AST rather than grepping the source text, so
    a prose mention of "tools/telemetry.py" in a docstring/comment (used
    to explain WHY the separation exists) can never accidentally satisfy
    -- or defeat -- this check."""

    def test_module_source_has_no_telemetry_import(self):
        source_path = pathlib.Path(agent_usage.__file__)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.append(node.module)
                imported_names.extend(alias.name for alias in node.names)
        self.assertTrue(
            all("telemetry" not in name for name in imported_names),
            f"unexpected telemetry-related import: {imported_names}",
        )

    def test_runtime_module_has_no_telemetry_attribute(self):
        # Belt-and-suspenders: the loaded module object itself carries no
        # telemetry symbol, confirming the AST check reflects reality.
        self.assertFalse(hasattr(agent_usage, "telemetry"))


class NowDeterminismTests(unittest.TestCase):
    def test_fixed_now_gives_identical_output_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "grud", [
                _record("2026-07-10T00:00:00Z"),
                _record("2026-07-11T00:00:00Z"),
            ])
            outputs = []
            for _ in range(2):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = main([
                        "--usage-dir", tmp,
                        "--window-days", str(WINDOW_DAYS),
                        "--now", "2026-07-19T12:00:00Z",
                        "--json",
                    ])
                self.assertEqual(rc, 0)
                outputs.append(out.getvalue())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(json.loads(outputs[0]), {"grud": 2})

    def test_function_level_now_string_and_datetime_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_jsonl(tmp, "grud", [_record("2026-07-12T00:00:00Z")])
            by_string = count_dispatches(tmp, WINDOW_DAYS, now="2026-07-19T12:00:00Z")
            by_datetime = count_dispatches(tmp, WINDOW_DAYS, now=NOW)
            self.assertEqual(by_string, by_datetime)


class CliBasicsTests(unittest.TestCase):
    def test_negative_window_days_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with redirect_stderr(err):
                rc = main([
                    "--usage-dir", tmp,
                    "--window-days", "0",
                    "--now", "2026-07-19T12:00:00Z",
                ])
            self.assertEqual(rc, 1)

    def test_default_window_days_is_fourteen(self):
        self.assertEqual(agent_usage.DEFAULT_WINDOW_DAYS, 14)


if __name__ == "__main__":
    unittest.main()
