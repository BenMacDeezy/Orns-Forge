"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10206`: TestFgA10206ShipFilterPins.
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


class TestFgA10206ShipFilterPins(unittest.TestCase):
    """Doc-pins for fg-a10206 (widen the verifier-finding filter to ship
    judges + Critical-security exploit bar): the amendment heading + TOC
    nesting + Amended-by pointer on the original section, the widened
    ship-judge trigger phrase, the Critical-security exploit-bar sentence
    (including the never-FILTERED fail-safe direction), the legal
    cite-check-only scope limit, and the one citing line in
    skills/ship/SKILL.md's bounce path.
    """

    SECTION_HEADING = (
        "## Ship-judge widening + Critical-security exploit bar — 2026-07-18"
    )

    def test_conventions_has_amendment_section_and_toc_nesting(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.SECTION_HEADING, content)
        self.assertIn(
            "  - Ship-judge widening + Critical-security exploit bar — "
            "2026-07-18",
            content,
        )

    def test_conventions_original_section_has_amended_by_pointer(self):
        content = conventions_corpus.corpus_text()
        original_idx = content.index(
            "## Verifier-finding filter (bounce pre-check) — 2026-07"
        )
        amendment_idx = content.index(self.SECTION_HEADING)
        self.assertLess(
            original_idx, amendment_idx,
            "amendment section must be tail-appended after the original",
        )
        original_section = content[original_idx:amendment_idx]
        self.assertIn(
            '> Amended by: "Ship-judge widening + Critical-security '
            'exploit bar — 2026-07-18"',
            original_section,
        )

    def test_conventions_amendment_has_widened_ship_judge_trigger(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "`forge-reviewer` returns CHANGES REQUESTED, `forge-security` "
            "returns CHANGES REQUESTED, or `forge-legal` returns "
            "BLOCK-RECOMMENDED",
            normalized,
        )
        self.assertIn("the kernel applies the SAME filter defined above", normalized)
        self.assertIn(
            "still counted by `tools/telemetry.py` as the `SHIP: FAIL` "
            "verdict of record",
            normalized,
        )

    def test_conventions_amendment_has_critical_security_exploit_bar(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the cited location existing is insufficient for SURVIVES on "
            "its own",
            normalized,
        )
        self.assertIn(
            "the outcome is CHALLENGED, never FILTERED — fail-safe: doubt "
            "keeps a Critical alive, it never silently dies",
            normalized,
        )

    def test_conventions_amendment_has_legal_cite_check_only_scope(self):
        content = conventions_corpus.corpus_text()
        section = content.split(self.SECTION_HEADING)[1]
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "the kernel verifies ONLY that the cited source (license "
            "text, dependency manifest, third-party notice) exists and "
            "says what the finding claims it says",
            normalized,
        )
        self.assertIn(
            "The kernel never re-judges the underlying legal risk "
            "assessment itself",
            normalized,
        )

    def test_ship_skill_cites_amendment_in_bounce_path(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "ship" / "SKILL.md"))
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            'REVIEW/SECURITY/LEGAL findings pass through the finding '
            'filter before a FAIL becomes a bounce — '
            '`docs/conventions.md`, "Ship-judge widening + '
            'Critical-security exploit bar — 2026-07-18".',
            normalized,
        )
