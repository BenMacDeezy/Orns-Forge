"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0101`: TestFgC0101ProvidersDomainPins.
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


class TestFgC0101ProvidersDomainPins(unittest.TestCase):
    """Doc-pins for fg-c0101 (Providers domain schema + content in
    skills/kernel/references/operator-profiles.md). Every substring below is
    unique to this task's new "## Providers domain: schema (fg-c0101)"
    section -- never a phrase that pre-exists in the Autonomy domain section
    above it (the fg-b0104 lesson: assert against text this task actually
    added, not text a sibling domain section would also satisfy)."""

    def _operator_profiles(self):
        return _cached_read_text((
            REPO_ROOT / "skills" / "kernel" / "references" / "operator-profiles.md"
        ))

    def test_providers_domain_heading_present(self):
        content = self._operator_profiles()
        self.assertIn("## Providers domain: schema (fg-c0101)", content)

    def test_role_keys_and_phase_2_gate_present(self):
        content = self._operator_profiles()
        for key in (
            "role-plan-refuter",
            "role-spec-review",
            "role-co-verifier",
            "role-worker",
        ):
            self.assertIn(key, content)
        # R1 live 2026-07-22 (bm-atomic-doc-fix-canonical-route): role-worker
        # is no longer Phase-2-gated — a resolved provider is the automatic-
        # default BUILDER route.
        self.assertIn("**`role-worker` is R1-live", content)

    def test_claude_only_stock_defaults_present(self):
        content = self._operator_profiles()
        self.assertIn("### Stock Providers content", content)
        self.assertIn(
            "Stock = `claude-only` everywhere, matching the `providers` "
            "Feature's OFF\ndefault",
            content,
        )
        self.assertIn("- enabled-providers: none", content)

    def test_pilot_gate_sentence_names_fg_c0104_and_fg_c0105(self):
        content = self._operator_profiles()
        self.assertIn("`fg-c0104`", content)
        self.assertIn("`fg-c0105`", content)
        self.assertIn("neither provider is", content)
        self.assertIn(
            "dispatchable until a human has reviewed", content
        )
        self.assertIn("that evidence and cleared the", content)

    def test_never_hardcode_model_ids_phrase_present(self):
        content = self._operator_profiles()
        self.assertIn(
            "**values are implementation-pinned\n  strings", content
        )
        self.assertIn(
            "this file never hardcodes a model ID", content
        )

    def test_three_preset_names_present(self):
        content = self._operator_profiles()
        self.assertIn("**`claude-only`**", content)
        self.assertIn("**`cross-check-second-judging`**", content)
        self.assertIn("**`budget-tiers`**", content)

    def test_budget_tiers_interpretive_flag_present_for_fg_c0106(self):
        """Pins the honesty flag telling fg-c0106 to confirm the
        role-spec-review tier reading before wiring dispatch -- must not
        silently vanish in a future edit before fg-c0106 reads it."""
        content = self._operator_profiles()
        self.assertIn(
            "Interpretation flag (unverified, stated here rather than "
            "silently assumed):",
            content,
        )
        self.assertIn(
            "A future task\nimplementing `fg-c0106` should confirm this "
            "reading against spec-e8a3\nbefore wiring `role-spec-review`'s "
            "tier resolution",
            content,
        )
