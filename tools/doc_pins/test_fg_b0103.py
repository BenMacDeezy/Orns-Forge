"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0103`: TestFgB0103OperatorProfileContainerPins.
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


class TestFgB0103OperatorProfileContainerPins(unittest.TestCase):
    """fg-b0103 (spec-4d2a): the shared overlay-profile container format --
    skills/kernel/references/operator-profiles.md, the docs/conventions.md
    dated section pointing at it, and tools/validate_config.py's
    validate_profile() extension."""

    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"
    CONVENTIONS_HEADING = (
        "## Operator-profile container format — 2026-07-18 "
        "(fg-b0103, spec-4d2a)"
    )
    REFERENCE_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "operator-profiles.md"
    )
    VALIDATE_CONFIG_PATH = REPO_ROOT / "tools" / "validate_config.py"

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(self.CONVENTIONS_HEADING, c)

    def test_toc_lists_the_new_section(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(
            "- Operator-profile container format — 2026-07-18 "
            "(fg-b0103, spec-4d2a)",
            c,
        )

    def test_manifest_maps_section_to_config_and_features_shard(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn(
            "`Operator-profile container format — 2026-07-18 "
            "(fg-b0103, spec-4d2a)` -> `docs/conventions/config-and-features.md`",
            c,
        )

    def test_conventions_section_names_container_guarantees(self):
        c = self._norm(self.CONVENTIONS_PATH)
        self.assertIn("kind: stock | preset | custom", c)
        self.assertIn("## Providers", c)
        self.assertIn(".forge/profiles/<name>.md", c)
        self.assertIn("validate_profile()", c)

    def test_reference_file_exists(self):
        self.assertTrue(self.REFERENCE_PATH.is_file())

    def test_reference_file_states_container_is_domain_agnostic(self):
        content = _cached_read_text(self.REFERENCE_PATH)
        self.assertIn(
            "one profile file format, two optional top-level",
            content,
        )
        self.assertIn("## Autonomy", content)
        self.assertIn("## Providers", content)

    def test_reference_file_states_stock_preset_immutability(self):
        content = _cached_read_text(self.REFERENCE_PATH)
        self.assertIn("never modified in place", content)

    def test_reference_file_states_lossless_switching(self):
        content = _cached_read_text(self.REFERENCE_PATH)
        self.assertIn("Lossless switching contract", content)
        self.assertIn(
            "MUST NOT read, write, mutate, or delete any profile",
            content,
        )

    def test_reference_file_states_warn_not_fail_degrade(self):
        content = _cached_read_text(self.REFERENCE_PATH)
        self.assertIn("never a hard failure", content)

    def test_validate_config_has_validate_profile_function(self):
        content = _cached_read_text(self.VALIDATE_CONFIG_PATH)
        self.assertIn("def validate_profile(path, warnings=None):", content)
        self.assertIn("KNOWN_PROFILE_DOMAINS", content)
