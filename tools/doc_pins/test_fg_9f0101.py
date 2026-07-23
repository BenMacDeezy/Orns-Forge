"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9f0101`: TestFg9f0101PersonaPins.
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


class TestFg9f0101PersonaPins(unittest.TestCase):
    """Doc-pins for fg-9f0101 (agent persona display-name layer): all 19
    roster agents carry a unique `display-name:` frontmatter field, the
    canonical mapping is stated once in docs/conventions.md as a dated
    amendment (heading + TOC + amended-by + table anchor + label format +
    display-layer-only sentence), and the kernel/queue-status-board cite it.
    Extended by fg-a10802 to 20 roster agents (forge-grunt/Grud added; the
    new row is pinned in the tail "Grud routing" conventions section, not
    by editing this table).
    """

    AGENTS_DIR = REPO_ROOT / "agents"

    CANONICAL_PERSONAS = {
        "forge-worker": "Brokk",
        "forge-verifier": "Vera",
        "forge-ui-verifier": "Iris",
        "forge-reviewer": "Rook",
        "forge-security": "Aegis",
        "forge-legal": "Lex",
        "forge-architect": "Blue",
        "forge-debugger": "Hex",
        "forge-ui": "Pixel",
        "forge-mobile": "Roam",
        "forge-mobile-verifier": "Lens",
        "forge-animator": "Flux",
        "forge-test-writer": "Tess",
        "forge-researcher": "Sage",
        "forge-migrator": "Tern",
        "forge-scout": "Scout",
        "forge-mapper": "Atlas",
        "forge-librarian": "Page",
        "forge-spec-writer": "Quill",
        "forge-triage": "Doc",
        "forge-data": "Rune",
        "forge-grunt": "Grud",
        "forge-finder": "Hound",
        "forge-refuter": "Foil",
        "forge-judge": "Gavel",
    }

    def _agent_files(self):
        return sorted(self.AGENTS_DIR.glob("*.md"))

    def _display_name(self, path):
        content = _cached_read_text(path)
        # Frontmatter is the block between the first two `---` lines.
        parts = content.split("---", 2)
        self.assertGreaterEqual(
            len(parts), 3, f"{path.name}: no frontmatter block found"
        )
        frontmatter = parts[1]
        m = re.search(r"^display-name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        return m.group(1) if m else None

    def test_exactly_23_roster_agents_matching_canonical_slugs(self):
        # Bumped 23->25 (forge-mobile-agent, 2026-07-21): forge-mobile
        # (Roam) / forge-mobile-verifier (Lens) added.
        files = self._agent_files()
        self.assertEqual(len(files), 25)
        self.assertEqual(
            {f.stem for f in files}, set(self.CANONICAL_PERSONAS)
        )

    def test_every_agent_file_has_display_name(self):
        missing = [f.name for f in self._agent_files() if self._display_name(f) is None]
        self.assertEqual(missing, [], f"agent files missing display-name: {missing}")

    def test_display_names_match_canonical_mapping(self):
        found = {f.stem: self._display_name(f) for f in self._agent_files()}
        self.assertEqual(found, self.CANONICAL_PERSONAS)

    def test_display_names_are_unique(self):
        found = [self._display_name(f) for f in self._agent_files()]
        self.assertEqual(
            len(found),
            len(set(found)),
            f"duplicate persona names found: {found}",
        )

    def test_display_name_immediately_follows_name_line(self):
        """One-line diff per file: display-name sits directly after name:,
        nothing else in the agent file changes."""
        for f in self._agent_files():
            lines = _cached_read_text(f).splitlines()
            name_idx = next(
                i for i, line in enumerate(lines) if line.startswith("name: ")
            )
            self.assertTrue(
                lines[name_idx + 1].startswith("display-name: "),
                f"{f.name}: display-name must immediately follow the name: line",
            )

    def test_conventions_has_persona_amendment_heading(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "## Dispatch display labels — persona amendment — 2026-07", content
        )

    def test_conventions_persona_amendment_in_toc(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "  - Dispatch display labels — persona amendment — 2026-07", content
        )

    def test_conventions_base_section_has_amended_by_pointer(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            '## Dispatch display labels — 2026-07\n\n'
            '> Amended by: "Dispatch display labels — persona amendment — 2026-07"',
            content,
        )

    def test_conventions_persona_table_anchor_and_full_mapping(self):
        """Table anchor (`| Slug | Persona |`) plus every one of the 19
        canonical slug->persona rows, plus örn as the orchestrator row —
        all inside the persona amendment section specifically."""
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        self.assertIn("| Slug | Persona |", section)
        self.assertIn("| örn |", section)
        for slug, persona in self.CANONICAL_PERSONAS.items():
            self.assertIn(f"| {slug} | {persona} |", section)

    def test_conventions_persona_section_has_label_format(self):
        """Historical: the original `<Persona> · <short task title>` format
        text is preserved verbatim (tail-append house convention — amended
        sections keep their prose, never edited in place) even though
        fg-a10213's role-label amendment (below) supersedes it as the
        format actually in force. The section now also carries an
        Amended-by pointer to that amendment."""
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        self.assertIn("`<Persona> · <short task title>`", section)
        self.assertIn("Brokk · Fix README typo", section)
        self.assertIn(
            '> Amended by: "Dispatch display labels — role-label '
            'amendment — 2026-07-18"',
            section,
        )

    def test_conventions_persona_section_has_display_layer_only_sentence(self):
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("Personas are display-layer only.", normalized)
        self.assertIn(
            "a persona name never appears where a slug is load-bearing",
            normalized,
        )

    def test_conventions_orn_is_orchestrator_persona(self):
        content = conventions_corpus.corpus_text()
        section = content.split(
            "## Dispatch display labels — persona amendment — 2026-07"
        )[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("örn is the orchestrator persona", normalized)
        self.assertIn("It is not backed by an `agents/*.md` file.", normalized)
        self.assertIn(
            "The kernel introduces itself as örn at the top of session "
            "reports and run charters",
            normalized,
        )

    def test_kernel_introduces_itself_as_orn(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "the session report and the run charter (SYNC, above) open "
            "with the kernel introducing itself as its **örn** persona.",
            normalized,
        )

    def test_kernel_cites_persona_amendment_for_dispatch_labels(self):
        """Evolved by fg-a10213: the kernel's dispatch-label sentence now
        states the `<Persona> (<role>)` format directly (no task id, no
        verb/title tail) and cites the role-label amendment, superseding
        the persona-leads-title phrasing this test used to pin."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            'Any human-visible dispatch label is "<Persona> (<role>)" — no '
            'task id, no verb/title tail (`docs/conventions.md` "Dispatch '
            'display labels" role-label amendment)',
            normalized,
        )

    def test_queue_status_board_cites_persona_slug_format(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "queue" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("`Persona (slug)`", normalized)
        self.assertIn(
            '"Dispatch display labels — persona amendment — 2026-07"',
            normalized,
        )
