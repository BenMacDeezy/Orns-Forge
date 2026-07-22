"""Doc-pin regression tests: cross-cutting pins (fg-9b0303 arbitration
paragraphs + map freshness, fg-9b0302 README/command-surface pins, and the
/court command consistency checks).

fg-a11040: the per-task-id doc-pin classes that used to live in this file
were sharded out to tools/doc_pins/test_fg_<id>.py (one module per task-id
prefix) so concurrent tasks appending new pins land in separate files
instead of conflicting at a shared tail. This file is kept -- thinned to
just the classes that aren't scoped to a single task id -- so any external
reference to tools/test_doc_pins.py keeps working. Shared helpers (REPO_ROOT,
cached file readers, the conventions corpus loader) now live in
tools/doc_pins/_common.py; both this file and the shard modules import from
there so there is exactly one copy of each helper."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from doc_pins._common import (  # noqa: E402
    REPO_ROOT,
    _read_path,
    _cached_read_text,
    _CONVENTIONS_PATH_RESOLVED,
    _WORD_TO_INT,
    validate_task,
    shard_task,
    conventions_corpus,
)


class TestDocPins(unittest.TestCase):
    """Mechanical regression tests for prose decision content and map freshness."""

    def test_secure_diff_review_has_cybersecurity_arbitration(self):
        """Verify forge-secure-diff-review SKILL.md contains scope arbitration and cybersecurity.

        Also pins a semantic anchor ("diff-scoped") from the paragraph body,
        not just the heading — a heading alone is gameable (someone could
        rename/gut the paragraph under "Scope arbitration" and still pass).
        Anchoring on body text forces the actual arbitration rule to survive.
        """
        skill_path = REPO_ROOT / "skills" / "forge-secure-diff-review" / "SKILL.md"
        content = _cached_read_text(skill_path)
        self.assertIn("Scope arbitration", content)
        self.assertIn("cybersecurity", content)
        self.assertIn("diff-scoped", content)

    def test_anti_generic_has_frontend_design_precedence(self):
        """Verify anti-generic-design-restraint SKILL.md contains precedence vs frontend-design.

        Also pins "vetoes" — the semantic core of the precedence rule (this
        skill only vetoes genericness, it doesn't choose direction). The
        heading alone doesn't distinguish a real precedence rule from an
        empty or reworded section; the body fragment does.
        """
        skill_path = REPO_ROOT / "skills" / "anti-generic-design-restraint" / "SKILL.md"
        content = _cached_read_text(skill_path)
        self.assertIn("Precedence vs", content)
        self.assertIn("frontend-design", content)
        self.assertIn("vetoes", content)

    def test_bug_triage_has_queue_boundary(self):
        """Verify bug-triage-classification SKILL.md contains boundary vs forge:queue.

        Also pins "nothing to reproduce or classify" — the actual dividing
        line the boundary paragraph draws (task-shaped TODOs have nothing to
        reproduce, so they skip triage). Without this, the heading plus a bare
        mention of "forge:queue" elsewhere in the file could satisfy the test
        without the boundary rule itself being intact.
        """
        skill_path = REPO_ROOT / "skills" / "bug-triage-classification" / "SKILL.md"
        content = _cached_read_text(skill_path)
        self.assertIn("Boundary vs", content)
        self.assertIn("forge:queue", content)
        self.assertIn("nothing to reproduce or classify", content)

    def test_map_freshness_header_is_real_commit(self):
        """Verify .forge/map/architecture.md forge-map-commit header points to a real commit."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = _cached_read_text(map_path)
        match = re.search(r"forge-map-commit: ([0-9a-f]{40})", content)
        self.assertIsNotNone(match, "forge-map-commit header not found in architecture.md")

        sha = match.group(1)
        result = subprocess.run(
            ["git", "cat-file", "-t", sha],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.stdout.strip(), "commit", f"SHA {sha} is not a valid commit")

    def test_map_mentions_current_surface(self):
        """Verify architecture.md contains v0.7.1 surface mentions (case-insensitive)."""
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = _cached_read_text(map_path).lower()
        self.assertIn("workflow", content)
        # "craft memory" or "Craft memory" -> check for both variants case-insensitive
        self.assertTrue(
            "craft memory" in content,
            "craft memory not found in architecture.md"
        )
        self.assertIn("fable", content)

    def test_map_command_count_consistent(self):
        """Verify the map's spelled-out command count, its entry-point bullet
        list, and the actual commands/*.md files all agree.

        Three independent surfaces claim to describe "how many commands
        Forge has": the Commands prose (spelled out, e.g. "Sixteen thin
        slash-command entry points"), the per-command entry-point bullet
        list (lines starting "- `/forge:"), and the real command files on
        disk. They can silently drift from each other when a command is
        added/removed and only one surface gets updated — this pin catches
        that drift instead of trusting any single surface.
        """
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")

        content = _cached_read_text(map_path)

        prose_match = re.search(
            r"\b([A-Za-z]+(?:-[A-Za-z]+)?)\s+thin slash-command entry points",
            content,
        )
        self.assertIsNotNone(
            prose_match,
            "Commands prose ('<N> thin slash-command entry points') not found",
        )
        word = prose_match.group(1).lower()
        self.assertIn(
            word, _WORD_TO_INT,
            f"unrecognized spelled-out number {word!r} in Commands prose",
        )
        prose_count = _WORD_TO_INT[word]

        entry_bullets = re.findall(r"^- `/forge:\w+", content, re.MULTILINE)
        entry_count = len(entry_bullets)

        actual_files = list((REPO_ROOT / "commands").glob("*.md"))
        actual_count = len(actual_files)

        self.assertEqual(
            prose_count, entry_count,
            f"Commands prose says {prose_count} but the entry-point bullet "
            f"list has {entry_count} lines",
        )
        self.assertEqual(
            prose_count, actual_count,
            f"Commands prose says {prose_count} but commands/*.md has "
            f"{actual_count} files",
        )


class TestCommandSurfacePins(unittest.TestCase):
    """Doc-pins for fg-9b0302: README surface, memory read section, verify safety."""

    def test_readme_lists_all_commands(self):
        readme = _cached_read_text((REPO_ROOT / "README.md"))
        commands = sorted(p.stem for p in (REPO_ROOT / "commands").glob("*.md"))
        for name in commands:
            self.assertIn(name, readme,
                          f"command {name!r} missing from README")

    def test_memory_skill_has_read_section(self):
        t = _cached_read_text((REPO_ROOT / "skills" / "memory" / "SKILL.md"))
        self.assertIn("Reading & searching", t)

    def test_verify_command_is_report_only(self):
        t = _cached_read_text((REPO_ROOT / "commands" / "verify.md"))
        self.assertIn("never transitions a task", t)

    def test_status_board_single_sourced_in_queue_skill(self):
        self.assertIn("Status board",
                      _cached_read_text((REPO_ROOT / "skills" / "queue" / "SKILL.md")))


class TestCourtCommandPins(unittest.TestCase):
    """Doc-pins for court-system-spec-review: /forge:court, the five-phase
    adversarial document-court command, plus the map/docs count-surface
    refresh (22 -> 23 commands) its addition to commands/*.md required.
    """

    def _court_content(self):
        return _read_path("commands/court.md")

    def test_court_command_file_exists(self):
        self.assertTrue((REPO_ROOT / "commands" / "court.md").exists())

    def test_court_frontmatter_argument_hint(self):
        content = self._court_content()
        self.assertIn(
            'argument-hint: "<path> [--focused \\"<delta scope>\\"]"',
            content,
        )

    def test_court_names_all_five_phases(self):
        content = self._court_content()
        for phase in (
            "PROSECUTION",
            "CLERK",
            "DEFENSE",
            "JUDGMENT",
            "VERDICT",
        ):
            self.assertIn(phase, content)

    def test_court_prosecution_jurisdiction_range_and_missing_beat(self):
        content = self._court_content()
        self.assertIn("5–9 jurisdiction-partitioned prosecutors", content)
        self.assertIn("what's-missing jurisdiction", content)
        self.assertIn("no scenario = inadmissible, not filed", content)

    def test_court_clerk_is_mechanical_and_drops_nothing(self):
        content = self._court_content()
        self.assertIn("drops or\n   softens nothing", content)
        self.assertIn("MECHANICAL tier", content)

    def test_court_judgment_reads_document_itself_never_hearsay(self):
        content = self._court_content()
        self.assertIn("never hearsay", content)
        self.assertIn("sustained-as-modified", content)

    def test_court_verdict_overruled_record_and_no_auto_apply(self):
        content = self._court_content()
        self.assertIn("OVERRULED RECORD", content)
        self.assertIn("Amendments are never auto-applied", content)

    def test_court_never_names_or_defaults_a_model(self):
        content = self._court_content()
        self.assertIn(
            "This\n  command never names or defaults a model.", content
        )
        self.assertIn("MECHANICAL/JUDGMENT vocabulary", content)

    def test_court_cost_gate_is_human_ask_only(self):
        content = self._court_content()
        self.assertIn(
            "Cost gate — fires only on the human's own ask, never "
            "automatically.",
            content,
        )
        self.assertIn(
            "prosecutors + 1 (clerk) + charges (defense) +\n  areas "
            "(judgment) + 1 (chief justice)",
            content,
        )

    def test_court_focused_mode_scopes_to_delta_and_bars_relitigation(self):
        content = self._court_content()
        self.assertIn("run fewer prosecutors", content)
        self.assertIn("scoped to the delta only", content)
        self.assertIn(
            "prior rulings from an earlier pass on the same\n   document "
            "are off-limits",
            content,
        )

    def test_court_verdict_file_collision_never_silent_overwrite(self):
        # 2026-07-20 grouped retro-verify P1 fix: same-day re-trial must
        # suffix, never clobber the prior verdict's OVERRULED RECORD.
        content = self._court_content()
        self.assertIn("**Verdict-file collision check —\n   runs before "
                      "the write.**", content)
        self.assertIn("NEVER allowed to\n   silently overwrite a prior "
                      "verdict", content)
        self.assertIn("<target-stem>-court-<YYYY-MM-DD>-2.md", content)
        self.assertIn("the prior verdict\n   is never modified or deleted",
                      content)

    def test_court_focused_mode_discovers_prior_rulings(self):
        # 2026-07-20 grouped retro-verify P1 fix: the off-limits rule needs
        # an operational discovery step or it is decorative.
        content = self._court_content()
        self.assertIn("**Prior rulings are discovered,\n   not assumed**",
                      content)
        self.assertIn("globs\n   `<target-stem>-court-*.md`", content)
        self.assertIn("includes both verbatim\n   in each prosecutor's "
                      "brief as the off-limits docket", content)

    def test_court_command_and_skill_files_exist_no_new_agent_defs(self):
        # Boundary check: court.md dispatches read-only judge-shaped
        # agents via the generic Agent tool -- no new agents/*.md file
        # should exist for this task.
        self.assertFalse((REPO_ROOT / "agents" / "forge-court.md").exists())

    def test_map_architecture_names_court_entry_point(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertIn(
            "- `/forge:court <doc>` → `commands/court.md`: adversarial "
            "document court.",
            content,
        )
        # fg-b0203 bumped this 23->24 (commands/port.md added /forge:port);
        # prd-blueprint-command bumped it 24->25 (commands/blueprint.md
        # added /forge:blueprint); the startup-banner removal (owner-
        # directed, 2026-07-22) bumped 26->25 back down. This pin now
        # asserts the current count, not the count court's own addition
        # produced.
        self.assertIn("twenty-six slash commands", content)

    def test_map_architecture_under_char_ceiling(self):
        map_path = REPO_ROOT / ".forge" / "map" / "architecture.md"
        if not map_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(map_path)
        self.assertLessEqual(len(content), 8000)

    def test_map_subsystems_commands_names_court(self):
        subsys_path = (
            REPO_ROOT / ".forge" / "map" / "subsystems" / "commands.md"
        )
        if not subsys_path.exists():
            self.skipTest("Map not present (per-repo, optional)")
        content = _cached_read_text(subsys_path)
        self.assertIn("Twenty-six thin slash-command entry points", content)
        self.assertIn("`court`", content)

    def test_docs_architecture_names_twenty_three_commands(self):
        content = _read_path("docs/architecture.md")
        self.assertIn(
            "Twenty-six thin slash-command entry points under "
            "`commands/*.md`",
            content,
        )


if __name__ == "__main__":
    unittest.main()
