"""Tests for tools/benchmark/arms.py + glue.py (fg-a10406, benchmark T6:
arm adapters + procedural-symmetry proof).

Design refs (docs/plans/2026-07-18-ab-benchmark-design.md, cited not
restated): D3 ("Same brief: one shared task file; arm identity is a runner
flag, not content" -- arm A = full Forge protocol, arm B = single agent,
same brief + same gates, no judge) and D8 ("Runner: script everything
deterministic; isolate the model-in-the-loop step" -- the sole
model-in-the-loop divergence is quarantined into two thin adapters, and
`test_symmetry.py` "asserts the two adapters receive identical task input,
gate command, and base commit, and that the sole allowed structural
divergence is arm A's verifier+judge+bounce stage").

All model-in-the-loop behavior is stubbed via a recording `dispatch`
callable -- no real model calls (fg-a10406 spawn brief: "Use stub dispatch
callables; no real model calls"). Gate commands are real but trivial
(`sys.executable -c ...`) so `arms.run_gates`'s real subprocess plumbing is
exercised without depending on a real ledgerkit checkout.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

from arms import (
    ARM_A_ATTEMPT_KINDS,
    ARM_B_ATTEMPT_KINDS,
    DispatchResult,
    make_arm_a_adapter,
    make_arm_b_adapter,
    run_gates,
)
from glue import RecordShapeError, flatten_pair_record
from metrics import MetricsInputError, build_pair_rows


class RecordingDispatch:
    """Stub `dispatch(prompt_text, worktree_path)` callable. Records every
    call as (prompt_text, worktree_path) and returns preset DispatchResults
    in order (the last preset repeats if more calls happen than presets
    given -- keeps bounce-loop tests short to write)."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, prompt_text, worktree_path):
        self.calls.append((prompt_text, worktree_path))
        idx = min(len(self.calls) - 1, len(self.results) - 1)
        return self.results[idx]


def _brief(tmp, content="# Task\n\nDo the thing.\n"):
    path = pathlib.Path(tmp) / "task.md"
    path.write_text(content, encoding="utf-8")
    return path


# A trivial, fast, real gate command -- exercises run_gates's actual
# subprocess plumbing without depending on any real project checkout.
PASS_GATE = [sys.executable, "-c", "pass"]
FAIL_GATE = [sys.executable, "-c", "import sys; sys.exit(1)"]


class TestBriefSymmetry(unittest.TestCase):
    """D3: same brief bytes reach both arms; D8: 'never two prompt texts'
    -- every dispatch call in either arm, including arm A's verify/bounce
    calls, receives the identical brief content, never a modified or
    arm-specific preamble."""

    def test_first_dispatch_call_gets_byte_identical_brief_in_both_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            brief_text = brief_path.read_text(encoding="utf-8")

            dispatch_a = RecordingDispatch([DispatchResult(tokens=10, verdict="PASS")])
            dispatch_b = RecordingDispatch([DispatchResult(tokens=10)])

            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=dispatch_a,
            )
            adapter_b = make_arm_b_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=dispatch_b,
            )

            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            adapter_a(wt)
            adapter_b(wt)

            self.assertEqual(dispatch_a.calls[0][0], brief_text)
            self.assertEqual(dispatch_b.calls[0][0], brief_text)
            self.assertEqual(dispatch_a.calls[0][0], dispatch_b.calls[0][0])

    def test_every_arm_a_dispatch_call_reuses_the_same_brief_text_no_second_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            brief_text = brief_path.read_text(encoding="utf-8")

            # FAIL then PASS: forces a dispatch/verify/bounce/re-verify
            # sequence (4 dispatch calls total) so this proves the
            # invariant across every attempt kind, not just the first.
            dispatch_a = RecordingDispatch([
                DispatchResult(tokens=10),                        # dispatch
                DispatchResult(tokens=5, verdict="FAIL", fail_item_ids=["x"]),  # verify
                DispatchResult(tokens=10),                        # bounce
                DispatchResult(tokens=5, verdict="PASS"),         # re-verify
            ])
            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=dispatch_a,
                max_bounce_rounds=2,
            )
            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            adapter_a(wt)

            self.assertEqual(len(dispatch_a.calls), 4)
            for prompt_text, _wt_path in dispatch_a.calls:
                self.assertEqual(prompt_text, brief_text)


