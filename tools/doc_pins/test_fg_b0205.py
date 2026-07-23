"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0205`: TestFgB0205UninstallPins.
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


class TestFgB0205UninstallPins(unittest.TestCase):
    """Doc-pins for fg-b0205 (spec-6b7c, "Agent porting and lifecycle"):
    commands/uninstall.md, the new /forge:uninstall command. Every substring
    below is unique to text this task added -- never a phrase update.md or
    customization-persistence.md already owns in text this task cites but
    does not restate."""

    UNINSTALL_PATH = REPO_ROOT / "commands" / "uninstall.md"

    def _uninstall(self):
        return _cached_read_text(self.UNINSTALL_PATH)

    def test_frontmatter_description_present(self):
        content = self._uninstall()
        self.assertIn(
            "description: Uninstall Forge — sequence claude plugin removal, "
            "offer .forge/ removal, print an itemized report",
            content,
        )

    def test_never_fetches_writes_or_executes_plugin_code_itself(self):
        content = self._uninstall()
        self.assertIn(
            "`/forge:uninstall` runs the **real Claude Code plugin manager** "
            "— Forge\nnever fetches, writes, or executes plugin code from "
            "the network itself.",
            content,
        )

    def test_interactive_only_no_flag_normative_sentence(self):
        content = self._uninstall()
        self.assertIn(
            "**Interactive-only — no scripted or unattended form.** There "
            "is no\n`--yes`/`--force` flag and none will be added: every "
            "irreversible step below\nis gated on an explicit human "
            "confirmation in this session.",
            content,
        )

    def test_noninteractive_context_stops_instead_of_guessing(self):
        content = self._uninstall()
        self.assertIn(
            "If invoked from\na non-interactive context where a structured "
            "confirm cannot be shown, stop\nand report that "
            "`/forge:uninstall` requires an interactive session instead\n"
            "of guessing an answer or proceeding unconfirmed.",
            content,
        )

    def test_sequences_real_cli_uninstall_and_marketplace_remove_commands(self):
        content = self._uninstall()
        self.assertIn(
            "`claude plugin uninstall forge@<marketplace-name>` (or the "
            "CLI's\n     documented equivalent) removes the plugin "
            "installation itself.",
            content,
        )
        self.assertIn(
            "`claude plugin marketplace remove <marketplace-name>` removes "
            "the\n     marketplace entry — but **only if this session's "
            "own flow added that\n     marketplace**",
            content,
        )

    def test_marketplace_not_added_this_session_is_left_alone(self):
        content = self._uninstall()
        self.assertIn(
            "A marketplace entry that\n     predates this session, or that "
            "this session did not itself add, is\n     left alone: Forge "
            "does not know what else depends on it and must not\n     "
            "assume it is safe to remove.",
            content,
        )

    def test_forge_dir_offer_via_one_structured_askuserquestion(self):
        content = self._uninstall()
        self.assertIn(
            "3. **Offer `.forge/` removal via one structured confirm.** "
            "Once steps 1-2\n   are done, ask a single `AskUserQuestion` "
            "(per `docs/conventions.md`,\n   \"Asking the user questions "
            "(interactive skills)\") scoped to exactly one\n   decision:",
            content,
        )

    def test_declining_leaves_forge_dir_fully_intact(self):
        content = self._uninstall()
        self.assertIn(
            "**Declining leaves `.forge/` fully intact** — no queue task, "
            "spec,\n     memory file, constitution, or config under it is "
            "touched.",
            content,
        )

    def test_forge_dir_scoped_to_current_repo_only_no_filesystem_scan(self):
        content = self._uninstall()
        self.assertIn(
            "Only on explicit `Remove .forge/` does this command delete "
            "the\n     directory, and only for **this repo's own "
            "`.forge/`** — the one at\n     this repo's root, resolved "
            "from the current working directory. It\n     never "
            "filesystem-scans for, nor touches, any other repo's "
            "`.forge/`\n     directory (per-repo trust model — every "
            "repo's Forge installation is\n     independently trusted and "
            "independently removed).",
            content,
        )

    def test_itemized_removed_list_and_never_overclaim_sentence(self):
        content = self._uninstall()
        self.assertIn(
            "4. **Print an exact itemized removed-list.** One line per "
            "thing actually\n   removed this run, e.g.:",
            content,
        )
        self.assertIn(
            "Never list something as removed that wasn't — a skipped "
            "marketplace\n   entry or a declined `.forge/` removal are "
            "reported as \"not removed\" /\n   \"kept\", "
            "not folded silently into the removed list.",
            content,
        )

    def test_never_accepts_yes_force_flag_sentence(self):
        content = self._uninstall()
        self.assertIn(
            "- Never accepts or checks for a `--yes`/`--force` flag — no "
            "scripted,\n  CI, or non-interactive path exists for this "
            "command, by design.",
            content,
        )

    def test_never_deletes_forge_dir_without_step3_confirmation(self):
        content = self._uninstall()
        self.assertIn(
            "- Never deletes `.forge/` without the explicit structured "
            "confirmation in\n  step 3 — declining always leaves it fully "
            "intact.",
            content,
        )

    def test_never_filesystem_scans_other_repos_forge_dir(self):
        content = self._uninstall()
        self.assertIn(
            "- Never filesystem-scans for or touches any other repo's "
            "`.forge/`\n  directory — `.forge/` handling is scoped to the "
            "current repo only.",
            content,
        )

    def test_never_modifies_beyond_confirmed_project_or_unowned_user_space(self):
        content = self._uninstall()
        self.assertIn(
            "- Never modifies any file under project space beyond what "
            "the human\n  explicitly confirmed for removal, nor any file "
            "under user space\n  (`docs/customization-persistence.md` is "
            "the source of truth for which\n  user-space surfaces Forge "
            "owns).",
            content,
        )

    def test_never_invents_undocumented_claude_plugin_flag(self):
        content = self._uninstall()
        self.assertIn(
            "- Never invents a `claude plugin` flag or subcommand not "
            "shown in the\n  CLI's own `--help` output. If the installed "
            "CLI's help text has drifted\n  from what this command "
            "expects, stop and report the drift instead of\n  proceeding "
            "on a guess.",
            content,
        )

    def test_never_fetches_or_executes_beyond_claude_plugin_subcommands(self):
        content = self._uninstall()
        self.assertIn(
            "- Never fetches or executes plugin code itself beyond "
            "invoking the `claude\n  plugin` subcommands above; all "
            "actual removal work is the installed\n  Claude Code CLI's "
            "own responsibility.",
            content,
            content,
        )
