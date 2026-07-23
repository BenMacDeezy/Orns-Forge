"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0107`: TestFgC0107VibeModePins.
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


class TestFgC0107VibeModePins(unittest.TestCase):
    """Doc-pins for fg-c0107 (VIBE mode: örn-guided conversational
    Providers/Autonomy profile authoring, added to commands/settings.md
    step 2 as the clearly-delimited "2(d-vibe)" subsection). Every
    substring below is unique to this task's addition -- never a phrase
    that pre-existed in step 2's FORM-mode text (fg-c0108's boundary),
    so a future edit that guts the vibe-mode content without touching
    FORM mode still fails these tests."""

    def _settings(self):
        return _cached_read_text((REPO_ROOT / "commands" / "settings.md"))

    def test_mode_choice_hook_present(self):
        content = self._settings()
        self.assertIn("**Choose authoring mode.**", content)
        self.assertIn("**FORM mode**", content)
        self.assertIn("**VIBE mode**", content)
        self.assertIn("2(d-vibe)", content)

    def test_vibe_mode_heading_present(self):
        content = self._settings()
        self.assertIn(
            "**2(d-vibe). VIBE mode — örn-guided conversational "
            "authoring.**",
            content,
        )

    def test_downstream_indistinguishable_normative_sentence_present(self):
        """Pins the exact normative claim required by spec-e8a3's Dual
        authoring UX AC: vibe mode's output is downstream-indistinguishable
        from form mode's."""
        content = self._settings()
        self.assertIn(
            "**Normative sentence (downstream-indistinguishable).** VIBE "
            "mode\n     writes the identical schema-versioned `## "
            "Providers` / `## Autonomy`\n     profile format FORM mode "
            "writes",
            content,
        )
        self.assertIn(
            "nothing in the\n     resulting file records which mode "
            "authored it.",
            content,
        )

    def test_closed_vocabulary_discipline_cites_both_domains(self):
        content = self._settings()
        self.assertIn("**Closed-vocabulary discipline (normative).**", content)
        self.assertIn("`operator-profiles.md`,\n       \"`## Autonomy` key vocabulary\"", content)
        self.assertIn("`operator-profiles.md`, \"`## Providers` key vocabulary\"", content)
        self.assertIn(
            "örn never invents a key or a\n     value outside them",
            content,
        )

    def test_pilot_gate_refusal_present(self):
        """Pins the pilot-gate refusal: grok/antigravity are explained,
        never written into enabled-providers or a role-* key, within the
        vibe-mode interview."""
        content = self._settings()
        self.assertIn("*Pilot-gated providers.*", content)
        self.assertIn("`grok` or `antigravity`", content)
        self.assertIn(
            "refuses to write that provider\n       into "
            "`enabled-providers` or any `role-*` key",
            content,
        )

    def test_missing_trust_confirmation_points_at_step_5(self):
        content = self._settings()
        self.assertIn("*Missing trust confirmation.*", content)
        self.assertIn(
            "örn points at step 5 (\"Per-provider trust "
            "confirm\") below rather",
            content,
        )

    def test_validate_profile_gate_shared_with_form_mode(self):
        content = self._settings()
        self.assertIn(
            "the interview hands off to\n     (d)'s own **Validate "
            "before finishing** and **Activate** bullets",
            content,
        )
        self.assertIn("the same `validate_profile()` gate", content)

    def test_mode_symmetric_editing_present(self):
        content = self._settings()
        self.assertIn("**Editing.** Choosing VIBE mode to customize", content)
        self.assertIn("mode-symmetric editing (spec-e8a3", content)
        self.assertIn(
            "a profile\n     authored in form mode is fully editable via "
            "vibe mode and vice\n     versa",
            content,
        )