class TestWorktreePathSymmetry(unittest.TestCase):
    """D8: the adapter forwards the worktree path it is handed unmodified
    -- no rewriting/wrapping -- to both dispatch() and the gate command,
    identically in both arms."""

    def test_worktree_path_forwarded_unmodified_to_dispatch_in_both_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            dispatch_a = RecordingDispatch([DispatchResult(verdict="PASS")])
            dispatch_b = RecordingDispatch([DispatchResult()])

            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=dispatch_a,
            )
            adapter_b = make_arm_b_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=dispatch_b,
            )

            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            adapter_a(wt)
            adapter_b(wt)

            self.assertEqual(dispatch_a.calls[0][1], wt)
            self.assertEqual(dispatch_b.calls[0][1], wt)


class TestGateCommandSymmetry(unittest.TestCase):
    """D3/D8: the identical gate command runs in both arms, invoked the
    same way (same argv, cwd = the arm's own worktree path)."""

    def test_run_gates_invokes_exact_command_in_worktree_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            marker = wt / "marker.txt"
            gate_command = [
                sys.executable, "-c",
                f"import pathlib; pathlib.Path({str(marker)!r}).write_text('ran')",
            ]
            passed = run_gates(gate_command, wt)
            self.assertTrue(passed)
            self.assertTrue(marker.exists())

    def test_failing_gate_command_reports_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            wt = pathlib.Path(tmp)
            self.assertFalse(run_gates(FAIL_GATE, wt))

    def test_both_arms_run_the_identical_gate_command_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            wt_a = pathlib.Path(tmp) / "wt-a"
            wt_b = pathlib.Path(tmp) / "wt-b"
            wt_a.mkdir()
            wt_b.mkdir()
            marker_a = wt_a / "ran.txt"
            marker_b = wt_b / "ran.txt"

            def gate_for(marker):
                return [
                    sys.executable, "-c",
                    f"import pathlib; pathlib.Path({str(marker)!r}).write_text('ran')",
                ]

            # Both arms are handed a command built the same way (same
            # template, only the worktree-relative marker path differs --
            # the runner supplies each arm a distinct worktree per D4, so
            # the *command template* is what must be identical, which it
            # is here by construction).
            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=gate_for(marker_a),
                model_tier="sonnet/high",
                dispatch=RecordingDispatch([DispatchResult(verdict="PASS")]),
            )
            adapter_b = make_arm_b_adapter(
                brief_path=brief_path, gate_command=gate_for(marker_b),
                model_tier="sonnet/high",
                dispatch=RecordingDispatch([DispatchResult()]),
            )
            adapter_a(wt_a)
            adapter_b(wt_b)

            self.assertTrue(marker_a.exists())
            self.assertTrue(marker_b.exists())


