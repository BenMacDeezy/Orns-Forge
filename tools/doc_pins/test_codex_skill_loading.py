"""Doc-pin regression tests for codex-skill-loading (2026-07-21): Codex
worker skill access — worktree materialization (the guaranteed floor) plus
optional native Agent Skills discovery registration. Split into its own
module per the sharded doc-pins convention (fg-a11040) so this task's pins
land in their own file instead of conflicting at a shared tail.
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


class TestCodexSkillLoadingPins(unittest.TestCase):
    """Pins for codex-skill-loading: materialization path + INTEGRATE
    exclusion, attachment-stays-a-requirement, curated-subset + budget
    numbers, the human-run canary-test precondition, and the trust note."""

    PROVIDER_JUDGES_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "provider-judges.md"
    )
    CONFIG_FEATURES_PATH = REPO_ROOT / "docs" / "conventions" / "config-and-features.md"
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    def _provider_judges_content(self):
        return _cached_read_text(self.PROVIDER_JUDGES_PATH)

    def _config_features_content(self):
        return _cached_read_text(self.CONFIG_FEATURES_PATH)

    def _conventions_content(self):
        return _read_path(self.CONVENTIONS_PATH)

    # -- provider-judges.md section 8 -----------------------------------

    def test_provider_judges_has_skill_materialization_heading(self):
        content = self._provider_judges_content()
        self.assertIn(
            "## 8. Skill materialization (codex-skill-loading, 2026-07-21)",
            content,
        )

    def test_materialization_path_phrase(self):
        """Materialize each attached skill's SKILL.md (+ references/) into
        the dispatch worktree under an uncommitted path."""
        content = self._provider_judges_content()
        self.assertIn(".forge-dispatch/skills/<name>/", content)
        self.assertIn(
            "materialize each attached skill's\n`SKILL.md`", content
        )
        self.assertIn("its `references/` subdirectory", content)

    def test_integrate_exclusion_phrase(self):
        content = self._provider_judges_content()
        self.assertIn(
            "THE SYSTEM SHALL exclude\n"
            "`.forge-dispatch/` from the diff INTEGRATE merges back to "
            "the kernel's\nbranch",
            content,
        )
        self.assertIn(
            "so materialized\n"
            "skill copies never enter the merged diff, never get "
            "committed, and never\n"
            "leak into the task's Files-changed list",
            content,
        )

    def test_materialization_is_floor_regardless_of_native_discovery(self):
        content = self._provider_judges_content()
        self.assertIn(
            "materialization is the\n"
            "floor every provider dispatch gets, never conditional on "
            "native discovery\n"
            "being present, current, or verified",
            content,
        )

    def test_attachment_stays_a_requirement_phrase(self):
        content = self._provider_judges_content()
        self.assertIn(
            "### 8.3 Attachment is a requirement, not merely a discovery hint",
            content,
        )
        self.assertIn(
            "THE SYSTEM SHALL treat that\n"
            "attachment as a requirement the worker is told to follow",
            content,
        )
        self.assertIn(
            "Native discovery is\n"
            "never a substitute for the contract explicitly naming what "
            "applies to a\n"
            "given task",
            content,
        )

    def test_trust_note_phrase(self):
        content = self._provider_judges_content()
        self.assertIn(
            "### 8.4 Trust note — skill content travels with the dispatch",
            content,
        )
        self.assertIn(
            "traveling to that provider — the same trust boundary the "
            "per-provider TOFU\nconfirmation already covers",
            content,
        )
        self.assertIn(
            "exposes the registered skills' content to EVERY Codex "
            "session on the\nmachine",
            content,
        )

    def test_canary_precondition_phrase(self):
        content = self._provider_judges_content()
        self.assertIn(
            "close before automation relies on them: whether `codex\n"
            "exec` (non-interactive dispatch mode) discovers native "
            "skills identically\n"
            "to the interactive TUI",
            content,
        )
        self.assertIn(
            "Forge itself SHALL NOT run `codex exec` to test any of this",
            content,
        )

    # -- docs/conventions/config-and-features.md registration section ---

    def test_config_features_has_registration_heading(self):
        content = self._config_features_content()
        self.assertIn(
            "## Codex native skill discovery — optional registration "
            "(codex-skill-loading, 2026-07-21)",
            content,
        )

    def test_curated_subset_and_budget_numbers(self):
        content = self._config_features_content()
        self.assertIn("roughly 2% of context or 8,000 characters", content)
        self.assertIn("roughly 29,200 measured characters", content)
        self.assertIn(
            "Instead,\nregister only the curated subset actually attached "
            "to provider-eligible\nroles",
            content,
        )

    def test_registration_junction_command(self):
        content = self._config_features_content()
        self.assertIn(
            'mklink /J "%USERPROFILE%\\.agents\\skills\\<name>" '
            '"<forge-plugin-root>\\skills\\<name>"',
            content,
        )
        self.assertIn("no admin rights on Windows", content)

    def test_canary_test_precondition_in_config_features(self):
        content = self._config_features_content()
        self.assertIn(
            "**Precondition — human-run canary test.**", content
        )
        self.assertIn(
            "Materialization\n"
            "(provider-judges.md §8.1) remains the guaranteed floor",
            content,
        )

    def test_trust_note_in_config_features(self):
        content = self._config_features_content()
        self.assertIn("**Trust note.**", content)
        self.assertIn(
            "exposes their\n"
            "content to every Codex session on the machine",
            content,
        )

    # -- docs/conventions.md TOC + shards manifest -----------------------

    def test_conventions_toc_entry(self):
        content = self._conventions_content()
        self.assertIn(
            "- Codex native skill discovery — optional registration "
            "(codex-skill-loading, 2026-07-21)",
            content,
        )

    def test_conventions_shards_manifest_row(self):
        content = self._conventions_content()
        self.assertIn(
            "`Codex native skill discovery — optional registration "
            "(codex-skill-loading, 2026-07-21)` -> "
            "`docs/conventions/config-and-features.md`",
            content,
        )


if __name__ == "__main__":
    unittest.main()
