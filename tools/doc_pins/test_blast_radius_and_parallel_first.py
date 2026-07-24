"""Doc-pins for the 2026-07-23 owner-directed pair: the blast-radius gate
(mode-1 widening, so not every standard task pays a verifier spawn) and
parallel-first dispatch (parallel is the default, sequential needs a
reason). Both were prompted by a live session that ran sequentially and
spawned a full verifier per task; these pins exist so the kernel cannot
drift back to either behavior without a deliberate edit.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO_ROOT,
    _cached_read_text,
    conventions_corpus,
)

KERNEL = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
VERIFY_MODES = REPO_ROOT / "skills" / "kernel" / "references" / "verify-modes.md"


def _norm(text):
    # collapse whitespace so pins survive line-wrap changes
    return " ".join(text.split())


class TestBlastRadiusGate(unittest.TestCase):
    def test_conventions_section_exists_and_is_dated(self):
        self.assertIn(
            "## Blast-radius gate — 2026-07-23 (owner-directed)",
            conventions_corpus.corpus_text(),
        )

    def test_kernel_mode_1_is_no_longer_trivial_only(self):
        # The whole point: a standard-tier task can now reach gates-inline.
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("Gates-inline (trivial tier, or a standard task", k)
        self.assertIn("blast-radius", k)
        self.assertIn("references/verify-modes.md", k)

    def test_reference_enumerates_all_five_tests(self):
        v = _norm(_cached_read_text(VERIFY_MODES))
        self.assertIn("Blast-radius gate (mode-1 widening)", v)
        self.assertIn("passes ALL FIVE of the tests", v)
        for marker in ("(a) **Gate-covered.**",
                       "(b) **No new behavior or contract.**",
                       "(c) **No sensitive surface.**",
                       "(d) **Not visual.**",
                       "(e) **First attempt.**"):
            self.assertIn(_norm(marker), v, marker)

    def test_full_tier_never_qualifies(self):
        # tier: full must keep shipping through the full protocol -- the
        # spec-approval gate is not what this change was loosening.
        v = _norm(_cached_read_text(VERIFY_MODES))
        self.assertIn("`tier: full` NEVER qualifies", v)
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("`tier: full` NEVER qualifies", c)

    def test_hard_rule_3_is_explicitly_preserved(self):
        # Mode 1 is the KERNEL running gates, not the worker checking itself.
        # If that ever inverts, the gate becomes self-verification.
        v = _norm(_cached_read_text(VERIFY_MODES))
        self.assertIn("The kernel runs the gates, never the worker", v)
        self.assertIn("the worker never verifies its own work", v)

    def test_uncertainty_disqualifies(self):
        # Whitelist semantics: the failure mode of a "judgment call" gate is
        # that it silently widens until it swallows everything.
        v = _norm(_cached_read_text(VERIFY_MODES))
        self.assertIn("is uncertain rather than clearly true, the task does "
                      "NOT qualify", v)

    def test_sampling_audit_is_pinned(self):
        v = _norm(_cached_read_text(VERIFY_MODES))
        self.assertIn("After 6 consecutive blast-radius-clear completions", v)
        self.assertIn("sampling audit", v)


class TestParallelFirstDispatch(unittest.TestCase):
    def test_conventions_section_exists_and_is_dated(self):
        self.assertIn(
            "## Parallel-first dispatch — 2026-07-23 (owner-directed)",
            conventions_corpus.corpus_text(),
        )

    def test_kernel_gate_defaults_to_parallel(self):
        k = _norm(_cached_read_text(KERNEL))
        self.assertIn("Parallel is the DEFAULT when the eligibility test", k)
        self.assertIn("sequential/inline needs a stated reason", k)

    def test_kernel_gate_no_longer_lists_parallelism_as_a_delegate_criterion(self):
        # Parallelism is decided BEFORE inline-vs-delegate now, so keeping it
        # as one of the delegate criteria would re-create the old ordering
        # where the gate nudges toward inline first.
        k = _norm(_cached_read_text(KERNEL))
        self.assertNotIn("genuine parallelism exists", k)

    def test_kernel_states_the_auto_default_not_three(self):
        # The stale "default 3" was the concrete reason the kernel under-
        # dispatched: it read its own doc and sized batches to 3.
        k = _norm(_cached_read_text(KERNEL))
        self.assertNotIn("max-parallel-tasks` (forge.md, default 3)", k)
        self.assertIn("default `auto` = `min(cores-2, 16)`", k)
        self.assertIn("a batch of 2-3 is a floor, not a target", k)

    def test_conventions_supersede_every_stale_default_three(self):
        c = _norm(conventions_corpus.corpus_text())
        self.assertIn("Supersedes every \"default 3\"", c)


if __name__ == "__main__":
    unittest.main()
