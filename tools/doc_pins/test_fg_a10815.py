"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10815`: TestFgA10815ShardMergeVerifyPins.
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


class TestFgA10815ShardMergeVerifyPins(unittest.TestCase):
    """Doc-pins for fg-a10815 (T4b): the "Shard merge, verify, bisect,
    atomicity" subsection added to skills/kernel/references/parallel-
    dispatch.md -- the judgment-heavy safety half of the sharded fan-out
    epic (fg-a10801). Covers all 4 EARS clauses (merge/conflict-bounce,
    verify-model tied to the Low-risk predicate, bisect + coupling
    misattribution, INTEGRATE atomicity), the refuter revisions R-D4a,
    R-D4b, and R-D7 (fg-a10801, "Refuter verdict + kernel reconciliation"),
    the fg-a10801 EARS clause-2 reconciliation, Grud/grunt inheritance, and
    a cross-doc integrity pin against the Low-risk verification predicate
    section this task ties skip-verify to. Does NOT touch dispatch/
    expansion semantics (fg-a10814/T4a) -- that section is untouched by
    this task.
    """

    REF_PATH = (
        REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
    )
    CONVENTIONS_PATH = REPO_ROOT / "docs" / "conventions.md"

    SECTION_HEADING = "## Shard merge, verify, bisect, atomicity (fg-a10815)"

    def _section(self):
        content = _cached_read_text(self.REF_PATH)
        self.assertIn(
            self.SECTION_HEADING, content,
            "parallel-dispatch.md is missing the fg-a10815 'Shard merge, "
            "verify, bisect, atomicity' section",
        )
        return content.split(self.SECTION_HEADING, 1)[1]

    def _normalized_section(self):
        return re.sub(r"\s+", " ", self._section())

    def _low_risk_predicate_section(self):
        content = _read_path(self.CONVENTIONS_PATH)
        heading = "## Low-risk verification (standard sub-class) — 2026-07"
        self.assertIn(
            heading, content,
            "docs/conventions.md is missing the Low-risk verification "
            "predicate section this task ties skip-verify to",
        )
        rest = content.split(heading, 1)[1]
        return rest.split("\n## ", 1)[0]

    def _normalized_low_risk_predicate_section(self):
        return re.sub(r"\s+", " ", self._low_risk_predicate_section())

    def test_forward_pointer_still_resolves(self):
        """The fg-a10814 forward-pointer line ("see merge/verify contract
        in fg-a10815 (T4b)") now resolves to a real section immediately
        after it -- this task fulfills that pointer without editing it."""
        content = _cached_read_text(self.REF_PATH)
        self.assertIn(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)",
            content,
        )
        pointer_idx = content.index(
            "Shards complete → see merge/verify contract in fg-a10815 (T4b)"
        )
        section_idx = content.index(self.SECTION_HEADING)
        self.assertLess(
            pointer_idx, section_idx,
            "fg-a10815 section must come AFTER the fg-a10814 forward "
            "pointer that names it",
        )

    def test_merge_conflict_bounce_is_verbatim_reuse(self):
        """EARS clause 1: disjoint outputs merge with a conflict CHECK; a
        surprise conflict bounces to blocked, never speculatively resolved
        -- verbatim reuse of the wave conflict-bounce, cited by name."""
        normalized = self._normalized_section()
        self.assertIn("**verbatim reuse**", normalized)
        self.assertIn("do not resolve speculatively", normalized)
        self.assertIn("NEVER", normalized)
        self.assertIn("`blocked`", normalized)
        self.assertIn("INTEGRATE — Parallel batch", normalized)
        self.assertIn("**Merge conflict:**", normalized)

    def test_verify_model_tied_to_low_risk_predicate_not_blanket(self):
        """EARS clause 2 / R-D4a: skip-verify is tied to the EXISTING
        Low-risk predicate, never a blanket mechanical->optional rule."""
        normalized = self._normalized_section()
        self.assertIn(
            "every EARS clause pin-covered, no protocol-file touch, gates "
            "cover the change", normalized,
        )
        self.assertIn(
            "Low-risk verification (standard sub-class) — 2026-07", normalized,
        )
        self.assertIn("**NEVER** a", normalized)
        self.assertIn(
            'blanket "mechanical work → optional verify" rule', normalized,
        )

    def test_gates_green_counterexample(self):
        """EARS clause 2: the canonical rename-X->Y-deletes-X counterexample
        -- gates green because nothing references it, criterion unmet."""
        normalized = self._normalized_section()
        self.assertIn("Gates-green ≠ acceptance-met", normalized)
        self.assertIn("mechanical rename", normalized)
        self.assertIn("instead *deletes* `X`", normalized)
        self.assertIn("passes every gate green", normalized)
        self.assertIn('"rename X to Y") is unmet', normalized)

    def test_verify_mode_per_shard_or_merged_when_predicate_unmet(self):
        """EARS clause 2: when the predicate is not satisfied, an
        EARS-clause verifier runs -- per-shard for disjoint outputs, or
        once over the merged result -- with when each applies stated."""
        normalized = self._normalized_section()
        self.assertIn("not fully satisfied**, an EARS-clause verifier", normalized)
        self.assertIn("**per-shard** for disjoint outputs", normalized)
        self.assertIn("**once over the merged result**", normalized)

    def test_grud_shards_inherit_rule_explicitly(self):
        """Grud/grunt shards inherit the verify-model rule explicitly --
        no looser bar for a mechanical-tier slug (closes the D4a/D8 hole
        the parent task names)."""
        normalized = self._normalized_section()
        self.assertIn("Grud/grunt", normalized)
        self.assertIn("**inherit this rule explicitly**", normalized)
        self.assertIn("mechanical-tier slug does not", normalized)

    def test_clause2_reconciliation_modes_not_free_choice(self):
        """Reconciles fg-a10801 EARS clause 2 ("per-shard for disjoint
        outputs, or once over the merged result") against this task's
        verify model: the two options are modes selected by the Low-risk
        predicate, not a free choice."""
        normalized = self._normalized_section()
        self.assertIn(
            '"per-shard for disjoint outputs, or once over the merged '
            'result"', normalized,
        )
        self.assertIn(
            "**modes selected by the Low-risk predicate above, not a "
            "free choice**", normalized,
        )
        self.assertIn(
            "disjoint-output shard-sets **MAY** verify once-over-merged "
            "**ONLY** under the Low-risk predicate", normalized,
        )

    def test_bisect_coupling_misattribution(self):
        """EARS clause 3 / R-D4b: cross-slice coupling causes bisect to
        blame the last-merged slice; re-dispatch reproduces the failure;
        the 2nd failure blocks the WHOLE task, pointing at the slice SET."""
        normalized = self._normalized_section()
        self.assertIn("**cross-slice coupling**", normalized)
        self.assertIn("blames the **last-merged slice**", normalized)
        self.assertIn("**reproduces the failure**", normalized)
        self.assertIn("slice's **2nd failure**", normalized)
        self.assertIn("**WHOLE task blocks**", normalized)
        self.assertIn("**coupling-shaped, not slice-local**", normalized)
        self.assertIn("**slice SET**", normalized)

    def test_bisect_composes_with_eligibility_restriction(self):
        """States why coupling misattribution composes with the v1
        shard-by:files eligibility restriction (textually-clean-but-
        semantically-broken coupling is what that restriction guards)."""
        normalized = self._normalized_section()
        self.assertIn("Shard-eligibility predicate", normalized)
        self.assertIn("**textually-clean-but-semantically-broken**", normalized)
        self.assertIn("per-file-local", normalized)

    def test_atomicity_inversion_stated_explicitly(self):
        """EARS clause 4 / R-D7: shard INTEGRATE is ATOMIC for the task,
        explicitly inverting the reused parallel-batch INTEGRATE rule."""
        normalized = self._normalized_section()
        self.assertIn("a batch is not an all-or-nothing unit", normalized)
        self.assertIn("**Shard INTEGRATE inverts that rule.**", normalized)
        self.assertIn("INTEGRATE is **ATOMIC for the", normalized)
        self.assertIn(
            "whole task is done, or the whole task is blocked", normalized,
        )
        self.assertIn(
            "one deliverable in pieces", normalized,
        )

    def test_integrate_stub_must_cite_this_section(self):
        """R-D7: the kernel's new shard INTEGRATE stub (fg-a10816) must
        cite THIS section, not the batch-INTEGRATE stub, for shards."""
        normalized = self._normalized_section()
        self.assertIn("fg-a10816", normalized)
        self.assertIn("**MUST", normalized)
        self.assertIn("cite THIS section**", normalized)
        self.assertIn("not the batch-INTEGRATE stub", normalized)

    def test_low_risk_predicate_cited_verbatim_matches_conventions(self):
        """Cross-doc integrity pin (behavioral-adjacent): the Low-risk
        verification predicate bullets this section cites must actually
        exist, character-for-character, in docs/conventions.md's Low-risk
        verification section -- red if either doc's wording drifts out of
        sync with the other."""
        predicate_section = self._normalized_low_risk_predicate_section()
        our_section = self._normalized_section()

        quoted_bullets = [
            "docs/config-only, zero runtime-behavior change",
            "Every EARS clause is covered by a passing pin or regression "
            "test",
            "touches NONE of `skills/`, `agents/`, `hooks/`, `workflows/`, "
            "or `.forge/` protocol files",
        ]
        for bullet in quoted_bullets:
            self.assertIn(
                bullet, predicate_section,
                f"docs/conventions.md Low-risk verification section no "
                f"longer contains the bullet this task cites verbatim: "
                f"{bullet!r}",
            )
            self.assertIn(
                bullet, our_section,
                f"parallel-dispatch.md fg-a10815 section no longer cites "
                f"the conventions.md predicate bullet verbatim: {bullet!r}",
            )
