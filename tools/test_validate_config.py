# tools/test_validate_config.py
import contextlib, io, os, sys, warnings as _warnings_mod, pathlib, tempfile, unittest
import validate_config
from validate_config import validate, validate_profile, main

# -- Operator-profile container fixtures (fg-b0103, spec-4d2a) --

VALID_STOCK_PROFILE = """# Profile: guided

## Meta
- schema-version: 1
- kind: stock
- name: guided
- base: (none)

## Autonomy
- pause-points: dispatch, integrate
- wave-size: full
"""

VALID_CUSTOM_PROFILE = """# Profile: my-custom

## Meta
- schema-version: 1
- kind: custom
- name: my-custom
- base: guided

## Autonomy
- wave-size: 1
"""

VALID_MINIMAL_PROFILE = """# Profile: stub

## Meta
- schema-version: 1
- kind: preset
- name: stub
- base: (none)
"""

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

    def test_max_parallel_tasks_auto_passes(self):
        ok = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: auto")
        self.assertEqual(validate(self._write(ok)), [])

    def test_max_parallel_tasks_none_passes(self):
        ok = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: none")
        self.assertEqual(validate(self._write(ok)), [])

    def test_max_parallel_tasks_other_word_still_fails(self):
        broken = VALID.replace("max-parallel-tasks: 3", "max-parallel-tasks: lots")
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

    # -- Budgets: max-provider-dispatches-per-session (fg-c0113, spec-e8a3) --

    def test_provider_dispatch_cap_default_value_passes(self):
        ok = VALID.replace(
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n",
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n"
            "- max-provider-dispatches-per-session: 10\n")
        self.assertNotEqual(ok, VALID)
        self.assertEqual(validate(self._write(ok)), [])

    def test_provider_dispatch_cap_none_passes(self):
        ok = VALID.replace(
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n",
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n"
            "- max-provider-dispatches-per-session: none\n")
        self.assertNotEqual(ok, VALID)
        self.assertEqual(validate(self._write(ok)), [])

    def test_provider_dispatch_cap_zero_fails(self):
        broken = VALID.replace(
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n",
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n"
            "- max-provider-dispatches-per-session: 0\n")
        errs = validate(self._write(broken))
        self.assertTrue(any("max-provider-dispatches-per-session" in e for e in errs))

    def test_provider_dispatch_cap_bad_value_fails(self):
        broken = VALID.replace(
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n",
            "## Budgets\n- session-token-cap: none\n- max-tasks-per-session: none\n"
            "- max-provider-dispatches-per-session: unlimited\n")
        errs = validate(self._write(broken))
        self.assertTrue(
            any("max-provider-dispatches-per-session" in e for e in errs))

    def test_provider_dispatch_cap_absent_is_fine(self):
        # forge.md written before this key existed -- no key present at all,
        # not even a "none" -- must not be treated as an error (same
        # optional-if-set discipline as the other two Budgets keys).
        self.assertEqual(validate(self._write(VALID)), [])

    def test_provider_dispatch_checkpoint_requires_positive_integer(self):
        bad = VALID.replace("- max-tasks-per-session: none",
                            "- max-tasks-per-session: none\n"
                            "- provider-dispatch-checkpoint-every: banana")
        errs = validate(self._write(bad))
        self.assertTrue(any("provider-dispatch-checkpoint-every" in e for e in errs), errs)

    def test_provider_dispatch_checkpoint_positive_integer_passes(self):
        ok = VALID.replace("- max-tasks-per-session: none",
                           "- max-tasks-per-session: none\n"
                           "- provider-dispatch-checkpoint-every: 10")
        self.assertEqual(validate(self._write(ok)), [])

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

    def test_providers_feature_toggle_is_known(self):
        # fg-c0103 ships the `providers` toggle in docs/conventions/
        # config-and-features.md; KNOWN_FEATURES must carry it (the gap
        # fg-c0101's worker found) so a shipped forge.md stops warning it as
        # unrecognized.
        self.assertIn("providers", validate_config.KNOWN_FEATURES)
        tagged = VALID.replace("## Gates", "- providers: off\n\n## Gates")
        self.assertNotEqual(tagged, VALID)
        warnings = []
        errs = validate(self._write(tagged), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertFalse(any("providers" in w for w in warnings), warnings)

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

    def test_provider_qualified_routing_override_passes(self):
        ok = VALID.replace("(none)\n\n## Budgets",
                           "tools/telemetry.py: codex/gpt-5.6-sol/high — provider route\n\n## Budgets")
        self.assertEqual(validate(self._write(ok)), [])

    def test_provider_qualified_routing_override_rejects_unknown_slug(self):
        bad = VALID.replace("(none)\n\n## Budgets",
                            "tools/telemetry.py: codex/not-a-model/high — provider route\n\n## Budgets")
        errs = validate(self._write(bad))
        self.assertTrue(any("slug" in e for e in errs), errs)

    # -- Providers typed schema (settings-schema.md Providers rows) --

    def test_codex_provider_defaults_pass_their_own_schema(self):
        ok = VALID.replace("## Gates", "## Providers\n- codex-default-model: gpt-5.6-sol\n"
                           "- codex-default-effort: xhigh\n\n## Gates")
        self.assertEqual(validate(self._write(ok)), [])

    def test_codex_provider_defaults_reject_malformed_values(self):
        bad = VALID.replace("## Gates", "## Providers\n- codex-default-model: banana\n"
                            "- codex-default-effort: extreme\n\n## Gates")
        errs = validate(self._write(bad))
        self.assertTrue(any("codex-default-model" in e for e in errs), errs)
        self.assertTrue(any("codex-default-effort" in e for e in errs), errs)

    def test_pilot_provider_on_warns_but_does_not_error(self):
        ok = VALID.replace("## Gates", "## Providers\n- grok: on\n\n## Gates")
        warnings = []
        self.assertEqual(validate(self._write(ok), warnings=warnings), [])
        self.assertTrue(any(".forge/.trust-providers/grok.pilot-cleared.local" in w
                            for w in warnings), warnings)

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


class TestValidateProfile(unittest.TestCase):
    """Operator-profile container validation (fg-b0103, spec-4d2a) --
    skills/kernel/references/operator-profiles.md's format."""

    def _write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                        encoding="utf-8")
        f.write(text); f.close()
        return f.name

    # -- Meta section --

    def test_valid_stock_profile_passes(self):
        self.assertEqual(validate_profile(self._write(VALID_STOCK_PROFILE)), [])

    def test_valid_custom_profile_passes(self):
        self.assertEqual(validate_profile(self._write(VALID_CUSTOM_PROFILE)), [])

    def test_minimal_profile_no_domain_sections_passes(self):
        # Meta-only is valid: a stock/preset skeleton may reserve no domain
        # content yet (this task ships the container, not autonomy/provider
        # content).
        self.assertEqual(validate_profile(self._write(VALID_MINIMAL_PROFILE)), [])

    def test_missing_meta_section_fails(self):
        broken = VALID_STOCK_PROFILE.replace(
            "## Meta\n- schema-version: 1\n- kind: stock\n- name: guided\n"
            "- base: (none)\n\n", "")
        self.assertNotEqual(broken, VALID_STOCK_PROFILE)
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("Meta" in e for e in errs), errs)

    def test_missing_schema_version_fails(self):
        broken = VALID_STOCK_PROFILE.replace("- schema-version: 1\n", "")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("schema-version" in e for e in errs), errs)

    def test_non_numeric_schema_version_fails(self):
        broken = VALID_STOCK_PROFILE.replace(
            "- schema-version: 1", "- schema-version: one")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("schema-version" in e for e in errs), errs)

    def test_zero_schema_version_fails(self):
        broken = VALID_STOCK_PROFILE.replace(
            "- schema-version: 1", "- schema-version: 0")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("schema-version" in e for e in errs), errs)

    def test_bad_kind_fails(self):
        broken = VALID_STOCK_PROFILE.replace("- kind: stock", "- kind: bespoke")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("kind" in e for e in errs), errs)

    def test_missing_kind_fails(self):
        broken = VALID_STOCK_PROFILE.replace("- kind: stock\n", "")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("kind" in e for e in errs), errs)

    def test_missing_name_fails(self):
        broken = VALID_STOCK_PROFILE.replace("- name: guided\n", "")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("name" in e for e in errs), errs)

    def test_empty_name_fails(self):
        broken = VALID_STOCK_PROFILE.replace("- name: guided", "- name:")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("name" in e for e in errs), errs)

    # -- custom kind requires a real base --

    def test_custom_missing_base_fails(self):
        broken = VALID_CUSTOM_PROFILE.replace("- base: guided\n", "")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("base" in e for e in errs), errs)

    def test_custom_none_base_fails(self):
        broken = VALID_CUSTOM_PROFILE.replace("- base: guided", "- base: (none)")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("base" in e for e in errs), errs)

    def test_stock_with_absent_base_line_passes(self):
        # base is meaningless for stock/preset -- omitting it entirely is fine.
        ok = VALID_STOCK_PROFILE.replace("- base: (none)\n", "")
        self.assertEqual(validate_profile(self._write(ok)), [])

    # -- domain sections: known-domain warn-not-fail --

    def test_providers_section_is_known_and_passes(self):
        with_providers = VALID_STOCK_PROFILE + "\n## Providers\n- role: none\n"
        self.assertEqual(validate_profile(self._write(with_providers)), [])

    def test_unknown_domain_section_warns_not_fails(self):
        with_unknown = VALID_STOCK_PROFILE + "\n## Experimental\n- foo: bar\n"
        warnings = []
        errs = validate_profile(self._write(with_unknown), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(any("Experimental" in w for w in warnings), warnings)

    def test_duplicate_domain_section_fails(self):
        dup = VALID_STOCK_PROFILE + "\n## Autonomy\n- wave-size: 1\n"
        errs = validate_profile(self._write(dup))
        self.assertTrue(any("duplicate" in e and "Autonomy" in e for e in errs), errs)

    def test_malformed_domain_line_fails(self):
        broken = VALID_STOCK_PROFILE.replace(
            "- wave-size: full", "- wave-size full")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("malformed" in e for e in errs), errs)

    def test_duplicate_key_within_domain_section_fails(self):
        broken = VALID_STOCK_PROFILE.replace(
            "- wave-size: full\n", "- wave-size: full\n- wave-size: 1\n")
        errs = validate_profile(self._write(broken))
        self.assertTrue(any("duplicate" in e and "wave-size" in e for e in errs), errs)

    # -- Providers domain: key-level validation (fg-c0110, spec-e8a3) --

    def _providers(self, body):
        return VALID_STOCK_PROFILE + "\n## Providers\n" + body

    def test_stock_providers_content_passes_clean(self):
        stock = self._providers(
            "- enabled-providers: none\n"
            "- role-plan-refuter: claude-only\n"
            "- role-spec-review: claude-only\n"
            "- role-co-verifier: claude-only\n"
            "- role-worker: claude-only\n")
        warnings = []
        errs = validate_profile(self._write(stock), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_cross_check_preset_content_passes_clean(self):
        preset = self._providers(
            "- enabled-providers: codex\n"
            "- role-plan-refuter: codex\n"
            "- role-spec-review: claude-only\n"
            "- role-co-verifier: codex\n"
            "- role-worker: claude-only\n"
            "- codex-tier-judgment: (implementation-pinned at fg-c0106)\n")
        warnings = []
        errs = validate_profile(self._write(preset), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_enabled_providers_bad_entry_fails(self):
        broken = self._providers("- enabled-providers: chatgpt\n")
        errs = validate_profile(self._write(broken))
        self.assertTrue(
            any("enabled-providers" in e and "chatgpt" in e for e in errs), errs)

    def test_role_key_bad_value_fails(self):
        broken = self._providers("- role-plan-refuter: gemini\n")
        errs = validate_profile(self._write(broken))
        self.assertTrue(
            any("role-plan-refuter" in e for e in errs), errs)

    def test_unknown_providers_key_warns_not_fails(self):
        forward_compat = self._providers("- future-provider-thing: yes\n")
        warnings = []
        errs = validate_profile(self._write(forward_compat), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertTrue(
            any("future-provider-thing" in w for w in warnings), warnings)

    def test_removed_capability_key_degrades_with_one_warning(self):
        # No Providers key has actually been removed yet -- exercise the
        # degrade mechanism itself by injecting a fixture entry into
        # REMOVED_PROVIDER_KEYS, matching spec-e8a3's exact contract: never
        # an error, exactly one stated warning line, key ignored (degrades
        # to stock default) rather than rejected.
        original = dict(validate_config.REMOVED_PROVIDER_KEYS)
        validate_config.REMOVED_PROVIDER_KEYS["retired-role-key"] = (
            "claude-only")
        try:
            profile = self._providers("- retired-role-key: codex\n")
            warnings = []
            errs = validate_profile(self._write(profile), warnings=warnings)
            self.assertEqual(errs, [])
            matches = [w for w in warnings if "retired-role-key" in w]
            self.assertEqual(len(matches), 1, warnings)
            self.assertIn("degrad", matches[0].lower())
        finally:
            validate_config.REMOVED_PROVIDER_KEYS.clear()
            validate_config.REMOVED_PROVIDER_KEYS.update(original)

    def test_enabled_providers_grok_hard_errors_naming_pilot_gate(self):
        broken = self._providers("- enabled-providers: grok\n")
        errs = validate_profile(self._write(broken))
        self.assertTrue(
            any("grok" in e and "fg-c0104" in e for e in errs), errs)

    def test_enabled_providers_antigravity_hard_errors_naming_pilot_gate(self):
        broken = self._providers("- enabled-providers: antigravity\n")
        errs = validate_profile(self._write(broken))
        self.assertTrue(
            any("antigravity" in e and "fg-c0105" in e for e in errs), errs)

    def test_enabled_providers_codex_alone_is_fine(self):
        ok = self._providers("- enabled-providers: codex\n")
        errs = validate_profile(self._write(ok))
        self.assertEqual(errs, [])

    def test_full_bypass_flag_string_hard_rejected(self):
        hostile = self._providers(
            "- codex-dispatch-args: "
            "--dangerously-bypass-approvals-and-sandbox\n")
        errs = validate_profile(self._write(hostile))
        self.assertTrue(
            any("full-bypass" in e for e in errs), errs)
        self.assertTrue(
            any("Provider dispatch security rules" in e for e in errs), errs)

    def test_auto_approve_unpaired_with_sandbox_hard_rejected(self):
        hostile = self._providers(
            "- codex-dispatch-args: --ask-for-approval never\n")
        errs = validate_profile(self._write(hostile))
        self.assertTrue(any("sandbox" in e for e in errs), errs)
        self.assertTrue(
            any("Provider dispatch security rules" in e for e in errs), errs)

    def test_auto_approve_paired_with_sandbox_passes(self):
        ok = self._providers(
            "- codex-dispatch-args: --sandbox workspace-write "
            "--ask-for-approval never\n")
        errs = validate_profile(self._write(ok))
        self.assertEqual(errs, [])

    def test_grok_always_approve_unpaired_hard_rejected(self):
        hostile = self._providers("- grok-dispatch-args: --always-approve\n")
        errs = validate_profile(self._write(hostile))
        self.assertTrue(any("sandbox" in e for e in errs), errs)

    def test_full_bypass_flag_uppercase_hard_rejected(self):
        # Case must not be an evasion route: a verifier reproduced
        # `--DANGEROUSLY-BYPASS-APPROVALS-AND-SANDBOX` passing validation.
        hostile = self._providers(
            "- codex-dispatch-args: "
            "--DANGEROUSLY-BYPASS-APPROVALS-AND-SANDBOX\n")
        errs = validate_profile(self._write(hostile))
        self.assertTrue(any("full-bypass" in e for e in errs), errs)

    def test_auto_approve_mixed_case_unpaired_hard_rejected(self):
        hostile = self._providers(
            "- grok-dispatch-args: --Always-Approve\n")
        errs = validate_profile(self._write(hostile))
        self.assertTrue(any("sandbox" in e for e in errs), errs)

    def test_uppercase_sandbox_pairs_with_lowercase_auto_approve_passes(self):
        # Case-insensitivity must cut both ways: an uppercase --SANDBOX
        # still counts as a valid pairing, never stricter on the escape
        # than on the trap.
        ok = self._providers(
            "- codex-dispatch-args: --SANDBOX workspace-write "
            "--ask-for-approval never\n")
        errs = validate_profile(self._write(ok))
        self.assertEqual(errs, [])

    # -- R1 automatic-default migration notice (bm-upgrade-migration-
    #    warning, docs/specs/2026-07-22-phase2-external-workers.md) --

    def test_role_worker_claude_only_no_migration_warning(self):
        ok = self._providers("- role-worker: claude-only\n")
        warnings = []
        errs = validate_profile(self._write(ok), warnings=warnings)
        self.assertEqual(errs, [])
        self.assertEqual(warnings, [])

    def test_role_worker_provider_warns_migration_notice(self):
        # A profile with a pre-existing role-worker:<provider> assignment
        # (no acknowledgment marker on this machine yet) must surface the
        # one-time R1 automatic-default notice.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                profile_path = self._write(self._providers("- role-worker: codex\n"))
                warnings = []
                errs = validate_profile(profile_path, warnings=warnings)
            finally:
                os.chdir(cwd)
        self.assertEqual(errs, [])
        matches = [w for w in warnings if "role-worker" in w and "codex" in w]
        self.assertEqual(len(matches), 1, warnings)
        self.assertIn("R1", matches[0])
        self.assertIn(".forge/.trust-providers/role-worker.codex.migration-ack.local",
                      matches[0])

    def test_role_worker_provider_migration_notice_suppressed_by_marker(self):
        # Once the one-time acknowledgment marker exists on this machine,
        # the notice must be suppressed -- never re-nagged.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                marker_dir = pathlib.Path(".forge", ".trust-providers")
                marker_dir.mkdir(parents=True)
                (marker_dir / "role-worker.codex.migration-ack.local").write_text(
                    "acked-by: test\n", encoding="utf-8")
                profile_path = self._write(self._providers("- role-worker: codex\n"))
                warnings = []
                errs = validate_profile(profile_path, warnings=warnings)
            finally:
                os.chdir(cwd)
        self.assertEqual(errs, [])
        self.assertFalse(
            any("role-worker" in w and "codex" in w for w in warnings), warnings)

    def test_role_worker_provider_marker_is_per_provider(self):
        # An acknowledgment marker for one provider must not suppress the
        # notice for a DIFFERENT provider value.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                marker_dir = pathlib.Path(".forge", ".trust-providers")
                marker_dir.mkdir(parents=True)
                (marker_dir / "role-worker.codex.migration-ack.local").write_text(
                    "acked-by: test\n", encoding="utf-8")
                profile_path = self._write(self._providers("- role-worker: grok\n"))
                warnings = []
                errs = validate_profile(profile_path, warnings=warnings)
            finally:
                os.chdir(cwd)
        self.assertEqual(errs, [])
        self.assertTrue(
            any("role-worker" in w and "grok" in w for w in warnings), warnings)

    def test_role_worker_migration_warning_skipped_when_warnings_none(self):
        # No warnings list -> no crash, no filesystem access surprise.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                profile_path = self._write(self._providers("- role-worker: codex\n"))
                errs = validate_profile(profile_path)
            finally:
                os.chdir(cwd)
        self.assertEqual(errs, [])

    # -- CLI routing: a .forge/profiles/<name>.md path routes to
    #    validate_profile() instead of the forge.md validator --

    def test_main_routes_profile_path_to_profile_validator(self):
        tmp = tempfile.mkdtemp()
        profiles_dir = pathlib.Path(tmp, ".forge", "profiles")
        profiles_dir.mkdir(parents=True)
        profile_path = profiles_dir / "my-custom.md"
        profile_path.write_text(VALID_CUSTOM_PROFILE, encoding="utf-8")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(profile_path)])
        self.assertEqual(code, 0, out.getvalue())

    def test_main_routes_broken_profile_path_to_profile_validator(self):
        tmp = tempfile.mkdtemp()
        profiles_dir = pathlib.Path(tmp, ".forge", "profiles")
        profiles_dir.mkdir(parents=True)
        profile_path = profiles_dir / "broken.md"
        broken = VALID_CUSTOM_PROFILE.replace("- base: guided\n", "")
        profile_path.write_text(broken, encoding="utf-8")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(profile_path)])
        self.assertEqual(code, 1)
        self.assertIn("base", out.getvalue())

    def test_main_non_profile_path_still_uses_forge_md_validator(self):
        # A file not under .forge/profiles/ -- even one that happens to have
        # a "## Meta" heading -- validates as forge.md and fails the ordinary
        # way (missing ## Gates), proving routing is path-based, not
        # content-sniffed.
        tmp_path = self._write(VALID_STOCK_PROFILE)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([tmp_path])
        self.assertEqual(code, 1)
        self.assertIn("Gates", out.getvalue())


