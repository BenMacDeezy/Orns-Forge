"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0106`: TestFgB0106ProfilePickerPins.
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


class TestFgB0106ProfilePickerPins(unittest.TestCase):
    """fg-b0106 (spec-4d2a): the /forge:settings profile picker -- step 2's
    side-by-side listing, one-pointer-line-only switch, copy-on-write
    create-custom flow, validator-before-finish gate, the fg-a10902/
    fg-c0109 extensibility guarantee, and the git-tracked-custom-profiles
    note.

    Kernel-inline bounce catch (fg-b0106): the original diff stated these
    as "Pin --" prose paragraphs only, with no executable regression test
    (contract item 5 requires pin TESTS, not just prose). Every string
    pinned below was checked for uniqueness within settings.md before being
    pinned -- a string that also pre-exists elsewhere in the file is not
    load-bearing (learned from fg-b0104's own verifier finding, see
    test_settings_renders_default_string above).

    Whitespace-normalized comparisons throughout, same pattern as
    TestFgB0104ProfileWiringPins._norm."""

    SETTINGS_PATH = REPO_ROOT / "commands" / "settings.md"

    @staticmethod
    def _norm(path):
        text = _cached_read_text(path)
        return " ".join(text.split())

    def _settings(self):
        return self._norm(self.SETTINGS_PATH)

    # (1) side-by-side listing phrase
    def test_side_by_side_listing_phrase(self):
        content = self._settings()
        self.assertIn(
            "the picker lists stock, Forge-shipped presets, and the "
            "human's own custom profiles together in ONE listing, "
            "grouped by kind, never as three separate screens or "
            "prompts.",
            content,
        )

    # (2) one-pointer-line-only switch phrase + lossless-switching-contract
    # citation
    def test_one_pointer_line_only_switch_phrase(self):
        content = self._settings()
        self.assertIn(
            "switching the active profile writes exactly the one "
            "`active:` pointer line and nothing else",
            content,
        )
        self.assertIn("Lossless switching contract", content)

    # (3) copy-on-write custom-creation phrase
    def test_copy_on_write_custom_creation_phrase(self):
        content = self._settings()
        self.assertIn(
            "customizing a stock or preset (or an existing custom "
            "profile) always creates a NEW named "
            "`.forge/profiles/<name>.md` file capturing only the deltas "
            "over its `base`; the source profile is never modified in "
            "place",
            content,
        )

    # (4) validator-before-finish phrase
    def test_validator_before_finish_phrase(self):
        content = self._settings()
        self.assertIn(
            "the create-custom flow always runs `validate_profile()` on "
            "the new `.forge/profiles/<name>.md` before finishing",
            content,
        )
        self.assertIn(
            "does not report success or switch the active pointer to "
            "the new profile until it passes",
            content,
        )

    # (5) extensibility guarantee phrase incl. fg-c0109 citation
    def test_extensibility_guarantee_phrase(self):
        content = self._settings()
        self.assertIn(
            "this listing, the switch in (c), and the create-custom "
            'flow in (d) are all written generically over "the active '
            'container\'s domain sections"',
            content,
        )
        self.assertIn(
            "`fg-c0109` (immediately above) is that registration.", content
        )

    # (6) git-tracked-custom-profiles / only-trust-markers-gitignored note
    def test_git_tracked_custom_profiles_note(self):
        content = self._settings()
        self.assertIn(
            "Custom profiles are git-tracked, not gitignored.", content
        )
        self.assertIn("Only the machine-local TRUST MARKERS", content)
        self.assertIn(
            "a custom profile file is not a trust marker and must "
            "never be confused with one",
            content,
        )
