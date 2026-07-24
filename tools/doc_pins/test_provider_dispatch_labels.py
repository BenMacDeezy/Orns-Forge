"""Doc-pin regression tests for provider-dispatch-labels (2026-07-22):
provider dispatches get a persona + role + provider/model-slug + task-name
display label, telemetry and Routing records name the exact slug used
(never invented), blocked/degraded provider dispatches use the same
labeled voice, and codex model/reasoning-effort choosability follows a
documented resolution order with recorded per-provider defaults. Split
into its own module per the sharded doc-pins convention (fg-a11040).
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


class TestProviderDispatchLabelsPins(unittest.TestCase):
    """Pins for provider-dispatch-labels: label format, exact-slug-never-
    invented telemetry rule, blocked-same-voice rule, model/effort
    resolution order, recorded codex defaults, and the surfacing
    additions in provider-judges.md / settings-schema.md /
    commands/settings.md / docs/conventions.md."""

    TELEMETRY_LABELS_PATH = (
        REPO_ROOT / "docs" / "conventions" / "telemetry-and-labels.md"
    )
    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )
    SETTINGS_SCHEMA_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "settings-schema.md"
    )
    SETTINGS_COMMAND_PATH = REPO_ROOT / "commands" / "settings.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    def _telemetry_labels_content(self):
        return _cached_read_text(self.TELEMETRY_LABELS_PATH)

    def _provider_judges_content(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def _settings_schema_content(self):
        return _cached_read_text(self.SETTINGS_SCHEMA_PATH)

    def _settings_command_content(self):
        return _cached_read_text(self.SETTINGS_COMMAND_PATH)

    def _conventions_content(self):
        return _read_path(self.CONVENTIONS_PATH)

    # -- docs/conventions/telemetry-and-labels.md: new section heading --

    def test_telemetry_labels_has_new_section_heading(self):
        content = self._telemetry_labels_content()
        self.assertIn("## Provider dispatch labels — 2026-07-22", content)

    # -- Label format (AC1) -----------------------------------------------

    def test_label_format_definition(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "**Label format — provider dispatches.** A provider "
            "dispatch's display\nlabel is `<Persona> — <role> — "
            "<provider>/<model-slug> — <task name>`,",
            content,
        )

    def test_label_format_worked_example(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "e.g. `Vera — co-verifier — codex/gpt-5.6-sol — "
            "auth-session hardening`.",
            content,
        )

    def test_label_distinct_from_in_harness_format(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "This is a DISTINCT shape from the in-harness "
            "`<Persona> (<role>)`",
            content,
        )

    def test_label_fields_persona_role_slug_taskname(self):
        content = self._telemetry_labels_content()
        self.assertIn("- **Persona** —", content)
        self.assertIn("- **Role** —", content)
        self.assertIn("- **`<provider>/<model-slug>`** —", content)
        self.assertIn("- **Task name** —", content)

    def test_swarm_disambiguation_still_applies(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "`<Persona> #N — <role> — <provider>/<model-slug> — "
            "<task name>`.",
            content,
        )

    # -- Telemetry never-invent-a-number extends to model identity (AC2) --

    def test_telemetry_never_invent_model_identity_heading(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "**Telemetry never-invent-a-number extends to model "
            "identity.**",
            content,
        )

    def test_telemetry_never_invent_never_external_model_phrase(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "THE SYSTEM SHALL name the provider AND the exact model slug "
            "used — the\nliteral string passed to `-m` for that "
            "dispatch, read back from the\ndispatch invocation itself, "
            "never \"an external model,\" never a slug\nrecalled from "
            "memory or from a DIFFERENT dispatch's line.",
            content,
        )

    def test_routing_record_line_shape_for_provider_dispatch(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "e.g. `attempt 1: codex — codex/gpt-5.6-sol/\njudgment — "
            "role-co-verifier panel slot`.",
            content,
        )

    # -- Blocked/degraded same labeled voice (AC3) -------------------------

    def test_blocked_degraded_same_labeled_voice_heading(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "**Blocked/degraded dispatches use the same labeled voice.**",
            content,
        )

    def test_blocked_degraded_cites_provider_gate_blocked_line(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "`provider-judges.md` §1a's `provider-gate-blocked:\n"
            "codex layer=<layer> — <reason>` line (cited here, not "
            "restated) IS",
            content,
        )

    def test_blocked_degraded_never_silent_skip(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "so absence is as\nvisible as presence — never a bare "
            "silent skip.",
            content,
        )

    # -- Resolution order (AC4) --------------------------------------------

    def test_resolution_order_heading(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "**Resolution order — model + reasoning effort "
            "choosability\n(provider-dispatch-labels, 2026-07-22).**",
            content,
        )

    def test_resolution_order_never_unstated_hardcode(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "resolved in this order — never an unstated hardcode:",
            content,
        )

    def test_resolution_order_step1_task_routing_override(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "1. **Task routing override** — forge.md's "
            "`## Routing overrides`",
            content,
        )

    def test_resolution_order_step2_class_based_vocabulary(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "2. **Class-based routing vocabulary** — the dispatching "
            "task's",
            content,
        )
        self.assertIn(
            "MECHANICAL resolves effort to the recorded\n"
            "   per-provider default effort (step 3, below); JUDGMENT, "
            "or any\n   adversarial-judge role, resolves effort to "
            "`high` — or to a\n   §3 role pin's pinned effort where "
            "that is HIGHER",
            content,
        )
        # 2026-07-22 cross-model verify synthesis: floor-preserving
        # effort + pin-staleness trigger (codex found the schema gap,
        # Claude found the floor semantics — both fixes pinned).
        self.assertIn("`high` never lowers\n   an `xhigh` pin", content)
        self.assertIn("**Pin-staleness trigger**", content)
        self.assertIn(
            "model availability is CLI-version-\n   dependent", content)

    def test_routing_override_schema_accepts_provider_qualified_form(self):
        # Vera (codex/gpt-5.6-sol) FAIL finding, 2026-07-22: without
        # this form, resolution-order step 1 could not express a
        # provider model at all.
        content = _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "settings-schema.md")
        self.assertIn("`<provider>/<slug>/<effort>`", content)
        self.assertIn("`codex/gpt-5.6-sol/high`", content)
        self.assertIn(
            "slug verbatim as passed to `-m`", content)

    def test_resolution_order_step3_recorded_defaults(self):
        content = self._telemetry_labels_content()
        self.assertIn(
            "3. **Recorded per-provider defaults** — the floor every "
            "dispatch with",
            content,
        )
        self.assertIn(
            "`codex-default-model: gpt-5.6-sol`, `codex-default-effort: "
            "medium`\n   (owner-set 2026-07-22, floor-flag: no — the "
            "orchestrator MAY\n   override per dispatch via step 1 or 2 "
            "above)",
            content,
        )

    # -- provider-judges.md §2 additive label line --------------------------

    def test_provider_judges_label_slug_recording_heading(self):
        content = self._provider_judges_content()
        self.assertIn(
            "**Label + slug recording at dispatch time "
            "(provider-dispatch-labels,\n2026-07-22).**",
            content,
        )

    def test_provider_judges_label_slug_recording_amends_without_reorder(self):
        content = self._provider_judges_content()
        self.assertIn(
            "Amends this section without reordering or restating any\n"
            "flag above.",
            content,
        )

    def test_provider_judges_label_slug_recording_requirement(self):
        content = self._provider_judges_content()
        self.assertIn(
            "never a label or record\nwritten before `-m`'s value is "
            "known, and never a slug string other\nthan the literal "
            "one passed to this invocation.",
            content,
        )

    def test_provider_judges_existing_read_only_contract_pin_unmoved(self):
        """Existing fg-c0106 pin's leading substring must still match —
        confirms this task's insertion landed AFTER that paragraph, not
        inside it."""
        content = self._provider_judges_content()
        self.assertIn(
            "**Read-only contract.** A Phase 1 codex judge dispatch produces a\n"
            "verdict/findings payload ONLY — it never writes to the worktree, "
            "never\nruns `git commit`/`git add`, and never invokes any codex "
            "subcommand beyond\n`exec` with the flags above.",
            content,
        )

    # -- settings-schema.md registry additions ------------------------------

    def test_settings_schema_codex_default_model_row(self):
        content = self._settings_schema_content()
        # Amended 2026-07-22: "any model slug string" tightened to the
        # owner-allowed set (sol/terra/luna/5.5) verified against the
        # live catalog.
        self.assertIn(
            "| `codex-default-model` | string | `gpt-5.6-sol` | "
            "owner-allowed set",
            content,
        )

    def test_settings_schema_codex_default_effort_row(self):
        content = self._settings_schema_content()
        self.assertIn(
            "| `codex-default-effort` | string | `medium` | low, "
            "medium, high, xhigh |",
            content,
        )

    def test_settings_schema_no_floor_note(self):
        content = self._settings_schema_content()
        self.assertIn(
            "**Provider default keys carry no floor (floor-flag: "
            "no).**",
            content,
        )

    # -- commands/settings.md additive line ---------------------------------

    def test_settings_command_surfaces_default_keys(self):
        content = self._settings_command_content()
        self.assertIn(
            "Also rendered alongside each provider's\n"
            "     row: its recorded default model/effort fallback "
            "(`codex-default-model`\n     / `codex-default-effort`, "
            "`settings-schema.md`, \"Providers\") used only",
            content,
        )

    # -- docs/conventions.md TOC + shards manifest ---------------------------

    def test_conventions_toc_entry(self):
        content = self._conventions_content()
        self.assertIn("- Provider dispatch labels — 2026-07-22", content)

    def test_conventions_shards_manifest_row(self):
        content = self._conventions_content()
        self.assertIn(
            "`Provider dispatch labels — 2026-07-22` -> "
            "`docs/conventions/telemetry-and-labels.md`",
            content,
        )



class TestOwnerAllowedModelSetPins(unittest.TestCase):
    """2026-07-22 owner directive: terra/luna/5.5 allowed alongside sol;
    tier map re-pinned from the LIVE catalog per the staleness trigger."""

    def _judges(self):
        return _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "provider-judges.md")

    def test_tier_repin_section_governs(self):
        content = self._judges()
        self.assertIn(
            "### 9. Tier re-pin + owner-allowed model set — 2026-07-22",
            content)
        self.assertIn("THIS section governs", content)
        self.assertIn(
            "- codex-tier-judgment: gpt-5.6-sol "
            "(model_reasoning_effort=high)", content)
        self.assertIn(
            "- codex-tier-balanced: gpt-5.6-terra "
            "(model_reasoning_effort=medium)", content)
        self.assertIn(
            "- codex-tier-mechanical: gpt-5.6-luna "
            "(model_reasoning_effort=medium)", content)

    def test_staleness_trigger_cited_not_calendar(self):
        content = self._judges()
        self.assertIn("The pin-staleness trigger", content)
        self.assertIn("never on a\ncalendar", content)

    def test_schema_owner_allowed_set(self):
        schema = _cached_read_text(
            REPO_ROOT / "skills" / "kernel" / "references"
            / "settings-schema.md")
        self.assertIn(
            "owner-allowed set (2026-07-22, verified against the live "
            "models_cache catalog): `gpt-5.6-sol`, `gpt-5.6-terra`, "
            "`gpt-5.6-luna`, `gpt-5.5`", schema)



class TestSensitiveDomainCarveOutPins(unittest.TestCase):
    """2026-07-22 owner-directed: sensitive domains (forge-security
    trigger list + provider gate machinery) keep an in-harness Claude
    BUILDER by default; providers still judge; only a human-written
    routing override crosses the carve-out."""

    def _routing(self):
        return _cached_read_text(
            REPO_ROOT / "docs" / "conventions"
            / "dispatch-and-routing.md")

    def test_carve_out_section_and_index(self):
        self.assertIn(
            "## Sensitive-domain build carve-out — 2026-07-22 "
            "(owner-directed)", self._routing())
        index = _cached_read_text(REPO_ROOT / "docs" / "conventions.md")
        self.assertIn(
            "- `Sensitive-domain build carve-out — 2026-07-22 "
            "(owner-directed)` -> "
            "`docs/conventions/dispatch-and-routing.md`", index)

    def test_builder_role_only_providers_still_judge(self):
        content = self._routing()
        self.assertIn("SHALL default the BUILDER to an in-harness "
                      "Claude agent", content)
        self.assertIn("binds the builder\n  role only", content)
        self.assertIn("authorship of it is not delegated by\n  default",
                      content)

    def test_only_human_override_crosses_never_orchestrator(self):
        content = self._routing()
        self.assertIn("only a human-written override line crosses it",
                      content)
        self.assertIn("the\n  orchestrator never crosses it on its own "
                      "judgment", content)

    def test_carve_out_visible_in_label_rationale(self):
        content = self._routing()
        self.assertIn("sensitive-domain carve-out: auth", content)


if __name__ == "__main__":
    unittest.main()