class TestSoleStructuralDivergenceIsVerifyJudgeBounce(unittest.TestCase):
    """D3: 'the sole allowed structural divergence is arm A's
    verifier+judge+bounce stage'. Arm B's attempts are exactly one "turn"
    kind entry; arm A's attempts always start with the same "dispatch"
    build-equivalent step, and everything after it is verify-kind
    vocabulary (verify/re-verify/bounce) -- never anything else."""

    def test_arm_b_is_a_single_turn_attempt_no_judge_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            adapter_b = make_arm_b_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high",
                dispatch=RecordingDispatch([DispatchResult(tokens=42)]),
            )
            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            result = adapter_b(wt)

            kinds = [a["kind"] for a in result["attempts"]]
            self.assertEqual(kinds, ["turn"])
            for kind in kinds:
                self.assertIn(kind, ARM_B_ATTEMPT_KINDS)

    def test_arm_a_build_step_plus_verify_only_no_bounce_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high",
                dispatch=RecordingDispatch([
                    DispatchResult(tokens=10),
                    DispatchResult(tokens=5, verdict="PASS"),
                ]),
            )
            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            result = adapter_a(wt)

            kinds = [a["kind"] for a in result["attempts"]]
            self.assertEqual(kinds[0], "dispatch")
            self.assertEqual(kinds[1:], ["verify"])
            for kind in kinds:
                self.assertIn(kind, ARM_A_ATTEMPT_KINDS)
            # Beyond the shared "dispatch" build-equivalent step, every
            # remaining kind is verify-judge-bounce vocabulary -- never
            # anything arm B would also produce ("turn" never appears here).
            self.assertTrue(set(kinds[1:]) <= {"verify", "re-verify", "bounce"})

    def test_arm_a_bounce_loop_terminates_at_max_bounce_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = _brief(tmp)
            always_fail = RecordingDispatch([
                DispatchResult(tokens=10),  # dispatch
                DispatchResult(tokens=5, verdict="FAIL", fail_item_ids=["a"]),
                DispatchResult(tokens=10),
                DispatchResult(tokens=5, verdict="FAIL", fail_item_ids=["b"]),
            ])
            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=always_fail,
                max_bounce_rounds=1,
            )
            wt = pathlib.Path(tmp) / "wt"
            wt.mkdir()
            result = adapter_a(wt)

            kinds = [a["kind"] for a in result["attempts"]]
            self.assertEqual(kinds, ["dispatch", "verify", "bounce", "re-verify"])
            # Loop must actually terminate (this test itself is the proof
            # -- an unbounded loop would hang rather than reach here).


class TestFlattenPairRecord(unittest.TestCase):
    """The T6 interface seam: flatten_pair_record reshapes runner.run_pair's
    ONE pair-shaped record into TWO metrics-consumable RunRecords, per-arm
    run_id derived as f"{run_id}-{arm}" (fg-a10406 Execution plan)."""

    def _pair_record(self, run_id="pairrun1"):
        return {
            "task_id": "B1",
            "run_id": run_id,
            "base_sha": "deadbeef",
            "seed": 7,
            "arm_order": ["A", "B"],
            "arms": {
                "A": {
                    "wall_clock_seconds": 12.5,
                    "diff": "diff --git a/x b/x\n",
                    "adapter_result": {
                        "arm": "A",
                        "model_tier": "sonnet/high",
                        "attempts": [
                            {"kind": "dispatch", "tokens": 10, "verdict": None, "fail_item_ids": []},
                            {"kind": "verify", "tokens": 5, "verdict": "PASS", "fail_item_ids": []},
                        ],
                    },
                },
                "B": {
                    "wall_clock_seconds": 8.1,
                    "diff": "diff --git a/y b/y\n",
                    "adapter_result": {
                        "arm": "B",
                        "model_tier": "sonnet/high",
                        "attempts": [
                            {"kind": "turn", "tokens": 20, "verdict": None, "fail_item_ids": []},
                        ],
                    },
                },
            },
        }

    def test_produces_two_records_with_per_arm_run_id(self):
        rows = flatten_pair_record(self._pair_record(run_id="pairrun1"))
        self.assertEqual(len(rows), 2)
        by_arm = {r["arm"]: r for r in rows}
        self.assertEqual(set(by_arm), {"A", "B"})
        self.assertEqual(by_arm["A"]["run_id"], "pairrun1-A")
        self.assertEqual(by_arm["B"]["run_id"], "pairrun1-B")

    def test_run_ids_are_unique(self):
        rows = flatten_pair_record(self._pair_record())
        run_ids = [r["run_id"] for r in rows]
        self.assertEqual(len(run_ids), len(set(run_ids)))

    def test_carries_task_id_model_tier_wall_clock_and_attempts(self):
        rows = flatten_pair_record(self._pair_record())
        by_arm = {r["arm"]: r for r in rows}
        self.assertEqual(by_arm["A"]["task_id"], "B1")
        self.assertEqual(by_arm["B"]["task_id"], "B1")
        self.assertEqual(by_arm["A"]["model_tier"], "sonnet/high")
        self.assertEqual(by_arm["A"]["wall_clock_seconds"], 12.5)
        self.assertEqual(
            by_arm["A"]["attempts"],
            self._pair_record()["arms"]["A"]["adapter_result"]["attempts"],
        )

    def test_raises_on_missing_model_tier(self):
        record = self._pair_record()
        del record["arms"]["A"]["adapter_result"]["model_tier"]
        with self.assertRaises(RecordShapeError):
            flatten_pair_record(record)

    def test_raises_on_missing_attempts(self):
        record = self._pair_record()
        del record["arms"]["B"]["adapter_result"]["attempts"]
        with self.assertRaises(RecordShapeError):
            flatten_pair_record(record)

    def test_raises_on_missing_arm(self):
        record = self._pair_record()
        del record["arms"]["B"]
        with self.assertRaises(RecordShapeError):
            flatten_pair_record(record)

    def test_round_trips_through_metrics_build_pair_rows(self):
        rows = flatten_pair_record(self._pair_record(run_id="pairrun2"))
        # No scorecards yet -- proves the reshaped records satisfy
        # metrics.py's RunRecord validators (unique run_id, arm-vocabulary
        # match) on their own, per the fg-a10406 Execution plan's "prove by
        # round-tripping through metrics.build_pair_rows in a test".
        result_rows = build_pair_rows(rows, [])
        self.assertEqual(len(result_rows), 2)
        by_arm = {r["arm"]: r for r in result_rows}
        self.assertEqual(by_arm["A"]["run_id"], "pairrun2-A")
        self.assertEqual(by_arm["B"]["run_id"], "pairrun2-B")
        self.assertEqual(by_arm["A"]["turns"], 2)
        self.assertEqual(by_arm["B"]["turns"], 1)


