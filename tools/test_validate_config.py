# tools/test_validate_config.py
import contextlib, io, os, sys, warnings as _warnings_mod, pathlib, tempfile, unittest
from validate_config import validate, main

VALID = """# Forge config

## Routing overrides
<!-- optional lines: "<pattern or area>: <model>/<effort> — <reason>" -->
(none)

## Budgets
- session-token-cap: none
- max-tasks-per-session: none

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

## Features
<!-- Behavior toggles. `on`/`off`. Defaults below; docs/conventions.md
     ("Features (forge.md)") is the reference. -->
- natural-language-invocation: on   # Forge skills fire from plain conversation; off = command-only
- continuous-loop: on               # completing a task auto-pulls the next wave
- auto-queue-capture: on            # task-shaped ideas are offered for capture
- express-lane: on                  # standard-tier ideas skip the spec pipeline
- workflow-executor: on             # waves + full-tier reviews run as Workflow scripts

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
"""

# The live-file shape: no Features section, free-form Gates commands.
MINIMAL_VALID = """# Forge config

## Routing overrides
<!-- optional lines: "<pattern or area>: <model>/<effort> — <reason>" -->
(none)

## Budgets
- session-token-cap: none
- max-tasks-per-session: none

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

## Gates
- build: none (Claude plugin repo — no build step)
- test: python -m pytest tools/ -q
- lint: none (no linter configured)
"""


