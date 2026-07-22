"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10203`: TestFgA10203CraftBleedPins.
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


class TestFgA10203CraftBleedPins(unittest.TestCase):
    """Doc-pins for fg-a10203 (craft-memory bleed check): the canonical
    dated conventions section (heading, patterns anchor, warning-channel
    anchor), the kernel LEARN sentence citing it by exact name, and the
    char-ceiling ancestry this task had to fit under (already covered by
    test_kernel_skill_within_char_ceiling, above).
    """

    SECTION_HEADING = "## Craft-memory bleed check — 2026-07"

    def test_conventions_has_craft_bleed_section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_craft_bleed_section_in_toc(self):
        content = conventions_corpus.corpus_text()
        self.assertIn("  - Craft-memory bleed check — 2026-07", content)

    def test_conventions_craft_bleed_has_patterns_anchor(self):
        """Pins the craft-store-scoping rule and the hand-edited-pattern-list
        anchor -- the actual mechanism, not just the heading -- so a future
        edit can't quietly turn this into a vague description."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn(
            "parent directory named `memory` whose OWN parent is not "
            "`.forge`",
            section,
        )
        self.assertIn("canonically a hand-edited list", section)
        self.assertIn("validate_memory.CRAFT_BLEED_HANDLES", section)

    def test_conventions_craft_bleed_has_warning_channel_anchor(self):
        """Pins the warning-not-error rationale (legit cross-references
        exist) and the never-appended-to-errors / exit-code-unaffected
        guarantee, mirroring validate_task.py's pattern by name."""
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("Legitimate cross-references exist", normalized)
        self.assertIn(
            "never appended to the returned error list", normalized
        )
        self.assertIn("exit code is unaffected by warnings", normalized)
        self.assertIn("validate_task.py", normalized)

    def test_conventions_craft_bleed_has_learn_gate(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        self.assertIn("Promotion to craft memory requires resolving every "
                      "bleed\nwarning FIRST", section)

    def test_kernel_learn_cites_craft_bleed_section_by_exact_name(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn(
            '`docs/conventions.md`, "Craft-memory bleed check — 2026-07"',
            content,
        )

    def test_kernel_learn_promotion_gate_sentence_present(self):
        """Pins the LEARN-gate sentence itself: promotion requires resolving
        bleed warnings first, fix-or-keep-local, recorded in the session
        report -- not just a bare citation."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Promotion requires resolving all bleed warnings first "
            "(fix the fact or keep it project-local), recorded in the "
            "session report",
            normalized,
        )

    def test_validator_module_has_bleed_check_functions(self):
        """Sanity pin that the implementation exists where the docs say it
        does: validate_memory.py exposes the craft-store detector, the
        hand-edited handle list, and validate() accepts warnings=."""
        content = _cached_read_text((REPO_ROOT / "tools" / "validate_memory.py"))
        self.assertIn("_craft_plugin_root", content)
        self.assertIn("CRAFT_BLEED_HANDLES", content)
        self.assertIn("def validate(path, warnings=None):", content)
