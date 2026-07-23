"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9f0102`: TestFg9f0102ForgeDirPins.
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


class TestFg9f0102ForgeDirPins(unittest.TestCase):
    """Doc-pins for fg-9f0102 (.forge/ layout visibility): the canonical
    README template exists and states the plugin-vs-project split, queue's
    Auto-init wires it in alongside .provenance, spec/discover each carry a
    one-line pointer to queue's rule instead of restating it, and
    /forge:status offers to backfill a missing README.md.

    Covers all 3 EARS clauses: (1) auto-init writes .forge/README.md from
    the template, explaining project vs plugin contents including the
    .forge/agents/ carve-out; (2) /forge:status offers to add a missing
    README once, never nagging twice a session; (3) the template is
    single-sourced in the queue skill's references, cited (not duplicated)
    by the other auto-init paths.
    """

    def test_template_exists_and_has_plugin_vs_project_anchor(self):
        """The canonical template exists and explicitly draws the
        plugin-vs-project line — the actual sentence a user reads, not just
        a heading — so a future edit can't quietly gut the distinction this
        task exists to state."""
        tpl_path = (
            REPO_ROOT / "skills" / "queue" / "references"
            / "forge-dir-readme-template.md"
        )
        self.assertTrue(tpl_path.exists(), "forge-dir-readme-template.md missing")
        content = _cached_read_text(tpl_path)
        self.assertIn(
            "agents, skills, commands, and hooks are NOT in this folder",
            content,
        )
        self.assertIn("shared by all your projects", content)

    def test_template_has_project_local_agent_carveout_and_entries(self):
        """Pins the /forge:agent project-local carve-out plus a sample of
        the one-line-per-entry inventory (queue/tasks/, map/, forge.md)."""
        tpl_path = (
            REPO_ROOT / "skills" / "queue" / "references"
            / "forge-dir-readme-template.md"
        )
        content = _cached_read_text(tpl_path)
        self.assertIn("/forge:agent", content)
        self.assertIn("`queue/tasks/`", content)
        self.assertIn("`map/`", content)
        self.assertIn("`forge.md`", content)
        self.assertIn(".trust-local", content)

    def test_queue_auto_init_wires_readme_template(self):
        """Verify queue's Auto-init writes README.md from the template
        alongside .provenance, on the same trigger, never overwriting an
        existing one — the actual wiring, not just a mention of the
        filename."""
        content = _cached_read_text((REPO_ROOT / "skills" / "queue" / "SKILL.md"))
        self.assertIn("references/forge-dir-readme-template.md", content)
        self.assertIn(
            "Never overwrite an existing `.forge/README.md`.", content
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "on that same first-ever-`.forge/` trigger, also write "
            "`.forge/README.md`",
            normalized,
        )

    def test_spec_and_discover_have_readme_pointer_lines(self):
        """spec and discover each cite queue's README rule with a one-line
        pointer rather than restating the template wiring."""
        spec_content = _cached_read_text((REPO_ROOT / "skills" / "spec" / "SKILL.md"))
        discover_content = _cached_read_text((
            REPO_ROOT / "skills" / "discover" / "SKILL.md"
        ))

        spec_normalized = re.sub(r"\s+", " ", spec_content)
        discover_normalized = re.sub(r"\s+", " ", discover_content)

        self.assertIn(
            "It also writes `.forge/README.md` from the template on that "
            "same trigger, same rule as queue's.",
            spec_normalized,
        )
        self.assertIn(
            "It also writes `.forge/README.md` from the template on that "
            "same trigger, same rule as queue's.",
            discover_normalized,
        )
        # Neither restates the template's own filename/path — that stays
        # single-sourced in queue's Auto-init section.
        self.assertNotIn("forge-dir-readme-template.md", spec_content)
        self.assertNotIn("forge-dir-readme-template.md", discover_content)

    def test_status_command_offers_missing_readme_once(self):
        """/forge:status offers to backfill a missing README.md, pointing at
        the same canonical template, with the never-twice-a-session rule
        stated inline."""
        content = _cached_read_text((REPO_ROOT / "commands" / "status.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "If `.forge/` exists but `.forge/README.md` doesn't, offer once",
            normalized,
        )
        self.assertIn("forge-dir-readme-template.md", normalized)
        self.assertIn("never repeat this offer twice", normalized)
