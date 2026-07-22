"""A/B benchmark arm adapters (fg-a10406, benchmark T6).

Implements design decisions D3 ("Same brief: one shared task file; arm
identity is a runner flag, not content") and D8 ("Runner: script everything
deterministic; isolate the model-in-the-loop step") from
docs/plans/2026-07-18-ab-benchmark-design.md (cited, never restated here).

- **Arm A** (`make_arm_a_adapter`) drives the full Forge-protocol shape:
  a build dispatch, then a verify-judge attempt loop (verify -> if FAIL,
  bounce -> re-verify -> ... up to `max_bounce_rounds`), mirroring D3's
  "ROUTE -> DISPATCH -> VERIFY -> ship judges -> INTEGRATE, including the
  bounce protocol" and the Attempt-log grammar tools/telemetry.py /
  blinding.py already recognize (`dispatch`, `verify`, `bounce`,
  `re-verify`).
- **Arm B** (`make_arm_b_adapter`) drives a single build dispatch, the same
  gate command, and stops -- "no adversarial verifier spawn, no ship judge,
  and no bounce" (D3).

Both factories return a `Callable[[Path], Any]` -- runner.run_pair's
`adapters["A"|"B"]` shape (runner.py, T3) -- so `run_pair(..., adapters={"A":
make_arm_a_adapter(...), "B": make_arm_b_adapter(...)})` works unmodified.

**The model-in-the-loop seam.** Both factories take a `dispatch` argument:
`Callable[[str, Path], DispatchResult]`, i.e. `dispatch(prompt_text,
worktree_path) -> DispatchResult`. This is the sole model-in-the-loop call
either adapter makes; everything else here (reading the brief, deciding
which attempt kind to record, running the gate command, deciding whether to
loop) is deterministic, scripted glue around it, per D8. The real dispatch
implementation is supplied by the T8 execution layer at run time; tests in
this repo use a recording stub (`test_symmetry.py`), never a real model
call.

**"Never two prompt texts" (D3).** Both adapters read `brief_path` once
into `brief_text` and pass that exact string, byte-identical, to *every*
`dispatch()` call they make -- the initial build call, and (arm A only)
every verify/bounce/re-verify call. There is no arm-specific preamble and
no separate "please verify this" prompt text: the *kind* of a call (build
vs. verify vs. bounce) is tracked entirely by the adapter's own bookkeeping
(which attempt slot it records), never by varying what is handed to
`dispatch`. This keeps the one invariant D3 requires -- identical brief
content reaches both arms -- true by construction rather than by
discipline, and `test_symmetry.py` proves it holds for every call, not just
the first.

**Attempt-kind vocabulary** matches metrics.py's ARM_A_ATTEMPT_KINDS /
ARM_B_ATTEMPT_KINDS exactly (arm A: dispatch/verify/re-verify/bounce; arm B:
turn) -- see metrics.py's module docstring for the full RunRecord contract
this module's `adapter_result["attempts"]` must satisfy once glue.py's
`flatten_pair_record` reshapes it.
"""
from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from typing import Any, Callable, List, Optional

# Mirrors metrics.py's ARM_A_ATTEMPT_KINDS / ARM_B_ATTEMPT_KINDS (kept as a
# literal copy rather than an import, same rationale blinding.py states for
# its own mirrored telemetry vocabulary: this module should not have to
# reach into metrics.py's internals just to know its own output vocabulary).
ARM_A_ATTEMPT_KINDS = {"dispatch", "verify", "re-verify", "bounce"}
ARM_B_ATTEMPT_KINDS = {"turn"}


@dataclasses.dataclass(frozen=True)
class DispatchResult:
    """What the injected `dispatch(prompt_text, worktree_path)` callable
    returns for one model-in-the-loop call -- the shape T8's real dispatch
    implementation must produce, and the shape stubs use in tests.

    Fields map straight onto one metrics.py RunRecord `attempts[]` entry
    (see metrics.py module docstring): `tokens` is real per-call usage
    (`None` if unreported -- never a stand-in for zero, per D6). `verdict`
    is only meaningful for verify-kind calls (arm A's verify/re-verify
    steps) -- `None` for a build/bounce/turn call. `fail_item_ids` is the
    structured list of checklist item ids a FAIL verdict cites (empty list
    default, never omitted) -- how compute_caught() works without parsing
    prose (metrics.py).
    """

    tokens: Optional[int] = None
    verdict: Optional[str] = None
    fail_item_ids: List[str] = dataclasses.field(default_factory=list)


