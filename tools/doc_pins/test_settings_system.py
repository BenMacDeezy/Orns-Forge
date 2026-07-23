"""Doc-pin regression tests for the batched sibling pair `provider-toggles`
+ `settings-system-depth` (2026-07-21): per-provider forge.md toggles
layered under the global `providers` Feature, and the settings-schema
registry + /forge:settings overhaul that consumes it. Follows the sharded,
one-module-per-task-id-prefix convention `tools/doc_pins/test_fg_*.py`
already establishes so concurrent tasks appending pins land in separate
files instead of conflicting at a shared tail."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
)


class TestProviderTogglesPins(unittest.TestCase):
    """Pins for provider-toggles: the four-layer gate chain wired into
    provider-judges.md §1a, the missing-toggle-means-off exception, the
    TOFU-never-cleared rule, and the pilot-gate-never-overridden rule --
    both in the NORMATIVE reference and in the dated conventions section
    that cites it."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )
    CONFIG_FEATURES_PATH = (
        REPO_ROOT / "docs" / "conventions" / "config-and-features.md"
    )
    TEMPLATE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references"
        / "forge-config-template.md"
    )
    VALIDATE_CONFIG_PATH = REPO_ROOT / "tools" / "validate_config.py"

    def _provider_judges(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def _config_features(self):
        return _cached_read_text(self.CONFIG_FEATURES_PATH)

    def _template(self):
        return _cached_read_text(self.TEMPLATE_PATH)

    def _validate_config(self):
        return _cached_read_text(self.VALIDATE_CONFIG_PATH)

    # -- four-layer gate sentence --

    def test_provider_judges_four_layer_heading(self):
        content = self._provider_judges()
        self.assertIn(
            "### 1a. Per-provider toggle — additive fourth gate layer "
            "(provider-toggles, 2026-07-21)",
            content,
        )

    def test_provider_judges_four_layers_enumerated(self):
        content = self._provider_judges()
        self.assertIn(
            "A codex judge fills the panel slot ONLY when ALL FOUR\n"
            "hold, checked in this order:",
            content,
        )
        self.assertIn(
            "1. the `providers` Feature is `on` for this repo;", content
        )
        self.assertIn(
            "3. codex's per-provider trust marker\n"
            "   (`.forge/.trust-providers/codex.local`) is present;",
            content,
        )
        self.assertIn(
            "4. the dispatch cap (`max-provider-dispatches-per-session`, "
            "section 7.6\n   below) has headroom.",
            content,
        )

    def test_provider_judges_blocked_dispatch_labeled_line(self):
        content = self._provider_judges()
        self.assertIn(
            "provider-gate-blocked: codex layer=<layer> — <reason>",
            content,
        )
        self.assertIn(
            "where `<layer>` is one of `global-feature` (layer 1), "
            "`provider-toggle`\n(layer 2), `trust-marker` (layer 3), or "
            "`dispatch-cap` (layer 4).",
            content,
        )

    def test_config_features_four_layers_cited(self):
        content = self._config_features()
        self.assertIn(
            "**Four independent gate layers.** A provider dispatches only "
            "when ALL of\nthe following hold",
            content,
        )
        self.assertIn(
            "labeled line (`provider-judges.md` §1a's `provider-gate-"
            "blocked: <provider>\nlayer=<layer> — <reason>` format)",
            content,
        )

    # -- missing-toggle-means-off exception --

    def test_provider_judges_missing_toggle_means_off(self):
        content = self._provider_judges()
        self.assertIn(
            "a toggle absent from\n"
            "   forge.md, or the whole `## Providers` section absent, "
            "resolves to OFF —\n"
            "   the one place in forge.md config where a missing key "
            "does NOT mean\n   default-on",
            content,
        )

    def test_config_features_missing_toggle_exception_heading(self):
        content = self._config_features()
        self.assertIn(
            "**Missing-toggle exception — the one surface where missing "
            "means OFF.**",
            content,
        )
        self.assertIn(
            "The\nper-provider `## Providers` toggle inverts that norm "
            "on purpose: a\nprovider id absent from the section, or the "
            "whole `## Providers` section\nabsent from forge.md, "
            "resolves to OFF, not to some documented \"default\"\nvalue.",
            content,
        )

    def test_template_providers_section_default_off(self):
        content = self._template()
        self.assertIn(
            "MISSING TOGGLE = OFF — the one place in\n     forge.md "
            "where a missing key does NOT mean its listed default here;",
            content,
        )
        self.assertIn("- codex: off", content)
        self.assertIn("- grok: off", content)
        self.assertIn("- antigravity: off", content)

    def test_validate_config_missing_key_means_off_docstring(self):
        content = self._validate_config()
        self.assertIn(
            "missing section, or a provider id the section omits, means "
            "that\n    provider is OFF",
            content,
        )

    # -- TOFU never cleared --

    def test_provider_judges_toggling_off_never_clears_trust(self):
        content = self._provider_judges()
        self.assertIn(
            "**Toggling off never clears trust.** Setting codex's forge.md "
            "toggle to\n`off` (layer 2) leaves "
            "`.forge/.trust-providers/codex.local` (layer 3)\nuntouched",
            content,
        )

    def test_config_features_toggling_off_never_clears_tofu(self):
        content = self._config_features()
        self.assertIn(
            "**Toggling off never clears TOFU.** Setting a provider's "
            "forge.md toggle to\n`off` leaves that provider's "
            "`.forge/.trust-providers/<provider-id>.local`\nmarker "
            "untouched",
            content,
        )

    # -- pilot gate never overridden by a toggle --

    def test_provider_judges_pilot_gate_never_overridden(self):
        content = self._provider_judges()
        self.assertIn(
            "**Pilot gates are never overridden by a toggle.** `grok` and "
            "`antigravity`\nstay undispatchable pending human pilot-"
            "evidence review",
            content,
        )

    def test_config_features_pilot_gate_never_overridden(self):
        content = self._config_features()
        self.assertIn(
            "**Pilot gates are never overridden by a toggle.** `grok` and "
            "`antigravity`\nstay undispatchable pending human pilot-"
            "evidence review regardless of what\ntheir forge.md toggle "
            "says",
            content,
        )

    # -- pilot gate note folds into the graceful-degrade note shape --

    def test_provider_judges_toggle_layer_folds_into_degrade_note(self):
        content = self._provider_judges()
        self.assertIn(
            "**Provider-toggle layer folds into the same note "
            "(provider-toggles,\n2026-07-21).**",
            content,
        )


class TestSettingsSystemDepthPins(unittest.TestCase):
    """Pins for settings-system-depth: the ONE-canonical-place schema-
    registry rule, the floor-refusal rule (four named floors), and the
    Providers view's three-fields-together rendering in commands/
    settings.md."""

    SETTINGS_SCHEMA_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "settings-schema.md"
    )
    CONFIG_FEATURES_PATH = (
        REPO_ROOT / "docs" / "conventions" / "config-and-features.md"
    )
    SETTINGS_CMD_PATH = REPO_ROOT / "commands" / "settings.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    def _schema(self):
        return _cached_read_text(self.SETTINGS_SCHEMA_PATH)

    def _config_features(self):
        return _cached_read_text(self.CONFIG_FEATURES_PATH)

    def _settings_cmd(self):
        return _cached_read_text(self.SETTINGS_CMD_PATH)

    # -- schema registry: one canonical place --

    def test_schema_file_exists_normative_header(self):
        content = self._schema()
        self.assertIn(
            "NORMATIVE. The ONE canonical place a `.forge/forge.md` "
            "setting is defined",
            content,
        )

    def test_config_features_one_canonical_place_heading(self):
        content = self._config_features()
        self.assertIn(
            "## Settings schema registry — one canonical place — "
            "2026-07-21 (settings-system-depth)",
            content,
        )
        self.assertIn(
            "`skills/kernel/references/settings-\nschema.md` (NORMATIVE) "
            "is now the ONE canonical place a new forge.md\nsetting is "
            "added",
            content,
        )

    def test_settings_cmd_cites_canonical_schema_source(self):
        content = self._settings_cmd()
        self.assertIn(
            "**Canonical schema source.** Every setting this command "
            "renders, validates,\nor writes is drawn from "
            "`skills/kernel/references/settings-schema.md`",
            content,
        )

    def test_conventions_toc_and_manifest_entries(self):
        content = _cached_read_text(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Settings schema registry — one canonical place — "
            "2026-07-21 (settings-system-depth)",
            content,
        )
        self.assertIn(
            "- `Settings schema registry — one canonical place — "
            "2026-07-21 (settings-system-depth)` -> "
            "`docs/conventions/config-and-features.md`",
            content,
        )
        self.assertIn(
            "- Per-provider dispatch toggles (`forge.md` Providers "
            "section) — 2026-07-21 (provider-toggles)",
            content,
        )
        self.assertIn(
            "- `Per-provider dispatch toggles (`forge.md` Providers "
            "section) — 2026-07-21 (provider-toggles)` -> "
            "`docs/conventions/config-and-features.md`",
            content,
        )

    # -- floor-refusal rule --

    def test_schema_four_floor_names(self):
        content = self._schema()
        self.assertIn("- `trust-confirmation` —", content)
        self.assertIn("- `human-set-cap` —", content)
        self.assertIn("- `spec-approval-gate` —", content)
        self.assertIn("- `providers-default-off` —", content)

    def test_config_features_floor_protected_settings_paragraph(self):
        content = self._config_features()
        self.assertIn(
            "**Floor-protected settings.** A subset of forge.md's surface "
            "is a FLOOR —\nnever relaxed by a settings edit regardless of "
            "how the edit is phrased:",
            content,
        )

    def test_settings_cmd_floor_check_step(self):
        content = self._settings_cmd()
        self.assertIn("**Floor check.**", content)
        self.assertIn(
            "refuse the write and name the floor plainly", content
        )
        self.assertIn(
            "No settings edit ever overrides a floor, regardless of how\n"
            "   the request is phrased.",
            content,
        )

    def test_settings_cmd_validate_before_write(self):
        content = self._settings_cmd()
        self.assertIn(
            "4. **Validate, then apply the minimal diff.** BEFORE writing "
            "anything, check",
            content,
        )
        self.assertIn(
            "write ONLY the changed lines, preserve everything else "
            "byte-for-byte",
            content,
        )

    # -- providers view: toggle + trust-marker + pilot-gate together --

    def test_settings_cmd_providers_view_three_fields(self):
        content = self._settings_cmd()
        self.assertIn(
            "each showing THREE fields together,\n     never split "
            "across separate views: its forge.md `## Providers` toggle",
            content,
        )
        self.assertIn("whether its TOFU trust marker", content)
        self.assertIn("and its\n     pilot-gate status", content)

    def test_settings_cmd_providers_missing_toggle_off_exception_stated(self):
        content = self._settings_cmd()
        self.assertIn(
            "unlike every\n     other section in this view, a missing "
            "toggle here resolves to `off`,",
            content,
        )

    def test_settings_cmd_enable_provider_writes_toggle_with_marker(self):
        content = self._settings_cmd()
        self.assertIn(
            "write\n     the machine-local marker file (format in that "
            "section) AND write that\n     provider's forge.md "
            "`## Providers` toggle to `on`",
            content,
        )


