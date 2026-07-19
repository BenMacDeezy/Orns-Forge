# tools/test_validate_config.py
import contextlib, io, os, pathlib, tempfile, unittest
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


if __name__ == "__main__":
    unittest.main()
