"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10201`: TestFgA10201VerifierFindingFilterPins.
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


class TestFgA10201VerifierFindingFilterPins(unittest.TestCase):
    """Doc-pins for fg-a10201 (Dex-style verifier-finding filter): the
    canonical dated conventions section (heading, reproduce-on-inspection
    rule, PASS-after-filter honesty sentence, telemetry-counts-it-as-FAIL
    sentence, mem-b82d19 lineage), plus kernel INTEGRATE's citing paragraph
    ahead of the MECHANICAL bounce-routing text.

    Covers all 3 EARS clauses: (1) spot-check-before-bounce with
    reproduce-on-direct-inspection and the SURVIVES/CHALLENGED/FILTERED
    per-finding outcomes; (2) PASS-after-filter recorded in the Attempt log,
    never silently; (3) the rule lives canonically in one dated conventions
    section, cited (not restated) from kernel INTEGRATE, with mem-b82d19
    named as the same discipline.
    """

    SECTION_HEADING = "## Verifier-finding filter (bounce pre-check) — 2026-07"

    def test_conventions_has_section_heading(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)

    def test_conventions_section_in_toc(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "- Verifier-finding filter (bounce pre-check) — 2026-07", content
        )

    def test_conventions_section_has_reproduce_on_inspection_and_outcomes(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the claimed defect must reproduce on direct inspection",
            normalized,
        )
        self.assertIn("**SURVIVES**", normalized)
        self.assertIn("**CHALLENGED**", normalized)
        self.assertIn("**FILTERED**", normalized)
        self.assertIn("never silently dropped", normalized)
        self.assertIn(
            "A bounce dispatches only for surviving findings, quoted",
            normalized,
        )

    def test_conventions_section_has_pass_after_filter_honesty(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("PASS-after-filter", normalized)
        self.assertIn(
            "recorded in the Attempt log with the reason", normalized,
        )
        self.assertIn(
            "full filter rationale", normalized,
        )
        self.assertIn("never silently", normalized)

    def test_conventions_section_has_telemetry_counts_as_fail_sentence(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "a verifier whose\nfindings all filtered is still counted"
            .replace("\n", " "),
            normalized,
        )
        self.assertIn("counted by `tools/telemetry.py` as a FAIL", normalized)

    def test_conventions_section_names_mem_b82d19_lineage(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn("mem-b82d19", normalized)
        self.assertIn(
            "the same discipline applied to verifier", normalized,
        )

    def test_kernel_cites_section_before_mechanical_bounce_routing(self):
        """The filter paragraph cites the conventions section by exact name
        and appears BEFORE the MECHANICAL bounce routing paragraph — filter
        first, then route what survives."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertIn(
            '"Verifier-finding filter (bounce\n  pre-check) — 2026-07"',
            content,
        )
        filter_idx = content.index("Verifier-finding filter.")
        mechanical_idx = content.index("MECHANICAL bounce routing (latency rule).")
        self.assertLess(
            filter_idx, mechanical_idx,
            "filter-before-routing anchor violated: the filter paragraph "
            "must appear before the MECHANICAL bounce routing paragraph",
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("Filter FAIL NOTES first, then route what survives", normalized)

    def test_kernel_skill_within_char_ceiling(self):
        """Sanity pin: kernel SKILL.md must stay under the 31,617-char
        ceiling established by fg-9c0305 (TestFg9c0305Pins) — this task's
        addition must be minimal-touch, not a regression back toward the
        pre-restructure size."""
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertLess(len(content), 31617)
