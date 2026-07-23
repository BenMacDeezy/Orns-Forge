"""Doc-pin regression tests sharded from tools/test_doc_pins.py (fg-a11040):
classes for task-id prefix `fg-9e0103`: TestFg9e0103BatchWindowPins.
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


class TestFg9e0103BatchWindowPins(unittest.TestCase):
    """Doc-pins for fg-9e0103 (parallel-batch INTEGRATE moves to a single
    gate run + bisect-on-failure; sliding-window dispatch replaces the wave
    barrier; both cite the canonical conventions section fg-9e0101 landed).

    Covers all 3 EARS clauses: (1) single-gate batch INTEGRATE — merge all
    worktrees one at a time conflict-checked per merge, run gates ONCE on
    the merged result, bisect per-merge in completion order only on
    failure, merged-gates-is-authoritative unchanged; (2) sliding-window
    dispatch — max-parallel-tasks is a concurrency window, surplus workers
    dispatch the moment a slot frees, .forge/ writes/merges stay serialized
    and kernel-owned; (3) both rules are cited by the conventions section's
    exact name wherever they're read.
    """

    CONVENTIONS_SECTION = (
        "Latency rules — ship-review overlap, mechanical bounces, "
        "batch gates, sliding-window dispatch — 2026-07"
    )

    def test_parallel_dispatch_has_single_gate_and_bisect_rule(self):
        content = _cached_read_text((
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ))
        self.assertIn("run the gate suite ONCE against the", content)
        self.assertIn("not once per task", content)
        self.assertIn(
            "bisects by re-running gates per-merge in the same completion "
            "order",
            content,
        )
        self.assertIn(
            "merged-gates run remains authoritative\n  over any per-worktree "
            "gate pass",
            content,
        )
        normalized = re.sub(r"\s+", " ", content)
        self.assertEqual(
            normalized.count(re.sub(r"\s+", " ", self.CONVENTIONS_SECTION)), 2,
            "parallel-dispatch.md must cite the canonical conventions "
            "section by exact name at both the INTEGRATE and "
            "ROUTE+DISPATCH spots",
        )

    def test_parallel_dispatch_has_sliding_window_rule(self):
        content = _cached_read_text((
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ))
        self.assertIn("Sliding-window dispatch.", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(
            "not a hard cap on how many eligible tasks a session may "
            "eventually run", normalized,
        )
        self.assertIn(
            "dispatch each surplus task's worker the moment an "
            "in-flight worker's slot frees", normalized,
        )

    def test_kernel_gate_no_longer_has_wait_for_next_batch(self):
        content = _cached_read_text((REPO_ROOT / "skills" / "kernel" / "SKILL.md"))
        self.assertNotIn(
            "surplus eligible\n  tasks wait for the next batch.", content,
            "GATE's surplus sentence still contradicts the sliding-window "
            "rule (fg-9e0103)",
        )
        self.assertIn(
            "dispatch as slots free", content,
            "sliding-window dispatch behavior must be documented"
        )
        # Extract the GATE's "Parallel eligibility" section from kernel SKILL.md
        gate_match = re.search(
            r"\*\*Parallel eligibility \(wave-level\)\.\*\*.*?(?=\n###|\n## |\Z)",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(gate_match, "GATE 'Parallel eligibility' section not found")
        gate_section = gate_match.group(0)
        self.assertNotIn(
            "batch size ≤",
            gate_section,
            "GATE 'Parallel eligibility' section must not have batch size as "
            "an eligibility condition (fg-9e0103 requirement)",
        )
        # Check parallel-dispatch.md's eligibility scope sentence
        dispatch_content = _cached_read_text((
            REPO_ROOT / "skills" / "kernel" / "references" / "parallel-dispatch.md"
        ))
        # Extract the top-of-file scope sentence (lines 1-6)
        dispatch_scope = dispatch_content.split("\n\n")[0]
        self.assertNotIn(
            "batch size ≤",
            dispatch_scope,
            "parallel-dispatch.md eligibility scope sentence must not list "
            "batch size as an eligibility condition (fg-9e0103 requirement)",
        )

    def test_forge_wave_prose_aligned_to_single_gate_bisect(self):
        content = _cached_read_text((REPO_ROOT / "workflows" / "forge-wave.md"))
        self.assertIn(
            "the kernel runs the gate suite ONCE\nagainst the fully-merged "
            "result", content,
        )
        self.assertIn("the kernel bisects by re-running gates", content)
        normalized = re.sub(r"\s+", " ", content)
        self.assertIn(re.sub(r"\s+", " ", self.CONVENTIONS_SECTION), normalized)