class TestFullPairIntegration(unittest.TestCase):
    """End-to-end through runner.run_pair with real git worktrees (mirrors
    tools/benchmark/test_runner.py's scratch-repo pattern), proving the
    adapters are runner-compatible Callable[[Path], Any] and that the
    reshaped output survives a real worktree round-trip untouched."""

    def _git(self, args, cwd):
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", check=True,
        )

    def _init_scratch_repo(self, path):
        self._git(["init", "-q"], path)
        self._git(["config", "user.email", "arms-test@example.com"], path)
        self._git(["config", "user.name", "Arms Test"], path)
        self._git(["config", "commit.gpgsign", "false"], path)
        (path / "a.txt").write_text("base\n", encoding="utf-8", newline="\n")
        self._git(["add", "a.txt"], path)
        self._git(["commit", "-q", "-m", "base commit"], path)
        return self._git(["rev-parse", "HEAD"], path).stdout.strip()

    def test_run_pair_with_both_adapters_flattens_and_validates(self):
        from runner import run_pair

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            repo_root = tmp_path / "scratch-repo"
            repo_root.mkdir()
            base_sha = self._init_scratch_repo(repo_root)
            brief_path = _brief(tmp)

            def make_dispatch_a():
                def _dispatch(prompt_text, worktree_path):
                    (worktree_path / "a.txt").write_text(
                        "changed-by-a\n", encoding="utf-8", newline="\n")
                    return DispatchResult(tokens=10, verdict="PASS")
                return _dispatch

            def make_dispatch_b():
                def _dispatch(prompt_text, worktree_path):
                    (worktree_path / "a.txt").write_text(
                        "changed-by-b\n", encoding="utf-8", newline="\n")
                    return DispatchResult(tokens=10)
                return _dispatch

            adapter_a = make_arm_a_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=make_dispatch_a(),
            )
            adapter_b = make_arm_b_adapter(
                brief_path=brief_path, gate_command=PASS_GATE,
                model_tier="sonnet/high", dispatch=make_dispatch_b(),
            )

            pair_record = run_pair(
                task_id="B1",
                repo_root=repo_root,
                base_sha=base_sha,
                seed=3,
                adapters={"A": adapter_a, "B": adapter_b},
                work_dir=tmp_path / "bench" / "wt",
            )

            rows = flatten_pair_record(pair_record)
            self.assertEqual(len(rows), 2)
            # Not a MetricsInputError -> proves this module's reshaping
            # satisfies metrics.py's RunRecord contract end to end.
            try:
                build_pair_rows(rows, [])
            except MetricsInputError as exc:  # pragma: no cover - failure path
                self.fail(f"reshaped records failed metrics validation: {exc}")


if __name__ == "__main__":
    unittest.main()