class ResolveMaxParallelTasksTests(unittest.TestCase):
    """`auto` must derive one window everywhere; `none` must mean unbounded."""

    def test_auto_derives_cores_minus_two(self):
        self.assertEqual(
            validate_config.resolve_max_parallel_tasks("auto", cpu_count=8), 6)

    def test_auto_is_capped_at_the_ceiling(self):
        # a 32-core box must not spawn 30 concurrent worktree builds
        self.assertEqual(
            validate_config.resolve_max_parallel_tasks("auto", cpu_count=32),
            validate_config.AUTO_PARALLEL_CEILING)

    def test_auto_floors_at_one_on_tiny_machines(self):
        for cores in (1, 2, 3):
            self.assertEqual(
                validate_config.resolve_max_parallel_tasks(
                    "auto", cpu_count=cores),
                1,
                f"cores={cores} must still allow one worker")

    def test_absent_value_resolves_like_auto(self):
        self.assertEqual(
            validate_config.resolve_max_parallel_tasks(None, cpu_count=8), 6)

    def test_none_is_unbounded(self):
        self.assertIsNone(
            validate_config.resolve_max_parallel_tasks("none", cpu_count=8))

    def test_explicit_int_is_used_verbatim(self):
        self.assertEqual(
            validate_config.resolve_max_parallel_tasks("3", cpu_count=32), 3)


if __name__ == "__main__":
    unittest.main()