class TestValidateConfig(unittest.TestCase):
    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    # -- Gates --

    def test_valid_file_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_minimal_live_shape_passes(self):
        self.assertEqual(validate(self._write(MINIMAL_VALID)), [])

    def test_missing_gates_section_fails(self):
        broken = VALID.replace(
            "## Gates\n- build: (auto-detect)\n- test: (auto-detect)\n"
            "- lint: (auto-detect)\n", "")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("Gates" in e for e in errs))

    def test_gates_missing_build_key_fails(self):
        broken = VALID.replace("- build: (auto-detect)\n", "")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("build" in e for e in errs))

    def test_gates_empty_value_fails(self):
        broken = VALID.replace("- lint: (auto-detect)", "- lint:")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("lint" in e for e in errs))

    def test_malformed_gates_line_fails(self):
        broken = VALID.replace("- build: (auto-detect)", "- build (auto-detect)")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("malformed" in e for e in errs))

    def test_gates_none_with_explanation_passes(self):
        self.assertEqual(validate(self._write(MINIMAL_VALID)), [])

    # -- Queue --

    def test_queue_section_absent_is_fine(self):
        no_queue = VALID.replace(
            "## Queue\n- claim-staleness-hours: 0.5\n- max-parallel-tasks: 3\n\n", "")
        self.assertNotEqual(no_queue, VALID)
        self.assertEqual(validate(self._write(no_queue)), [])

    def test_claim_staleness_non_numeric_fails(self):
        broken = VALID.replace("claim-staleness-hours: 0.5", "claim-staleness-hours: soon")
        errs = validate(self._write(broken))
        self.assertTrue(any("claim-staleness-hours" in e for e in errs))

    def test_claim_staleness_negative_fails(self):
        broken = VALID.replace("claim-staleness-hours: 0.5", "claim-staleness-hours: -1")
        errs = validate(self._write(broken))
        self.assertTrue(any("claim-staleness-hours" in e for e in errs))

    def test_claim_staleness_zero_fails(self):
        broken = VALID.replace("claim-staleness-hours: 0.5", "claim-staleness-hours: 0")
        errs = validate(self._write(broken))
        self.assertTrue(any("claim-staleness-hours" in e for e in errs))

    def test_claim_staleness_integer_passes(self):
        ok = VALID.replace("claim-staleness-hours: 0.5", "claim-staleness-hours: 2")
        self.assertEqual(validate(self._write(ok)), [])

    def test_max_parallel_tasks_non_int_fails(self):
        broken = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: 3.5")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-parallel-tasks" in e for e in errs))

    def test_max_parallel_tasks_zero_fails(self):
        broken = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: 0")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-parallel-tasks" in e for e in errs))

    def test_max_parallel_tasks_negative_fails(self):
        broken = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: -3")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-parallel-tasks" in e for e in errs))

    # -- Budgets --

    def test_budgets_section_absent_is_fine(self):
        no_budgets = VALID.replace(
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n\n", "")
        self.assertNotEqual(no_budgets, VALID)
        self.assertEqual(validate(self._write(no_budgets)), [])

    def test_budgets_none_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_budgets_positive_int_passes(self):
        ok = VALID.replace("max-tasks-per-session: none", "max-tasks-per-session: 10")
        self.assertEqual(validate(self._write(ok)), [])

    def test_budgets_zero_fails(self):
        broken = VALID.replace("max-tasks-per-session: none", "max-tasks-per-session: 0")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-tasks-per-session" in e for e in errs))

    def test_budgets_bad_value_fails(self):
        broken = VALID.replace("session-token-cap: none", "session-token-cap: unlimited")
        errs = validate(self._write(broken))
        self.assertTrue(any("session-token-cap" in e for e in errs))

    # -- Features --

    def test_features_section_absent_is_fine(self):
        self.assertEqual(validate(self._write(MINIMAL_VALID)), [])

    def test_features_known_toggles_pass(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_features_bad_value_fails(self):
        broken = VALID.replace(
            "- continuous-loop: on               # completing a task auto-pulls the next wave",
            "- continuous-loop: enabled          # completing a task auto-pulls the next wave")
        errs = validate(self._write(broken))
        self.assertTrue(any("continuous-loop" in e for e in errs))

    def test_features_unknown_toggle_warns_not_errors(self):
        tagged = VALID.replace(
            "## Gates", "- some-new-toggle: on\n\n## Gates")
        self.assertNotEqual(tagged, VALID)
        warnings = []
        errs = validate(self._write(tagged), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(any("some-new-toggle" in w for w in warnings))

    def test_features_unknown_toggle_no_warnings_arg_still_passes(self):
        tagged = VALID.replace("## Gates", "- some-new-toggle: on\n\n## Gates")
        self.assertEqual(validate(self._write(tagged)), [])

    def test_features_double_quoted_value_passes(self):
        # A hand-editor quoting a Features scalar by analogy with task/spec
        # frontmatter (which dequotes upstream) must not hit a false-positive
        # "bad Features value" error.
        quoted = VALID.replace(
            "- workflow-executor: on             # waves + full-tier reviews run as Workflow scripts",
            '- workflow-executor: "on"           # waves + full-tier reviews run as Workflow scripts')
        self.assertNotEqual(quoted, VALID)
        self.assertEqual(validate(self._write(quoted)), [])

    def test_features_single_quoted_value_passes(self):
        quoted = VALID.replace(
            "- workflow-executor: on             # waves + full-tier reviews run as Workflow scripts",
            "- workflow-executor: 'on'           # waves + full-tier reviews run as Workflow scripts")
        self.assertNotEqual(quoted, VALID)
        self.assertEqual(validate(self._write(quoted)), [])

    def test_features_quoted_off_passes(self):
        quoted = VALID.replace(
            "- continuous-loop: on               # completing a task auto-pulls the next wave",
            '- continuous-loop: "off"            # completing a task auto-pulls the next wave')
        self.assertNotEqual(quoted, VALID)
        self.assertEqual(validate(self._write(quoted)), [])

    def test_features_quoted_garbage_still_fails(self):
        broken = VALID.replace(
            "- continuous-loop: on               # completing a task auto-pulls the next wave",
            '- continuous-loop: "enabled"        # completing a task auto-pulls the next wave')
        errs = validate(self._write(broken))
        self.assertTrue(any("continuous-loop" in e for e in errs))

    # -- misc --

    def test_nonexistent_path_reports_clean_error(self):
        ghost = str(pathlib.Path(tempfile.gettempdir()) / "forge-does-not-exist-0001.md")
        errs = validate(ghost)
        self.assertEqual(len(errs), 1)
        self.assertIn("forge-does-not-exist-0001.md", errs[0])

    def test_bom_prefixed_file_parses(self):
        errs = validate(self._write("﻿" + VALID))
        self.assertEqual(errs, [])

    def test_gates_shown_in_fence_only_reported_missing(self):
        fenced = VALID.replace(
            "## Gates\n- build: (auto-detect)\n- test: (auto-detect)\n"
            "- lint: (auto-detect)\n",
            "```\n## Gates\n- build: (auto-detect)\n- test: (auto-detect)\n"
            "- lint: (auto-detect)\n```\n")
        self.assertNotEqual(fenced, VALID)
        errs = validate(self._write(fenced))
        self.assertTrue(any("Gates" in e for e in errs))

    # -- CLI defaults --

    def _run_in(self, tmp, argv=None):
        cwd = os.getcwd()
        os.chdir(tmp)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = main(argv or [])
        finally:
            os.chdir(cwd)
        return code, buf.getvalue()

    def test_main_default_path_used_when_present(self):
        tmp = tempfile.mkdtemp()
        forge_dir = pathlib.Path(tmp, ".forge")
        forge_dir.mkdir()
        (forge_dir / "forge.md").write_text(VALID, encoding="utf-8")
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertIn("1 file(s) checked, 0 error(s)", out)

    def test_main_no_files_when_absent(self):
        tmp = tempfile.mkdtemp()
        code, out = self._run_in(tmp)
        self.assertEqual(code, 0)
        self.assertIn("0 file(s) checked, 0 error(s)", out)

    # -- BUG 1: UnicodeDecodeError caught cleanly --

    def test_utf16_encoded_file_reports_clean_error_not_crash(self):
        f = tempfile.NamedTemporaryFile("wb", suffix=".md", delete=False)
        f.write(VALID.encode("utf-16"))
        f.close()
        errs = validate(f.name)
        self.assertEqual(len(errs), 1)
        self.assertIn("cannot read file", errs[0])

    # -- BUG 6: fenced example content within a real ## Gates section must
    # not satisfy the build/test/lint key check --

    def test_gates_example_fence_within_real_section_not_counted(self):
        # The real "## Gates" header is present and unfenced, but its only
        # build/test/lint bullets are inside a fenced documentation example,
        # not real (unfenced) Gates configuration.
        fenced = VALID.replace(
            "## Gates\n- build: (auto-detect)\n- test: (auto-detect)\n"
            "- lint: (auto-detect)\n",
            "## Gates\nExample:\n```\n- build: (auto-detect)\n"
            "- test: (auto-detect)\n- lint: (auto-detect)\n```\n")
        self.assertNotEqual(fenced, VALID)
        errs = validate(self._write(fenced))
        self.assertTrue(any("Gates" in e for e in errs), errs)

    # -- BUG 17: duplicate keys within a bullet section must be flagged --

    def test_duplicate_gates_key_fails(self):
        dup = VALID.replace(
            "## Gates\n- build: (auto-detect)\n- test: (auto-detect)\n"
            "- lint: (auto-detect)\n",
            "## Gates\n- build: (auto-detect)\n- build: echo dup\n"
            "- test: (auto-detect)\n- lint: (auto-detect)\n")
        self.assertNotEqual(dup, VALID)
        errs = validate(self._write(dup))
        self.assertTrue(
            any("duplicate" in e and "build" in e for e in errs), errs)

    def test_duplicate_features_key_fails(self):
        dup = VALID.replace(
            "- continuous-loop: on               # completing a task auto-pulls the next wave\n",
            "- continuous-loop: on               # completing a task auto-pulls the next wave\n"
            "- continuous-loop: off               # duplicate\n")
        self.assertNotEqual(dup, VALID)
        errs = validate(self._write(dup))
        self.assertTrue(
            any("duplicate" in e and "continuous-loop" in e for e in errs),
            errs)

    def test_no_duplicate_no_false_positive(self):
        errs = validate(self._write(VALID))
        self.assertFalse(any("duplicate" in e for e in errs), errs)

    # -- BUG 18: re.split's maxsplit must be passed as a keyword --

    def test_features_inline_comment_split_raises_no_deprecation_warning(self):
        with _warnings_mod.catch_warnings(record=True) as caught:
            _warnings_mod.simplefilter("always")
            errs = validate(self._write(VALID))
        self.assertEqual(errs, [])
        self.assertFalse(
            any(issubclass(w.category, DeprecationWarning) for w in caught),
            [str(w.message) for w in caught])

    # -- fg-a11020: ## Routing overrides section must be structurally
    # validated, not silently skipped --

    def test_routing_overrides_none_placeholder_passes(self):
        self.assertEqual(validate(self._write(VALID)), [])

    def test_routing_overrides_well_formed_line_passes(self):
        ok = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py: sonnet/high — parser correctness needs care\n")
        self.assertNotEqual(ok, VALID)
        self.assertEqual(validate(self._write(ok)), [])

    def test_routing_overrides_malformed_shape_fails(self):
        broken = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py sonnet high because reasons\n")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("Routing overrides" in e for e in errs), errs)

    def test_routing_overrides_bad_model_fails(self):
        broken = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py: gpt5/high — wrong model family\n")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("Routing overrides" in e and "model" in e for e in errs), errs)

    def test_routing_overrides_bad_effort_fails(self):
        broken = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py: sonnet/extreme — wrong effort level\n")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("Routing overrides" in e and "effort" in e for e in errs), errs)

    def test_routing_overrides_missing_reason_fails(self):
        broken = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py: sonnet/high\n")
        self.assertNotEqual(broken, VALID)
        errs = validate(self._write(broken))
        self.assertTrue(any("Routing overrides" in e for e in errs), errs)

    def test_routing_overrides_absent_section_is_fine(self):
        no_routing = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n\n", "")
        self.assertNotEqual(no_routing, VALID)
        self.assertEqual(validate(self._write(no_routing)), [])

    def test_routing_overrides_hyphen_separator_also_passes(self):
        # Hand-edited files may use a plain hyphen instead of an em dash.
        ok = VALID.replace(
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "(none)\n",
            "## Routing overrides\n"
            "<!-- optional lines: \"<pattern or area>: <model>/<effort> — <reason>\" -->\n"
            "tools/telemetry.py: sonnet/high - parser correctness needs care\n")
        self.assertNotEqual(ok, VALID)
        self.assertEqual(validate(self._write(ok)), [])

    # -- BUG 19: em-dash output must not crash under a legacy codepage --

    def test_em_dash_message_does_not_crash_under_legacy_codepage(self):
        tmp = tempfile.mkdtemp()
        forge_dir = pathlib.Path(tmp, ".forge")
        forge_dir.mkdir()
        malformed = VALID.replace(
            "- build: (auto-detect)", "- build — (auto-detect)")
        self.assertNotEqual(malformed, VALID)
        (forge_dir / "forge.md").write_text(malformed, encoding="utf-8")

        cp437_stream = io.TextIOWrapper(io.BytesIO(), encoding="cp437",
                                        errors="strict")
        cwd = os.getcwd()
        os.chdir(tmp)
        real_stdout = sys.stdout
        sys.stdout = cp437_stream
        try:
            code = main([])  # must not raise UnicodeEncodeError
        finally:
            sys.stdout = real_stdout
            os.chdir(cwd)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
