"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10901`: TestFgA10901VerificationEconomicsPins.
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


class TestFgA10901VerificationEconomicsPins(unittest.TestCase):
    """Covers fg-a10901's EARS clauses (constitution rule 3): the
    verification-economics policy prose is NORMATIVE protocol, so its
    load-bearing sentences are pinned — a future edit cannot silently drop
    a security trigger, re-serialize dispatch behind verify, or resurrect
    per-task panels without a failing test.
    """

    # The seven named Aegis triggers (docs/conventions.md, "Verification
    # economics — 2026-07-18"). Keyword fragments, not full sentences, so
    # per-file phrasing/separators may differ while the LIST cannot.
    TRIGGERS = [
        "cookie/storage write",
        "raw-HTML",
        "auth/token/",
        "form/redirect",
        "untrusted",
        "new dependency",
        "money/payment",
    ]

    @staticmethod
    def _norm(path):
        # collapse whitespace so pins survive line-wrap changes
        text = _read_path(path)
        return " ".join(text.split())

    def test_conventions_section_exists_and_keeps_the_floor(self):
        c = self._norm("docs/conventions.md")
        self.assertIn("## Verification economics — 2026-07-18 (fg-a10901)", c)
        self.assertIn("no task integrates UNVERIFIED", c)
        self.assertIn("gates-inline with zero spawned verifiers", c)

    def test_named_trigger_list_identical_across_all_three_surfaces(self):
        # EARS clause 3 (Aegis): conventions, the agent brief, and ship
        # step 5 must all carry every trigger — no surface may drift.
        for path in (
            "docs/conventions.md",
            "agents/forge-security.md",
            "skills/ship/SKILL.md",
        ):
            content = self._norm(path)
            for trig in self.TRIGGERS:
                self.assertIn(
                    trig, content,
                    f"{path} lost the named security trigger {trig!r}",
                )
        self.assertIn("no named trigger", self._norm("skills/ship/SKILL.md"))

    def test_pipelining_gates_integrate_never_dispatch(self):
        # EARS clause 1: both the kernel stub and the reference mechanics.
        self.assertIn(
            "verification gates INTEGRATE, never the next dispatch",
            self._norm("skills/kernel/SKILL.md"),
        )
        ref = self._norm("skills/kernel/references/parallel-dispatch.md")
        self.assertIn("Build-ahead pipelining (fg-a10901)", ref)
        self.assertIn("Verification gates INTEGRATE, never the next dispatch", ref)
        self.assertIn("rework exposure is judged, not assumed clean", ref)

    def test_wave_end_failure_is_merge_gate_and_composes_with_atomic_shards(self):
        # EARS clause 5.
        c = self._norm("docs/conventions.md")
        self.assertIn("merge-gate failure", c)
        self.assertIn("re-verified, not silently shipped", c)
        self.assertIn("batch-invert rule applies", c)

    def test_delta_only_bounce_reverify(self):
        # EARS clause 6.
        self.assertIn("never a fresh full panel", self._norm("docs/conventions.md"))

    def test_single_re_derivation_owner(self):
        # EARS clause 7: policy + the reviewer consuming, not recomputing.
        self.assertIn("ONE re-derivation owner", self._norm("docs/conventions.md"))
        self.assertIn(
            "do not re-derive the whole table", self._norm("agents/forge-reviewer.md")
        )

    def test_wave_end_rook_with_full_tier_exception(self):
        # EARS clause 3 (Rook).
        c = self._norm("docs/conventions.md")
        self.assertIn("wave-end, not per-task", c)
        self.assertIn("keep the per-task reviewer", c)
        self.assertIn("wave-end by default", self._norm("agents/forge-reviewer.md"))

    def test_contract_first_decomposition_in_spec_skill(self):
        # EARS clause 2.
        self.assertIn(
            "Contract-first decomposition (fg-a10901)", self._norm("skills/spec/SKILL.md")
        )
