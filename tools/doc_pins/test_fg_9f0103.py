"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9f0103`: TestFg9f0103ReadmePins.
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

from . import test_fg_9f0101 as _fg_9f0101_mod  # noqa: E402 -- fg-a11040 shard cross-reference (import the module, not the class, so pytest does not re-collect the TestCase as a duplicate test item here)


class TestFg9f0103ReadmePins(unittest.TestCase):
    """Doc-pins for fg-9f0103 (product-grade README): hero logo reference,
    mermaid architecture diagram, quickstart anchor, and the full 19-persona
    roster table all survive in README.md.

    Reuses _fg_9f0101_mod.TestFg9f0101PersonaPins.CANONICAL_PERSONAS as the single source
    of truth for the 19 persona names rather than re-listing them, so the
    two pin suites can't silently drift apart.
    """

    def test_readme_has_logo_reference(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("assets/logo-light.png", content)

    def test_readme_has_mermaid_architecture_diagram(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("```mermaid", content)
        self.assertIn("flowchart", content)

    def test_readme_has_quickstart_anchor(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("/forge:onboard", content)
        self.assertIn("## Quickstart", content)

    def test_readme_has_all_20_personas(self):
        content = _cached_read_text((REPO_ROOT / "README.md"))
        for slug, persona in _fg_9f0101_mod.TestFg9f0101PersonaPins.CANONICAL_PERSONAS.items():
            self.assertIn(persona, content, f"persona {persona!r} ({slug}) missing from README")
            self.assertIn(f"`{slug}`", content, f"slug {slug!r} missing from README")

    def test_readme_hero_is_theme_aware(self):
        """Verify the README hero uses a <picture> element with a
        prefers-color-scheme dark source, so the logo actually adapts to
        the reader's theme instead of being a single static image."""
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("<picture>", content)
        self.assertIn("prefers-color-scheme: dark", content)

    def test_readme_references_both_theme_logo_variants(self):
        """Verify both theme-variant logo files are referenced from the
        README (not just created on disk) and that both files exist."""
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("assets/logo-dark.png", content)
        self.assertIn("assets/logo-light.png", content)
        self.assertTrue((REPO_ROOT / "assets" / "logo-dark.png").exists())
        self.assertTrue((REPO_ROOT / "assets" / "logo-light.png").exists())

    def test_readme_tests_badge_uses_drift_proof_floor(self):
        """Verify the tests badge uses a floor format (e.g. "400+") rather
        than an exact count, so it doesn't silently go stale as waves add
        tests — pins the literal badge substring used in the hero.
        Floor raised 400->980 at the 2026-07-18 v0.12.0 release point;
        980->1300 at the 2026-07-19 v0.14.0 release point (the release
        commit bumped the badge but missed this companion pin -- caught by
        the fg-a10408 gate run)."""
        content = _cached_read_text((REPO_ROOT / "README.md"))
        self.assertIn("tests-1300%2B-brightgreen", content)
