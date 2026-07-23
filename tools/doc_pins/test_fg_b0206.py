"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0206`: TestFgB0206RollbackPins.
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


class TestFgB0206RollbackPins(unittest.TestCase):
    """Pins for fg-b0206: `/forge:update --version vX.Y.Z` version-rollback
    flow — install against the public mirror's fresh-history-per-release
    tags (`fg-a10913`), the proactive fg-e106 schema-version compatibility
    warning fired before rollback completes, and the plugin-version-only
    scope boundary against fg-a10302's mid-task execution-state recovery.
    """

    UPDATE_PATH = REPO_ROOT / "commands" / "update.md"

    def _update_content(self):
        return _cached_read_text(self.UPDATE_PATH)

    def test_update_file_exists(self):
        self.assertTrue(self.UPDATE_PATH.is_file())

    def test_argument_hint_documents_version_flag(self):
        content = self._update_content()
        self.assertIn('argument-hint: "[--version vX.Y.Z]"', content)

    def test_version_rollback_heading_present(self):
        content = self._update_content()
        self.assertIn(
            "## Version rollback: `/forge:update --version vX.Y.Z`", content
        )

    def test_cites_fg_a10913_fresh_history_tag_convention(self):
        content = self._update_content()
        section = content.split("## Version rollback:")[1].split(
            "## Relationship to the SessionStart nudge"
        )[0]
        self.assertIn("`fg-a10913`", section)
        self.assertIn("fresh history per\nrelease", section)
        self.assertIn("tagged `v<version>`", section)

    def test_documents_version_pinned_install_path(self):
        content = self._update_content()
        section = content.split("## Version rollback:")[1].split(
            "## Relationship to the SessionStart nudge"
        )[0]
        self.assertIn(
            "**Version-pinned install, where the installed CLI supports "
            "it.**",
            section,
        )

    def test_documents_manual_fallback_path(self):
        content = self._update_content()
        section = content.split("## Version rollback:")[1].split(
            "## Relationship to the SessionStart nudge"
        )[0]
        self.assertIn(
            "**Documented-manual fallback, where it doesn't.**", section
        )
        self.assertIn(
            "this command does **not** invent one", section
        )

    def test_scope_boundary_excludes_fg_a10302_execution_state(self):
        content = self._update_content()
        section = content.split("## Version rollback:")[1].split(
            "## Relationship to the SessionStart nudge"
        )[0]
        self.assertIn(
            "**Scope — plugin version rollback only.**", section
        )
        self.assertIn("`fg-a10302`", section)
        self.assertIn("stays deferred/backlog per the spec's Non-goals", section)

    def test_proactive_schema_check_heading_and_ordering(self):
        """The schema-version check must be documented as happening BEFORE
        the install step, not after — that's the whole point of
        'proactive'."""
        content = self._update_content()
        self.assertIn(
            "### Proactive schema-version compatibility check", content
        )
        section = content.split("## Version rollback:")[1]
        check_pos = section.index(
            "### Proactive schema-version compatibility check"
        )
        stop_pos = section.index("stop before installing")
        self.assertLess(check_pos, stop_pos)
        self.assertIn(
            "Before any rollback install completes", section
        )

    def test_fg_e106_message_reused_verbatim(self):
        """The exact fg-e106 wording must match all three validators
        character-for-character (tools/validate_task.py,
        tools/validate_spec.py, tools/validate_memory.py) — never
        paraphrased."""
        content = self._update_content()
        pinned_message = (
            "produced by a newer Forge (schema-version {schema_version} "
            "> {SUPPORTED_SCHEMA}) — upgrade the plugin"
        )
        self.assertIn(pinned_message, content)

        # Cross-check against the live validator source strings so this
        # pin can never silently drift from the real fg-e106 wording.
        validators = [
            REPO_ROOT / "tools" / "validate_task.py",
            REPO_ROOT / "tools" / "validate_spec.py",
            REPO_ROOT / "tools" / "validate_memory.py",
        ]
        for path in validators:
            src = _cached_read_text(path)
            self.assertIn(
                'f"produced by a newer Forge (schema-version "',
                src,
                f"{path} no longer has the fg-e106 message — "
                "update.md's verbatim pin is now stale",
            )
            self.assertIn(
                'f"{schema_version} > {SUPPORTED_SCHEMA}) '
                '— upgrade the plugin")',
                src,
            )

    def test_never_paraphrases_fg_e106_never_invents_flags(self):
        content = self._update_content()
        self.assertIn("never paraphrased", content)

    def test_top_standing_rule_declares_the_network_exception(self):
        """The top-of-file 'never fetches from the network' sentence must
        acknowledge the schema-version-inspection exception and point at
        the section that defines its scope — no reader stumbling on the
        standing rule should be left unaware the exception exists."""
        content = self._update_content()
        intro = content.split("## What this command does")[0]
        self.assertIn(
            "Forge never\nfetches, writes, or executes plugin code from "
            "the network itself",
            intro,
        )
        self.assertIn("**The single exception**", intro)
        self.assertIn(
            'see "Proactive schema-version compatibility\ncheck" below',
            intro,
        )

    def test_never_does_bullet_declares_the_network_exception(self):
        """The 'What this command never does' network-fetch bullet must
        carry the same cross-reference as the top-of-file rule."""
        content = self._update_content()
        section = content.split("## What this command never does")[1].split(
            "## Version rollback:"
        )[0]
        self.assertIn(
            "Never fetches or executes anything itself beyond invoking "
            "the `claude", section,
        )
        self.assertIn("**The single exception**", section)
        self.assertIn(
            '(see "Proactive schema-version compatibility check" below)',
            section,
        )

    def test_schema_check_section_declares_itself_the_sole_exception(self):
        """The check section itself must state it is THE sole exception
        (not just an exception), that it is read-only, and that it
        executes nothing fetched — closing the loop back to both standing-
        rule sentences so the rule and exception mutually cite each
        other."""
        content = self._update_content()
        section = content.split(
            "### Proactive schema-version compatibility check"
        )[1].split("## Relationship to the SessionStart nudge")[0]
        self.assertIn(
            "the sole, narrowly-scoped exception to the standing "
            '"never\nfetches or executes anything from the network" rule',
            section,
        )
        self.assertIn("**read-only**", section)
        self.assertIn("never executes any fetched content", section)
        self.assertIn(
            "no cloning-and-running, no importing, no `eval`", section
        )

    def test_schema_check_never_clones_and_runs_fetched_code(self):
        """Regression pin: the check must be documented as a plain-text
        constant read (grep / git-show-of-one-file), never a checkout that
        executes anything from the target tag."""
        content = self._update_content()
        section = content.split(
            "### Proactive schema-version compatibility check"
        )[1].split("## Relationship to the SessionStart nudge")[0]
        self.assertIn(
            "never by cloning and running code from\n  the target tag",
            section,
        )
