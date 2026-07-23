"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10212`: TestFgA10212TokenCapturePins.
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


class TestFgA10212TokenCapturePins(unittest.TestCase):
    """fg-a10212: per-spawn token capture in Attempt logs -- an OPTIONAL
    `[tokens: <N>|unreported]` trailing suffix on dispatch/verify/re-verify/
    bounce Attempt-log lines, backward-compatible with every no-suffix line
    that predates it (mirrors JUDGE_YIELD_RE's strict-whole-match
    discipline: a malformed suffix fails the WHOLE line to unparsed, never
    a silent partial parse). Amends "Telemetry vocabulary — 2026-07" via a
    tail-appended dated section, cited (not restated) from the kernel
    skill within its pre-existing char ceiling. Covers all 3 EARS clauses.
    """

    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        # EARS clause 3: dated section, canonical home for the format.
        c = self._norm("docs/conventions.md")
        self.assertIn("## Token capture — 2026-07-19 (fg-a10212)", c)

    def test_toc_lists_the_new_section_nested_under_telemetry_vocabulary(self):
        # TOC entry text must equal the heading verbatim, nested under the
        # base "Telemetry vocabulary — 2026-07" topic it amends.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Telemetry vocabulary — 2026-07 - Token capture — 2026-07-19 "
            "(fg-a10212) - Routing-tuning recommendations",
            c,
        )

    def test_telemetry_vocabulary_has_amended_by_pointer(self):
        # Dated amendment + Amended-by pointer, house pattern (same shape
        # as every other amended-by-name section in this file).
        c = conventions_corpus.corpus_text()
        self.assertIn(
            '## Telemetry vocabulary — 2026-07\n\n'
            '> Amended by: "Token capture — 2026-07-19 (fg-a10212)"',
            c,
        )

    def test_suffix_grammar_documented(self):
        # EARS clause 1: fixed machine-parseable suffix, numeric AND the
        # explicit "unreported" form -- absent data recorded, never omitted
        # or invented.
        c = self._norm("docs/conventions.md")
        self.assertIn("`[tokens: <N>]`", c)
        self.assertIn("`[tokens: unreported]`", c)
        self.assertIn(
            "recorded explicitly, never omitted, never invented", c
        )

    def test_suffix_applies_to_the_four_completion_line_shapes(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "every dispatch / verify / re-verify / bounce Attempt-log line "
            "— the same four shapes that section's \"Attempt log line "
            "shapes\" enumerates — grows an OPTIONAL trailing suffix",
            c,
        )

    def test_backward_compat_and_malformed_discipline_documented(self):
        # EARS clause 1/2: no-suffix lines parse exactly as before; a
        # malformed suffix fails the WHOLE line to unparsed (coverage
        # honesty), mirroring JUDGE_YIELD_RE.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "A line carrying NO suffix at all parses EXACTLY as it did "
            "before this amendment", c,
        )
        self.assertIn(
            "fails the WHOLE line, which falls into the unparsed tally "
            "rather than a silent partial parse — mirroring "
            "JUDGE_YIELD_RE's strict-whole-match discipline exactly", c,
        )

    def test_measured_vs_legacy_estimate_separation_documented(self):
        # EARS clause 2: report/--json fields are clearly labeled MEASURED,
        # never confused with the audit's relative-cost ESTIMATE.
        c = self._norm("docs/conventions.md")
        self.assertIn("measured, never estimated", c)
        self.assertIn(
            "never confused with the audit's relative-weight ESTIMATE "
            "table", c,
        )
        self.assertIn(
            "`tools/telemetry.py` has never computed that estimate and "
            "does not start computing it here", c,
        )

    def test_per_layer_and_per_slug_fields_documented(self):
        # EARS clause 2: build/verify/bounce layers, per-slug totals via
        # the same Routing-record attribution agent_dispatch_counts uses.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "build (dispatch lines), verify (verify + re-verify lines), "
            "bounce (bounce lines) — and per agent-slug", c,
        )
        self.assertIn(
            "using the SAME Routing-record slug attribution "
            "`agent_dispatch_counts` already applies", c,
        )

    def test_kernel_cites_the_amendment_by_name(self):
        # EARS clause 3: kernel skill cites the dated amendment by name
        # (cite-don't-restate) rather than re-deriving the suffix grammar.
        content = self._norm("skills/kernel/SKILL.md")
        self.assertIn(
            'judge-yield lines and a per-completion `[tokens]` suffix in '
            'the Attempt log ("Token capture — 2026-07-19")', content,
        )

    def test_kernel_skill_within_char_ceiling(self):
        # Hard ceiling from the task contract: the kernel file must stay
        # under the pre-existing 31,617-char budget after displacement.
        content = _cached_read_text(self.KERNEL_PATH)
        self.assertLessEqual(len(content), self.CHAR_CEILING)
