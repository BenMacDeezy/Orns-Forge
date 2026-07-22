"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10602`: TestFgA10602IrisDesignConformancePins.
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


class TestFgA10602IrisDesignConformancePins(unittest.TestCase):
    """Doc-pins for fg-a10602 (Iris design-conformance check): extends
    `agents/forge-ui-verifier.md`'s output contract so a foundation-exists
    verify checks conformance through the normal verdict + finding-filter
    path, a no-foundation verify neither hard-fails nor silent-passes but
    elevates 2-3 proposed directions to the human, and the whole thing stays
    proportionate — elevate/propose, no bounce-loop on subjective taste,
    human's chosen direction is the arbiter, Iris judges application only.
    docs/conventions.md gets one APPENDED dated section (with TOC entry)
    describing the elevation as a human question channel, not a bounce.

    Covers all 3 EARS clauses in fg-a10602-iris-design-conformance.md:
    (1) foundation exists -> conformance check, real finding, normal path;
    (2) no foundation -> not hard-fail, not silent-pass, elevate 2-3
    directions; (3) proportionate — elevate/propose, human direction is
    arbiter, Iris never imposes her own.
    """

    VERIFIER_PATH = REPO_ROOT / "agents" / "forge-ui-verifier.md"
    CONVENTIONS_SECTION_HEADING = (
        "## Design-conformance elevation (Iris) — 2026-07-18"
    )

    def _verifier_text(self):
        return _cached_read_text(self.VERIFIER_PATH)

    def _conventions_section(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(self.CONVENTIONS_SECTION_HEADING, content)
        return content.split(self.CONVENTIONS_SECTION_HEADING, 1)[1]

    # --- EARS clause 1: foundation exists -> conformance check, real
    # finding, normal verdict + finding-filter path -------------------

    def test_verifier_has_design_conformance_section(self):
        content = self._verifier_text()
        self.assertIn("## Design conformance", content)

    def test_verifier_checks_conformance_when_foundation_exists(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "WHEN the project has `.forge/design/foundation.md`", normalized
        )
        self.assertIn(
            "check the rendered output against it as part of the "
            "acceptance bar", normalized,
        )
        self.assertIn(
            "do the foundation's tokens, visual identity, and layout "
            "language actually show up", normalized,
        )

    def test_verifier_conformance_gap_is_real_finding_not_silent_pass(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "A conformance gap is a real finding — run it through the same "
            "MECHANICAL/JUDGMENT tag discipline as any other defect",
            normalized,
        )
        self.assertIn("never fold it away as a silent pass", normalized)

    def test_output_contract_has_design_conformance_field(self):
        content = self._verifier_text()
        self.assertIn(
            "DESIGN CONFORMANCE: <foundation exists → tokens/identity/"
            "layout applied vs bare defaults, findings folded into FAIL "
            "NOTES like any other defect | no foundation → see ELEVATION>",
            content,
        )

    def test_verdict_fail_list_includes_conformance_gap(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "a design-conformance gap against an established foundation, "
            "or a constitution `no` = VERDICT: FAIL", normalized,
        )

    # --- EARS clause 2: no foundation -> not hard-fail, not silent-pass,
    # elevate 2-3 directions -------------------------------------------

    def test_verifier_elevates_when_no_foundation(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("WHEN no foundation file exists", normalized)
        self.assertIn("do not hard-fail the task for it", normalized)
        self.assertIn("do not silently pass over the gap", normalized)
        self.assertIn(
            "propose 2-3 concrete design directions derived from the "
            "project's concept", normalized,
        )
        self.assertIn(
            "framed as a question for the human", normalized,
        )

    def test_output_contract_has_elevation_field(self):
        content = self._verifier_text()
        self.assertIn(
            "ELEVATION: <no foundation exists → 2-3 concrete design "
            "directions proposed from the project concept, framed as a "
            "question for the human, never a task bounce | foundation "
            "exists → n/a>",
            content,
        )

    def test_missing_foundation_never_drives_verdict_alone(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn("A missing foundation never drives VERDICT on its own", normalized)
        self.assertIn(
            "A missing foundation file is never, by itself, a FAIL — it "
            "drives ELEVATION instead", normalized,
        )

    # --- EARS clause 3: proportionate — elevate/propose, no bounce-loop,
    # human direction is arbiter, Iris judges application only ---------

    def test_verifier_states_proportionality_no_bounce_loop(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Keep this proportionate: elevate and propose, never "
            "bounce-loop the task on subjective taste", normalized,
        )

    def test_verifier_states_human_direction_is_arbiter(self):
        content = self._verifier_text()
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "Once a foundation exists, the human's chosen direction is "
            "the arbiter", normalized,
        )
        self.assertIn(
            "judge only whether the shipped work APPLIES that direction",
            normalized,
        )
        self.assertIn(
            "never fail work for missing a direction of your own that no "
            "human chose", normalized,
        )

    # --- Wording-constraint guard: ui-behavior-correctness must stay a
    # single occurrence in forge-ui-verifier.md (pinned by
    # tools/test_pins_ui_behavior.py); this task must not add a second. --

    def test_ui_behavior_correctness_still_exactly_one_occurrence(self):
        content = self._verifier_text()
        self.assertEqual(content.count("ui-behavior-correctness"), 1)

    # --- Elevation surfaces as a human question channel, not a bounce --

    def test_conventions_has_toc_entry(self):
        content = conventions_corpus.corpus_text()
        self.assertIn(
            "- Design-conformance elevation (Iris) — 2026-07-18", content
        )

    def test_conventions_section_describes_human_question_not_bounce(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "The channel is a human question, not a bounce-loop.",
            normalized,
        )
        self.assertIn(
            "it is a decision only a human can make, so the kernel "
            "surfaces Iris's proposed directions to the human the same "
            "way any other Forge decision point asks one",
            normalized,
        )
        self.assertIn(
            "ELEVATION is not a task-level defect the kernel routes back "
            "to the worker for a redo", normalized,
        )
        self.assertIn(
            "The task's own verdict and integration proceed independently "
            "of when or whether that question gets answered", normalized,
        )

    def test_conventions_section_ties_conformance_path_to_normal_verdict(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "can drive VERDICT: FAIL through the normal path — no "
            "separate design-only failure mode, no silent pass",
            normalized,
        )

    def test_conventions_section_states_proportionality(self):
        section = self._conventions_section()
        normalized = re.sub(r"\s+", " ", section)
        self.assertIn(
            "This is elevate-and-propose, never a bounce-loop on "
            "subjective taste", normalized,
        )
        self.assertIn(
            "the human's chosen direction is the sole arbiter", normalized,
        )
