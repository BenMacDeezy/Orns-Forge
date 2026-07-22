"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10911`: TestFgA10911SeverityConfidencePins.
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


class TestFgA10911SeverityConfidencePins(unittest.TestCase):
    """fg-a10911: P0-P3 severity + confidence per judge finding (oh-my-pi
    steal, scout three-harness audit steal-list item 3) — REQUIRED
    output-contract fields alongside (not replacing) the existing
    MECHANICAL/JUDGMENT tag and each judge's Critical/Important/Minor
    vocabulary, a coherent finding-filter amendment (never-FILTERED-on-
    spot-check-alone for P0/high, never-alone-bounces for P3/low, severity
    is the judge's call), the backward-compatible judge-yield telemetry
    extension, and the dated conventions section + TOC entry."""

    @staticmethod
    def _norm(path):
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_is_dated(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "## Finding severity + confidence — 2026-07-18 (fg-a10911)", c
        )

    def test_toc_lists_the_new_section(self):
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "- Finding severity + confidence — 2026-07-18 (fg-a10911)", c
        )

    def test_output_contract_fields_pinned_in_forge_verifier(self):
        v = self._norm("agents/forge-verifier.md")
        self.assertIn(
            "FAIL NOTES: <if FAIL: P0|P1|P2|P3 confidence: "
            "high|medium|low — MECHANICAL | JUDGMENT — precisely what the "
            "worker must change — or omit>",
            v,
        )

    def test_output_contract_fields_pinned_in_forge_reviewer(self):
        r = self._norm("agents/forge-reviewer.md")
        self.assertIn(
            "- [Critical|Important|Minor] P0|P1|P2|P3 confidence: "
            "high|medium|low — <file:line> — <defect> — <failure scenario: "
            "how it breaks>",
            r,
        )

    def test_output_contract_fields_pinned_in_forge_security(self):
        s = self._norm("agents/forge-security.md")
        self.assertIn(
            "- [Critical|Important|Minor] P0|P1|P2|P3 confidence: "
            "high|medium|low — <file:line> — <vulnerability> — <exploit "
            "scenario>",
            s,
        )

    def test_never_filtered_on_spot_check_alone_rule(self):
        # EARS clause 2 (a): P0/high is never FILTERED on a spot-check
        # alone -- it gets a real re-check first.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "P0/high is never FILTERED on a spot-check alone", c
        )
        self.assertIn(
            "the kernel must complete a REAL re-check first", c
        )
        self.assertIn(
            "when the re-check is inconclusive, the outcome is CHALLENGED, "
            "never FILTERED", c,
        )

    def test_p3_low_never_alone_bounces_rule(self):
        # EARS clause 2 (b): P3/low findings never alone cause a bounce --
        # crisp rule stated with the exact disjunct.
        c = self._norm("docs/conventions.md")
        self.assertIn("P3/low never alone bounces", c)
        self.assertIn(
            "a bounce requires at least one SURVIVING finding that is "
            "EITHER severity `P0`, `P1`, or `P2` (any confidence), OR "
            "JUDGMENT-tagged with `confidence: medium` or `high` at ANY "
            "P-level",
            c,
        )

    def test_severity_is_judges_call_not_downgradable_rule(self):
        # EARS clause 2 (c): severity is the judge's call, the filter may
        # not downgrade it -- it may only FILTER with evidence.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "Severity is the judge's call; the filter never downgrades it",
            c,
        )
        self.assertIn(
            "the kernel's spot-check filter may change a finding's OUTCOME "
            "(SURVIVES/CHALLENGED/FILTERED, per the existing "
            "per-finding-outcome rules) but never its stated severity or "
            "confidence",
            c,
        )

    def test_telemetry_extension_documented_backward_compatibly(self):
        # EARS clause 3: judge-yield telemetry carries severity counts,
        # parser updated in the same change, backward compatible.
        c = self._norm("docs/conventions.md")
        self.assertIn(
            "extends BACKWARD-COMPATIBLY with an optional trailing suffix "
            "`p0=A p1=B p2=C p3=D`",
            c,
        )
        self.assertIn(
            "The base shape with no suffix still parses exactly as it "
            "always has",
            c,
        )
        self.assertIn(
            "fails the WHOLE line, which falls into the unparsed tally "
            "rather than a silent partial parse",
            c,
        )
