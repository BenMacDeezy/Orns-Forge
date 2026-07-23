"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0109`: TestFgC0109PickerProviderPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
    _CONVENTIONS_PATH_RESOLVED,
    _WORD_TO_INT,
    validate_task,
    shard_task,
    conventions_corpus,
)


class TestFgC0109PickerProviderPins(unittest.TestCase):
    """Doc-pins for fg-c0109 (spec-e8a3, "Overlay-profile model"): registering
    the Providers domain's stock/presets/custom into spec-4d2a's ONE shared
    picker in `commands/settings.md` step 2(a), plus the normative
    no-second-picker and pilot-gate-is-not-a-selection-block statements.

    Every substring below is unique to this task's added text -- checked
    against the pre-existing Autonomy listing bullets, the fg-b0106 pointer-
    format pins, and the fg-c0107/fg-c0108 VIBE/FORM pilot-gate phrasing
    (`TestFgC0107VibeModePins` / `TestFgC0108FormModePins` above) so this
    class never accidentally passes on text a sibling task already owns."""

    SETTINGS_PATH = REPO_ROOT / "commands" / "settings.md"

    @staticmethod
    def _norm(path):
        text = _cached_read_text(path)
        return " ".join(text.split())

    def _settings(self):
        return self._norm(self.SETTINGS_PATH)

    def test_providers_domain_heading_registers_via_extensibility_guarantee(self):
        content = self._settings()
        self.assertIn(
            "**`## Providers`** (`fg-c0109`, populated by `fg-c0101`/spec-e8a3 "
            "— registered into this SAME listing per the extensibility "
            "guarantee below, not a second listing mechanism):",
            content,
        )

    def test_providers_stock_summary(self):
        content = self._settings()
        self.assertIn(
            "*Stock* — `claude-only` everywhere (`operator-profiles.md`, "
            "\"Stock Providers content\"), shown with a one-line summary "
            "(\"all roles Claude-native — no-op overlay, matching "
            "`providers` Feature's OFF default\").",
            content,
        )

    def test_providers_three_named_presets_with_descriptions(self):
        content = self._settings()
        self.assertIn(
            "- `claude-only` — every role stays Claude-native; the "
            "explicit, selectable form of the stock default.",
            content,
        )
        self.assertIn(
            "- `cross-check-second-judging` — Codex as an advisory second "
            "opinion on plan-refuter and full-tier co-verifier, composing "
            "with Claude's own `forge-verifier`; spec-review and all "
            "worker dispatch stay Claude-only.",
            content,
        )
        self.assertIn(
            "- `budget-tiers` — routes the spec-review advisory pass to "
            "Codex's mechanical tier for a cost-conscious cross-check; "
            "plan-refuter, co-verifier, and all worker dispatch stay "
            "Claude-only.",
            content,
        )

    def test_providers_custom_listing_cites_key_vocabulary(self):
        content = self._settings()
        self.assertIn(
            "parses `kind: custom` and which carries a `## Providers` "
            "section, shown with its `base` and a one-line delta summary "
            "(which Providers keys it overrides vs. inherits, per "
            "`operator-profiles.md`'s \"`## Providers` key vocabulary\").",
            content,
        )

    def test_extensibility_guarantee_updated_to_fulfilled(self):
        """The pre-existing fg-b0106 guarantee paragraph now points at this
        task as its own fulfillment, phrased distinctly from the original
        forward-looking "fg-c0109 depends on this guarantee holding" line
        it replaces."""
        content = self._settings()
        self.assertIn(
            "`fg-c0109` (immediately above) is that registration.",
            content,
        )

    def test_no_second_picker_pin(self):
        content = self._settings()
        self.assertIn(
            "**Pin — no second picker for Providers.** The `## Providers` "
            "domain group above renders inside this SAME "
            "`AskUserQuestion` listing per the extensibility guarantee — "
            "`fg-c0109` builds no Providers-specific picker variant, "
            "screen, or command.",
            content,
        )

    def test_providers_switch_reuses_one_pointer_line_format(self):
        content = self._settings()
        self.assertIn(
            "Selecting a Providers stock, preset, or custom entry is the "
            "identical one-pointer-line switch (c) below already defines: "
            "`active: stock:<name>` for stock or preset, `active: "
            "custom:<name>` for custom — Providers profiles are addressed "
            "by the pointer exactly like Autonomy profiles, never a "
            "second pointer scheme.",
            content,
        )

    def test_pilot_gate_never_blocks_picker_selection_pin(self):
        content = self._settings()
        self.assertIn(
            "**Pin — the picker never blocks a pilot-gated selection.** "
            "A preset naming only `codex` in `enabled-providers` (all "
            "three minimum presets above) is fully selectable in the "
            "listing.",
            content,
        )
        self.assertIn(
            "naming a pilot-gated provider there is \"accepted and "
            "stored, never itself the thing that clears the gate\"; "
            "enforcement is the pilot gate (`fg-c0104`/`fg-c0105` "
            "evidence review) and the trust/toggle floors at dispatch "
            "time (`operator-profiles.md`, \"Interplay with the "
            "`providers` Feature toggle and the floor\"), never a "
            "picker-level selection block.",
            content,
        )
        self.assertIn(
            "step 2(d-form) below, is separate and unaffected — this "
            "pin covers the top-level listing in step 2(a) only.",
            content,
        )
