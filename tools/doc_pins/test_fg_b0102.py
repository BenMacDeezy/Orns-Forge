"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-b0102`: TestFgB0102CustomizationPersistenceDocPagePins.
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


class TestFgB0102CustomizationPersistenceDocPagePins(unittest.TestCase):
    """Pin tests for fg-b0102: docs/customization-persistence.md's one
    storage-tier table, plus its cross-links from README.md and
    docs/architecture.md's Subsystems index (spec-4d2a AC, "customization-
    persistence doc page")."""

    DOC_PATH = REPO_ROOT / "docs" / "customization-persistence.md"
    README_PATH = REPO_ROOT / "README.md"
    ARCHITECTURE_PATH = REPO_ROOT / "docs" / "architecture.md"

    @staticmethod
    def _norm(path):
        return " ".join(_cached_read_text(path).split())

    def test_doc_page_exists(self):
        self.assertTrue(self.DOC_PATH.is_file())

    def test_cites_fg_b0101_contract_not_restated(self):
        c = self._norm(self.DOC_PATH)
        self.assertIn(
            "Customization persistence contract — 2026-07-18 (fg-b0101)", c
        )
        self.assertIn("docs/conventions/config-and-features.md", c)

    def test_table_has_required_columns(self):
        c = self._norm(self.DOC_PATH)
        self.assertIn("| Surface | Storage tier | Update-survival guarantee", c)

    def test_table_covers_every_ac12_named_surface(self):
        """AC (`.forge/queue/tasks/fg-b0102-persistence-doc-page.md`) names
        eight surfaces explicitly; every one must have a row."""
        c = self._norm(self.DOC_PATH)
        for surface in (
            "Operator profiles",
            "Provider profiles",
            "Ported agents",
            "Project-local agents",
            "Project memory",
            "| Queue |",
            "| Specs |",
            "Project-local skills",
        ):
            self.assertIn(surface, c, f"missing table row for {surface!r}")

    def test_table_covers_brief_named_extras(self):
        c = self._norm(self.DOC_PATH)
        for surface in (
            "Provider trust markers",
            "Craft memory",
            "`forge.md` config",
            "Banner launcher shim",
        ):
            self.assertIn(surface, c, f"missing table row for {surface!r}")

    def test_table_covers_constitution_and_project_charter(self):
        """Bounce fix (fg-b0102 verifier, P2): the table missed two real
        shipped project-space surfaces documented in
        docs/conventions/artifact-formats.md — constitution.md and
        project.md."""
        c = self._norm(self.DOC_PATH)
        self.assertIn("Constitution", c)
        self.assertIn(".forge/constitution.md", c)
        self.assertIn("Edit freely: add project rules below", c)
        self.assertIn("Project charter", c)
        self.assertIn(".forge/project.md", c)
        self.assertIn("never clobbered once it exists", c)

    def test_constitution_row_matches_repo_reality(self):
        """The constitution row claims .forge/constitution.md exists on
        disk in this repo today -- pin that claim against the actual file."""
        self.assertTrue(
            (REPO_ROOT / ".forge" / "constitution.md").is_file(),
            "docs/customization-persistence.md's Constitution row says "
            "'exists on disk in this repo today' -- but it doesn't anymore; "
            "update the row.",
        )

    def test_project_charter_row_matches_repo_reality(self):
        """The project-charter row claims .forge/project.md does NOT exist
        in this repo as of this page -- pin that claim too, so the row gets
        flipped to 'instantiated' if a future session runs /forge:discover."""
        self.assertFalse(
            (REPO_ROOT / ".forge" / "project.md").exists(),
            "docs/customization-persistence.md's Project charter row says "
            "'.forge/project.md does not exist as of this page' -- but it "
            "now does; update the row's Status cell.",
        )

    def test_scope_note_addresses_map_and_queue_exclusions(self):
        """Bounce fix: a completeness self-sweep of artifact-formats.md's
        section list must explain, not silently omit, any human-editable
        artifact excluded from the table (e.g. .forge/map/ curation,
        per-task frontmatter fields already covered by the Queue row)."""
        c = self._norm(self.DOC_PATH)
        self.assertIn("Scope note: what this table deliberately excludes", c)
        self.assertIn(".forge/map/", c)
        self.assertIn("Queue task files", c)

    def test_not_yet_shipped_rows_say_so_not_present_tense(self):
        # 2026-07-20 (fg-b0203 retro-verify): both formerly not-yet-shipped
        # rows (operator profiles fg-b0103/b0104, ported agents fg-b0203)
        # flipped to Shipped when their tasks closed -- this pin's job was
        # to force exactly that flip. It now pins the shipped wording.
        c = self._norm(self.DOC_PATH)
        self.assertNotIn("**Not yet shipped**", c)  # bolded row marker only; the unbolded legend sentence at the top legitimately remains
        self.assertIn("`commands/port.md` (`fg-b0203`, `state: done`)", c)
        self.assertIn("`fg-b0103`/`fg-b0104` (container format + kernel wiring) are `state: done`", c)
        # The operator-profile row must not claim .forge/profiles/ exists today.
        self.assertFalse(
            (REPO_ROOT / ".forge" / "profiles").exists(),
            "docs/customization-persistence.md marks .forge/profiles/ as "
            "not-yet-shipped, but the directory now exists on disk — the "
            "doc page needs to flip that row to Shipped.",
        )

    def test_every_tier_used_is_one_of_the_three_contract_tiers(self):
        c = _cached_read_text(self.DOC_PATH)
        rows = [
            line for line in c.splitlines()
            if line.startswith("|") and "---" not in line
            and not line.startswith("| Surface")
        ]
        self.assertGreater(len(rows), 5)
        joined = " ".join(rows)
        # Every content row's tier cell names one of the three tiers verbatim
        # (Plugin cache / User space / Project space), matching fg-b0101's
        # own tier names exactly.
        for tier in ("Project space", "User space", "Plugin cache"):
            self.assertIn(tier, joined)

    def test_validate_persistence_boundary_gate_referenced(self):
        c = self._norm(self.DOC_PATH)
        self.assertIn("tools/validate_persistence_boundary.py", c)

    def test_linked_from_readme_reference_section(self):
        c = self._norm(self.README_PATH)
        self.assertIn(
            "[`docs/customization-persistence.md`](docs/customization-persistence.md)",
            c,
        )

    def test_linked_from_readme_depth_paragraph(self):
        c = self._norm(self.README_PATH)
        self.assertIn(
            "[customization-persistence table](docs/customization-persistence.md)",
            c,
        )

    def test_linked_from_architecture_subsystems_index(self):
        c = self._norm(self.ARCHITECTURE_PATH)
        self.assertIn(
            "[Customization persistence](customization-persistence.md)", c
        )
        self.assertIn("**Customization persistence**", c)