DispatchFn = Callable[[str, Path], DispatchResult]


def run_gates(gate_command: List[str], cwd: Path) -> bool:
    """Run the shared gate command in `cwd` (an arm's own worktree),
    scripted -- never model-in-the-loop. Returns True iff the command exits
    zero. Both adapters call this with whatever `gate_command` their caller
    supplied, unmodified, so the same command runs the same way in both
    arms (D3/D8)."""
    result = subprocess.run(
        list(gate_command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _to_attempt(kind: str, result: DispatchResult) -> dict:
    return {
        "kind": kind,
        "tokens": result.tokens,
        "verdict": result.verdict,
        "fail_item_ids": list(result.fail_item_ids or []),
    }


def _read_brief(brief_path: Path) -> str:
    return Path(brief_path).read_text(encoding="utf-8")


def make_arm_a_adapter(
    *,
    brief_path: Path,
    gate_command: List[str],
    model_tier: str,
    dispatch: DispatchFn,
    max_bounce_rounds: int = 2,
) -> Callable[[Path], Any]:
    """Build arm A's runner-compatible adapter: full Forge-protocol shape
    -- build dispatch, then a verify-judge attempt loop with up to
    `max_bounce_rounds` bounce/re-verify cycles (D3's "VERIFY mode 2 ...
    ship judges ... INTEGRATE, including the bounce protocol").

    Flow (attempt kinds in order, matching the Attempt-log grammar
    tools/telemetry.py and blinding.py already recognize):
      1. "dispatch"  -- the build call.
      2. run the gate command (scripted, not model-in-the-loop).
      3. "verify"    -- first verify call.
         - verdict != "FAIL" (PASS/ESCALATE/None) -> stop.
         - verdict == "FAIL" and bounce budget remains ->
           "bounce" (re-dispatch to fix) -> re-run gates ->
           "re-verify" -- repeat from here, up to `max_bounce_rounds`
           bounce rounds, then stop regardless of the final verdict (a
           double-bounce-and-still-FAIL run is recorded as-is; deciding
           what that means for routing is the report layer's job, not
           this adapter's).

    Returns an `adapter_result` dict (runner.py's `ArmRunResult.
    adapter_result`) shaped `{"arm": "A", "model_tier", "attempts",
    "gates_passed"}` -- `model_tier` and `attempts` are exactly what
    glue.py's `flatten_pair_record` reads back out (the fg-a10406 interface
    seam).
    """

    def adapter(worktree_path: Path) -> dict:
        brief_text = _read_brief(brief_path)
        attempts: List[dict] = []

        build_result = dispatch(brief_text, worktree_path)
        attempts.append(_to_attempt("dispatch", build_result))
        gates_passed = run_gates(gate_command, worktree_path)

        bounce_round = 0
        while True:
            verify_kind = "verify" if bounce_round == 0 else "re-verify"
            verify_result = dispatch(brief_text, worktree_path)
            attempts.append(_to_attempt(verify_kind, verify_result))

            if verify_result.verdict != "FAIL" or bounce_round >= max_bounce_rounds:
                break

            bounce_round += 1
            bounce_result = dispatch(brief_text, worktree_path)
            attempts.append(_to_attempt("bounce", bounce_result))
            gates_passed = run_gates(gate_command, worktree_path)

        return {
            "arm": "A",
            "model_tier": model_tier,
            "attempts": attempts,
            "gates_passed": gates_passed,
        }

    return adapter


def make_arm_b_adapter(
    *,
    brief_path: Path,
    gate_command: List[str],
    model_tier: str,
    dispatch: DispatchFn,
) -> Callable[[Path], Any]:
    """Build arm B's runner-compatible adapter: a single build dispatch,
    the identical gate command, and stop -- "no adversarial verifier spawn,
    no ship judge, and no bounce" (D3). The agent may self-review inside
    its own dispatch call; there is simply no separate adapter-level judge
    step, so exactly one attempt (kind "turn") is ever recorded.
    """

    def adapter(worktree_path: Path) -> dict:
        brief_text = _read_brief(brief_path)
        result = dispatch(brief_text, worktree_path)
        attempts = [_to_attempt("turn", result)]
        gates_passed = run_gates(gate_command, worktree_path)

        return {
            "arm": "B",
            "model_tier": model_tier,
            "attempts": attempts,
            "gates_passed": gates_passed,
        }

    return adapter
