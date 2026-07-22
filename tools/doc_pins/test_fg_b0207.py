"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0207`: TestFgB0207LifecycleDocsPins.
Split into one module per task-id prefix so concurrent tasks appending pins
land in separate files instead of conflicting at a shared tail."""
import pathlib
import sys
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


class TestFgB0207LifecycleDocsPins(unittest.TestCase):
    """Doc-pins for fg-b0207 (spec-6b7c... "agent porting and lifecycle"):
    the dated conventions section "Plugin lifecycle: uninstall + rollback —
    2026-07-20" (docs/conventions/config-and-features.md, indexed from
    docs/conventions.md's TOC + Shards manifest) and the CONTRIBUTING.md
    pointer line. Summarizes fg-b0205 (commands/uninstall.md) and fg-b0206
    (commands/update.md's rollback section) BY CITATION only -- these pins
    check the summary text itself, not a restatement of the underlying
    commands (those are pinned separately by test_fg_b0205.py /
    test_fg_b0206.py)."""

    CONFIG_SHARD_PATH = (
        REPO_ROOT / "docs" / "conventions" / "config-and-features.md"
    )
    CONVENTIONS_INDEX_PATH = REPO_ROOT / "docs" / "conventions.md"
    CONTRIBUTING_PATH = REPO_ROOT / "CONTRIBUTING.md"

    HEADING = "## Plugin lifecycle: uninstall + rollback — 2026-07-20"

    def _shard(self):
        return _cached_read_text(self.CONFIG_SHARD_PATH)

    def _index(self):
        return _cached_read_text(self.CONVENTIONS_INDEX_PATH)

    def _contributing(self):
        return _cached_read_text(self.CONTRIBUTING_PATH)

    def _section(self):
        content = self._shard()
        self.assertIn(self.HEADING, content)
        return content.split(self.HEADING)[1]

    # -- placement: heading exists in the config-and-features shard --
    def test_heading_present_in_config_and_features_shard(self):
        self.assertIn(self.HEADING, self._shard())

    def test_heading_is_last_section_in_shard(self):
        """Tail-append convention: the new dated section is appended after
        the shard's existing last section (fg-b0104, "Operator profile
        system"), never inserted mid-file."""
        content = self._shard()
        op_profile_pos = content.index(
            "## Operator profile system — 2026-07-18 (fg-b0104, spec-4d2a)"
        )
        new_section_pos = content.index(self.HEADING)
        self.assertGreater(new_section_pos, op_profile_pos)

    # -- TOC + Shards manifest lines in the index file --
    def test_toc_line_present(self):
        content = self._index()
        self.assertIn(
            "- Plugin lifecycle: uninstall + rollback — 2026-07-20", content
        )

    def test_shards_manifest_line_present(self):
        content = self._index()
        self.assertIn(
            "- `Plugin lifecycle: uninstall + rollback — 2026-07-20` -> "
            "`docs/conventions/config-and-features.md`",
            content,
        )

    def test_corpus_reassembly_includes_new_section(self):
        """The fg-b0401 corpus loader must pick up the new section via the
        Shards manifest -- confirms the manifest line is wired, not just
        present as text."""
        corpus = conventions_corpus.corpus_text()
        self.assertIn(self.HEADING, corpus)

    # -- content: cites both shipped commands by file, never restates --
    def test_cites_uninstall_command_file(self):
        section = self._section()
        self.assertIn("`commands/uninstall.md`", section)
        self.assertIn("`/forge:uninstall`", section)
        self.assertIn("`fg-b0205`", section)

    def test_cites_update_rollback_section(self):
        section = self._section()
        self.assertIn("`commands/update.md`", section)
        self.assertIn(
            "Version rollback:\n`/forge:update --version vX.Y.Z`", section
        )
        self.assertIn("`fg-b0206`", section)

    def test_uninstall_summary_cites_interactive_only_rule(self):
        section = self._section()
        self.assertIn("**Interactive-only**", section)
        self.assertIn("`--yes`/`--force`", section)

    def test_uninstall_summary_cites_forge_dir_confirm_scope(self):
        section = self._section()
        self.assertIn("`AskUserQuestion`", section)
        self.assertIn(
            "scoped\nto the current repo's own `.forge/` only", section
        )

    def test_rollback_summary_cites_schema_check_stop_rule(self):
        section = self._section()
        self.assertIn(
            "**proactive schema-version compatibility check**", section
        )
        self.assertIn("`fg-e106`", section)
        self.assertIn("**stops before installing**", section)

    def test_rollback_summary_cites_declared_network_exception(self):
        section = self._section()
        self.assertIn("**read-only**", section)
        self.assertIn("never a clone-and-run", section)

    def test_rollback_summary_cites_fg_a10302_exclusion(self):
        section = self._section()
        self.assertIn("`fg-a10302`", section)
        self.assertIn("deferred/backlog", section)

    # -- CONTRIBUTING.md pointer --
    def test_contributing_pointer_present_in_clone_and_install_section(self):
        content = self._contributing()
        self.assertIn("## 1. Clone + install", content)
        self.assertIn("## 2. Provider auth", content)
        section = content.split("## 1. Clone + install")[1].split(
            "## 2. Provider auth"
        )[0]
        self.assertIn("`/forge:uninstall`", section)
        self.assertIn("`/forge:update\n--version vX.Y.Z`", section)
        self.assertIn(
            "\"Plugin\nlifecycle: uninstall + rollback — 2026-07-20\"",
            section,
        )

    def test_contributing_pointer_cites_docs_conventions(self):
        content = self._contributing()
        section = content.split("## 1. Clone + install")[1].split(
            "## 2. Provider auth"
        )[0]
        self.assertIn("`docs/conventions.md`", section)


if __name__ == "__main__":
    unittest.main()
