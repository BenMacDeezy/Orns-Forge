"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-a10816`: TestFgA10816KernelStubPins.
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


class TestFgA10816KernelStubPins(unittest.TestCase):
    """Doc-pins for fg-a10816 (T5, final task of the fg-a10801 sharded
    fan-out epic): the THREE kernel citation stub sites
    skills/kernel/SKILL.md carries for sharding -- GATE (shard-eligibility
    predicate, docs/conventions.md "Sharded fan-out"), DISPATCH (shard
    expansion, parallel-dispatch.md fg-a10814), and the NEW INTEGRATE stub
    (R-D7: shard INTEGRATE is ATOMIC for the task, parallel-dispatch.md
    fg-a10815) -- plus the three-stub-site structural invariant, the
    pre-existing char-ceiling pin this task's additions had to fit under,
    and the len()-not-wc-bytes measurement caveat (EARS clause 2). Does NOT
    touch conventions.md or parallel-dispatch.md content (fg-a10813/814/815
    own that); this task only wires + pins the kernel-side citations.
    """

    KERNEL_PATH = REPO_ROOT / "skills" / "kernel" / "SKILL.md"
    CHAR_CEILING = 31617

    GATE_STUB = (
        'Shard eligibility (GATE, not wave): `docs/conventions.md`, '
        '"Shard-eligibility predicate." NORMATIVE.'
    )
    DISPATCH_STUB = (
        'Shard expansion (fg-a10814): '
        '`skills/kernel/references/parallel-dispatch.md` — '
        'worktree/shard, 1 window, #N. NORMATIVE.'
    )
    INTEGRATE_STUB = (
        '- Shard INTEGRATE is ATOMIC (inverts the batch rule above): '
        '`skills/kernel/references/parallel-dispatch.md` '
        '(fg-a10815, R-D7). NORMATIVE.'
    )
    BATCH_INTEGRATE_STUB = (
        "Parallel batch — INTEGRATE is strictly sequential and "
        "kernel-owned."
    )

    def _kernel_content(self):
        return _cached_read_text(self.KERNEL_PATH)

    def test_gate_stub_cites_shard_eligibility_predicate(self):
        """GATE stub: one line citing the shard-eligibility predicate
        (docs/conventions.md, "Sharded fan-out" section) -- eligibility is
        decided at GATE, separate from wave eligibility."""
        content = self._kernel_content()
        self.assertIn(self.GATE_STUB, content)
        gate_heading_idx = content.index("### 4. GATE")
        dispatch_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        stub_idx = content.index(self.GATE_STUB)
        self.assertLess(gate_heading_idx, stub_idx)
        self.assertLess(stub_idx, dispatch_heading_idx)

    def test_dispatch_stub_cites_shard_expansion(self):
        """DISPATCH stub: one line citing the shard-expansion protocol
        (parallel-dispatch.md, fg-a10814 "Shard expansion" section) --
        worktree-per-shard, one shared window, #N display."""
        content = self._kernel_content()
        self.assertIn(self.DISPATCH_STUB, content)
        dispatch_heading_idx = content.index("### 5. ROUTE + DISPATCH")
        verify_heading_idx = content.index("### 6. VERIFY")
        stub_idx = content.index(self.DISPATCH_STUB)
        self.assertLess(dispatch_heading_idx, stub_idx)
        self.assertLess(stub_idx, verify_heading_idx)

    def test_integrate_stub_cites_fg_a10815_atomicity(self):
        """INTEGRATE stub (the NEW one, R-D7): states shard INTEGRATE is
        ATOMIC for the task and cites the fg-a10815 atomicity section --
        this cannot piggyback the batch-INTEGRATE stub because batches are
        NOT all-or-nothing while shards ARE atomic."""
        content = self._kernel_content()
        self.assertIn(self.INTEGRATE_STUB, content)
        self.assertIn("ATOMIC", self.INTEGRATE_STUB)
        self.assertIn("fg-a10815", self.INTEGRATE_STUB)
        integrate_heading_idx = content.index("### 7. INTEGRATE")
        learn_heading_idx = content.index("### 8. LEARN")
        stub_idx = content.index(self.INTEGRATE_STUB)
        self.assertLess(integrate_heading_idx, stub_idx)
        self.assertLess(stub_idx, learn_heading_idx)

    def test_three_stub_sites_all_present_and_integrate_distinct_from_batch(self):
        """Structural invariant: all three stub sites exist (GATE,
        DISPATCH, INTEGRATE), and the new shard-INTEGRATE stub is
        textually distinct from -- never a reuse of -- the pre-existing
        parallel-batch INTEGRATE stub, and sits immediately adjacent to it
        (batches are NOT all-or-nothing; shards ARE atomic -- reusing one
        stub for both would silently misstate one of them)."""
        content = self._kernel_content()
        self.assertIn(self.GATE_STUB, content)
        self.assertIn(self.DISPATCH_STUB, content)
        self.assertIn(self.BATCH_INTEGRATE_STUB, content)
        self.assertIn(self.INTEGRATE_STUB, content)
        self.assertNotEqual(self.BATCH_INTEGRATE_STUB, self.INTEGRATE_STUB)

        batch_idx = content.index(self.BATCH_INTEGRATE_STUB)
        shard_idx = content.index(self.INTEGRATE_STUB)
        self.assertLess(
            batch_idx, shard_idx,
            "the shard-INTEGRATE stub must sit AFTER the batch-INTEGRATE "
            "stub, adjacent to it, so a reader sees both semantics side "
            "by side",
        )
        between = content[batch_idx + len(self.BATCH_INTEGRATE_STUB):shard_idx]
        self.assertLess(
            len(between), 400,
            "the shard-INTEGRATE stub must be adjacent to the "
            "batch-INTEGRATE stub, not scattered elsewhere in INTEGRATE",
        )

    def test_kernel_skill_within_char_ceiling(self):
        """Char-ceiling pin (EARS clauses 1 & 4): SKILL.md must stay under
        the 31,617-char ceiling already established and pinned by
        TestFgA10201VerifierFindingFilterPins.test_kernel_skill_within_char_ceiling
        and TestFgA10208IdleWaitPins.test_kernel_skill_within_char_ceiling
        (grep 31617 -- three prior instances). This is NOT a new,
        independent ceiling number: it verifies this task's own three stub
        additions still fit under that SAME pre-existing budget, matching
        the repo's established per-task self-verification pattern for this
        invariant rather than introducing a fourth unrelated constant."""
        content = self._kernel_content()
        self.assertLessEqual(len(content), self.CHAR_CEILING)

    def test_ceiling_measured_by_len_not_wc_bytes(self):
        """EARS clause 2: the ceiling is measured with Python len() --
        character count -- never `wc -c` byte count. None of the three
        pre-existing ceiling pins (grep 31617) document WHY len() is the
        right metric; this pin does. SKILL.md's em-dashes are multibyte in
        UTF-8, so the byte count and the char count provably diverge --
        this test fails red if that divergence ever disappears (e.g. the
        multibyte characters get stripped), which is exactly the signal
        that would mean char-vs-byte stopped mattering here."""
        text = self._kernel_content()
        byte_len = len(text.encode("utf-8"))
        char_len = len(text)
        self.assertGreater(
            byte_len, char_len,
            "expected SKILL.md's UTF-8 byte length to exceed its len() "
            "char length (multibyte em-dashes etc.) -- if equal, the "
            "char-vs-byte distinction this pin documents no longer holds",
        )
        self.assertLessEqual(
            char_len, self.CHAR_CEILING,
            "the CHAR count (len(), not wc -c bytes) must clear the "
            "ceiling -- this is the pinned metric per fg-a10816 EARS "
            "clause 2",
        )
