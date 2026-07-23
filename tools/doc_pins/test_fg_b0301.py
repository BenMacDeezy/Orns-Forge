"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0301`: TestFgB0301ArchiveTierPins.
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


class TestFgB0301ArchiveTierPins(unittest.TestCase):
    """Doc-pins for fg-b0301 (spec-b71f3a, bm-archive-tier-and-template):
    the ephemeral agent-tier dated conventions section (heading + TOC entry
    + amended-by pointer), the agent template's new `lifecycle:` Provenance
    field, and agent-factory SKILL.md's third-placement scope note.

    Covers all 4 EARS clauses: (1) the dated conventions section defines the
    archive tier's kernel-minted/never-mirrored/never-standing/naming
    properties; (2) agent-template.md's Provenance block carries the
    `lifecycle:` field; (3) agent-factory SKILL.md's "Scope: project-local
    vs. global" section names the archive tier as a third placement; (4)
    this test class itself is the doc-pins clause.
    """

    CONVENTIONS_HEADING = (
        "## Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)"
    )
    CONVENTIONS_TOC_ENTRY = (
        "  - Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)"
    )

    def _read(self, rel_path):
        return _read_path(rel_path)

    def test_conventions_has_dated_heading(self):
        content = self._read("docs/conventions.md")
        self.assertIn(self.CONVENTIONS_HEADING, content)

    def test_conventions_dated_heading_in_toc(self):
        content = self._read("docs/conventions.md")
        self.assertIn(self.CONVENTIONS_TOC_ENTRY, content)

    def test_conventions_base_section_has_amended_by_pointer(self):
        """The ".forge/agents/ (project-local agents)" base section carries
        an "Amended by:" pointer naming the new dated section, directly
        under its own heading — same house style as "Trust boundary"'s
        amended-by pointer."""
        content = self._read("docs/conventions.md")
        self.assertIn(
            '## .forge/agents/ (project-local agents)\n\n'
            '> Amended by: "Ephemeral agent tier — 2026-07-19 '
            '(fg-b0301, spec-b71f3a)"',
            content,
        )

    def test_conventions_section_defines_archive_tier_properties(self):
        """The dated section states the four defining properties: kernel-
        minted via the fast path, never mirrored to .claude/agents/, never
        a standing-team member, and naming per the existing project-local
        convention (never forge-prefixed) — per spec-b71f3a AC-Ephemeral."""
        content = self._read("docs/conventions.md")
        section = content.split(self.CONVENTIONS_HEADING)[1]
        self.assertIn("Kernel-minted, fast path only", section)
        self.assertIn("Never mirrored to `.claude/agents/`", section)
        self.assertIn("Never a standing-team member", section)
        self.assertIn("never prefixed `forge-`", section)
        self.assertIn("spec-b71f3a", section)
        self.assertIn("fg-b0305", section)
        self.assertIn("fg-b0306", section)

    def test_conventions_section_defines_directory_path(self):
        content = self._read("docs/conventions.md")
        section = content.split(self.CONVENTIONS_HEADING)[1]
        self.assertIn("`.forge/agents/archive/\n<name>.md`", section)

    def test_agent_template_has_lifecycle_provenance_field(self):
        """Pins the exact lifecycle-field grammar line (ephemeral | standing)
        alongside the existing four Provenance fields, plus a one-line
        explanation matching the template's inline-comment style (the
        `tools:` frontmatter line's `  — ...` comment convention)."""
        content = self._read(
            "skills/agent-factory/references/agent-template.md"
        )
        self.assertIn(
            "- lifecycle: ephemeral | standing  — ephemeral for fast-path "
            "kernel mints (`.forge/agents/archive/`), standing for "
            "roster/project-local/promoted agents",
            content,
        )
        # Still alongside the pre-existing four fields, not replacing them.
        for field in ("- created:", "- by:", "- rationale:", "- source-task:"):
            self.assertIn(field, content)

    def test_agent_factory_skill_notes_archive_as_third_placement(self):
        """agent-factory SKILL.md's "Scope: project-local vs. global"
        section names the archive tier as a third placement option, citing
        the conventions section rather than restating its definition, and
        explicitly scopes it to kernel fast-path minting only (not
        `/forge:agent`'s human-initiated flow)."""
        content = self._read("skills/agent-factory/SKILL.md")
        section = content.split("## Scope: project-local vs. global")[1]
        section = section.split("## Build the agent")[0]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("Archive (kernel fast-path minting only)", normalized)
        self.assertIn(".forge/agents/archive/<name>.md", normalized)
        self.assertIn(
            "Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)",
            normalized,
        )
        self.assertIn("never targets this tier", normalized)
