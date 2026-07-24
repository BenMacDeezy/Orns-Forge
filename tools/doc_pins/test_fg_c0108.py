"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-c0108`: TestFgC0108FormModePins.
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


class TestFgC0108FormModePins(unittest.TestCase):
    """Doc-pins for fg-c0108 (spec-e8a3, "Dual authoring UX"): the FORM-mode
    `## Providers` field wizard added to `commands/settings.md` step 2(d),
    plus the one-sentence mode-choice hook shared with fg-c0107's VIBE mode.

    Every substring below is unique to this task's added text -- checked
    against the pre-existing Autonomy "Delta capture" bullet and the
    existing fg-b0106 create-custom pins (`TestFgB0106ProfilePickerPins`
    above) so this class never accidentally passes on text a sibling task
    already owns."""

    SETTINGS_PATH = REPO_ROOT / "commands" / "settings.md"

    @staticmethod
    def _norm(path):
        text = _cached_read_text(path)
        return " ".join(text.split())

    def _settings(self):
        return self._norm(self.SETTINGS_PATH)

    def test_mode_choice_hook_present(self):
        """The one-sentence mode-choice hook collides with fg-c0107's own
        edit to the same paragraph by design -- pin it narrowly so a merge
        keeps this exact sentence intact."""
        content = self._settings()
        self.assertIn(
            "the human first picks an authoring mode via one structured "
            "question — VIBE (örn-guided interview) or FORM (structured "
            "`AskUserQuestion` wizard, 2(d-form) below) — either mode may "
            "edit a profile the other created, both writing the identical "
            "schema-versioned format.",
            content,
        )

    def test_form_mode_heading_and_boundary_present(self):
        content = self._settings()
        self.assertIn(
            "**2(d-form). FORM mode — `## Providers` field wizard "
            "(fg-c0108, spec-e8a3", content,
        )
        self.assertIn(
            "a profile authored in VIBE mode is fully editable in FORM "
            "mode and vice versa, per spec-e8a3's mode-symmetric edit AC",
            content,
        )

    def test_one_card_per_field_phrase(self):
        content = self._settings()
        self.assertIn(
            "ONE question card per `## Providers` field the human is "
            "customizing", content,
        )

    def test_cite_never_invent_phrase(self):
        content = self._settings()
        self.assertIn(
            "a FORM-mode card never offers an option the cited schema "
            "does not define", content,
        )

    def test_disabled_option_pilot_gate_and_trust_phrases(self):
        content = self._settings()
        self.assertIn(
            "each still appears on its card as a disabled option, with "
            "the refusal reason stated inline in that option's own "
            "description", content,
        )
        self.assertIn("A disabled option is visible with its reason, never a hidden option.", content)
        self.assertIn("pilot-gated behind `fg-c0104`", content)
        self.assertIn(
            "not yet trust-confirmed for this repo on this machine",
            content,
        )

    def test_deterministic_phrase(self):
        content = self._settings()
        self.assertIn(
            "FORM mode asks no open-ended question and makes no judgment "
            "call a VIBE-mode interview would", content,
        )

    def test_identical_schema_normative_sentence(self):
        """Pins the normative downstream-indistinguishable sentence
        required by the fg-c0108 spawn contract, phrased distinctly from
        fg-b0106's own validator-before-finish pin above."""
        content = self._settings()
        self.assertIn(
            "normatively, the two authoring modes are indistinguishable "
            "downstream by any consumer (picker, kernel role resolution, "
            "`tools/validate_config.py`), per spec-e8a3's \"Dual authoring "
            "UX\" AC.",
            content,
        )

    def test_form_mode_validates_before_finishing_phrase(self):
        content = self._settings()
        self.assertIn(
            "FORM mode runs `tools/validate_config.py`'s "
            "`validate_profile()` against the resulting file before "
            "reporting success or switching the active pointer",
            content,
        )
        self.assertIn(
            "FORM mode adds no second validation path alongside "
            "`validate_profile()`.",
            content,
        )