class TestValidateConfigProvidersSection(unittest.TestCase):
    """Behavioral pin (not just doc text): tools/validate_config.py must
    actually accept a well-formed `## Providers` toggle section, reject a
    bad on/off value, and warn (not error) on an unrecognized provider id
    -- exercised directly against the validator module rather than via a
    subprocess, matching this suite's own doc-pin-plus-behavior style for
    validator changes."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import validate_config  # noqa: E402
        self.validate_config = validate_config

    def test_known_provider_toggle_accepted(self):
        import tempfile
        content = (
            "# Forge config\n\n## Providers\n- codex: on\n- grok: off\n\n"
            "## Gates\n- build: none\n- test: none\n- lint: none\n"
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            path = f.name
        try:
            errors = self.validate_config.validate(path)
            self.assertEqual(errors, [])
        finally:
            pathlib.Path(path).unlink()

    def test_bad_provider_value_rejected(self):
        import tempfile
        content = (
            "# Forge config\n\n## Providers\n- codex: maybe\n\n"
            "## Gates\n- build: none\n- test: none\n- lint: none\n"
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            path = f.name
        try:
            errors = self.validate_config.validate(path)
            self.assertTrue(
                any("bad Providers value" in e for e in errors), errors
            )
        finally:
            pathlib.Path(path).unlink()

    def test_unknown_provider_id_warns_not_errors(self):
        import tempfile
        content = (
            "# Forge config\n\n## Providers\n- claude-remote: on\n\n"
            "## Gates\n- build: none\n- test: none\n- lint: none\n"
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False
        ) as f:
            f.write(content)
            path = f.name
        try:
            warnings = []
            errors = self.validate_config.validate(path, warnings=warnings)
            self.assertEqual(errors, [])
            self.assertTrue(
                any("unrecognized Providers toggle" in w for w in warnings),
                warnings,
            )
        finally:
            pathlib.Path(path).unlink()



class TestProviderDispatchCheckpointsPins(unittest.TestCase):
    """2026-07-22 owner-ratified: checkpoint cadence replaces the hard
    per-session provider dispatch cap in this repo (cap key keeps
    hard-cap semantics when numeric; none disables it)."""

    def _section(self):
        return _cached_read_text(
            REPO_ROOT / "docs" / "conventions" / "config-and-features.md")

    def test_amendment_heading_and_index(self):
        self.assertIn(
            "## Provider dispatch checkpoints — 2026-07-22 "
            "(owner-ratified)", self._section())
        index = _cached_read_text(REPO_ROOT / "docs" / "conventions.md")
        self.assertIn(
            "- `Provider dispatch checkpoints — 2026-07-22 "
            "(owner-ratified)` -> `docs/conventions/config-and-features.md`",
            index)

    def test_numeric_cap_semantics_preserved_none_disables(self):
        content = self._section()
        self.assertIn("keeps its original hard-cap semantics unchanged",
                      content)
        self.assertIn("`none` (the new recorded\n  value in this repo) "
                      "disables the hard ceiling", content)

    def test_checkpoint_is_visibility_not_stop_and_floors_untouched(self):
        content = self._section()
        self.assertIn("a\n  visibility-and-consent cadence, not a stop",
                      content)
        self.assertIn("never retried silently", content)
        self.assertIn("Floors unchanged", content)

    def test_checkpoint_model_is_global_shipped_default(self):
        content = self._section()
        self.assertIn("**Global, provider-agnostic**", content)
        self.assertIn("every\n  Forge repo and every provider", content)
        self.assertIn("per-provider breakdown", content)
        template = _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "forge-config-template.md")
        self.assertIn("- max-provider-dispatches-per-session: none",
                      template)
        self.assertIn("- provider-dispatch-checkpoint-every: 10", template)

    def test_schema_registers_checkpoint_key(self):
        schema = _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "settings-schema.md")
        self.assertIn("`provider-dispatch-checkpoint-every` | int | 10",
                      schema)


if __name__ == "__main__":
    unittest.main()
