"""A/B benchmark runner core (fg-a10403, benchmark T3).

Implements docs/plans/2026-07-18-ab-benchmark-design.md D4 (fresh git
worktree per arm-run from a pinned base, no shared state) and D8 (script
everything deterministic; isolate the model-in-the-loop step). Stdlib only.

This module is the reusable harness: worktree lifecycle (create from a
pinned base SHA, run the injected adapter, capture the diff, remove --
idempotently, even on failure), a seeded arm-order draw whose seed is
recorded in the run record, wall-clock capture per arm-run (monotonic clock,
never self-reported by the adapter), and a deterministic plain-JSON run
record. The model-in-the-loop step is entirely behind the `adapters[arm]`
callable each caller injects (arm_a.py / arm_b.py, benchmark T6) -- this
module never embeds task content, prompts, or dispatch logic itself.
"""
from __future__ import annotations

import dataclasses
import json
import random
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ARMS = ("A", "B")


class WorktreeError(RuntimeError):
    """Raised when a git worktree operation fails."""


def _run_git(args, cwd):
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def create_worktree(repo_root: Path, base_sha: str, dest: Path) -> None:
    """Create a fresh git worktree at `dest`, detached at `base_sha`.

    `dest` must not already exist as a non-empty directory -- creation is
    not idempotent by design (D4: every arm-run gets its own fresh
    worktree). Only teardown (`remove_worktree`) is idempotent.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = _run_git(
        ["worktree", "add", "--detach", str(dest), base_sha],
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise WorktreeError(
            f"git worktree add failed for {dest} @ {base_sha}: "
            f"{result.stderr.strip()}"
        )


def remove_worktree(repo_root: Path, dest: Path) -> None:
    """Remove a git worktree at `dest`. Idempotent: a missing or already-
    removed worktree is not an error (D4/D8: "idempotent cleanup on
    failure"). Uses --force since an arm-run's uncommitted changes are
    expected to still be present at teardown time -- they are captured via
    `capture_diff` before this is called.
    """
    if not dest.exists():
        _run_git(["worktree", "prune"], cwd=repo_root)
        return
    result = _run_git(
        ["worktree", "remove", "--force", str(dest)],
        cwd=repo_root,
    )
    if result.returncode != 0:
        # Fall back to a manual removal + prune so a single wedged
        # worktree can never block the rest of a run.
        shutil.rmtree(dest, ignore_errors=True)
        _run_git(["worktree", "prune"], cwd=repo_root)
        if dest.exists():
            raise WorktreeError(
                f"failed to remove worktree {dest}: {result.stderr.strip()}"
            )


@contextmanager
def worktree(repo_root: Path, base_sha: str, dest: Path):
    """Context manager: create the worktree on enter, always remove it on
    exit (normal return or exception) -- the idempotent-cleanup-on-failure
    half of D4's worktree lifecycle.
    """
    create_worktree(repo_root, base_sha, dest)
    try:
        yield dest
    finally:
        remove_worktree(repo_root, dest)


def draw_arm_order(seed: int) -> tuple:
    """Deterministically draw the per-task arm-run order from a seed (D3:
    "arm-order randomization + recording"). The same seed always yields the
    same order; the seed itself is what the caller records, not the order
    alone, so the draw is reproducible from the run record.
    """
    rng = random.Random(seed)
    order = list(ARMS)
    rng.shuffle(order)
    return tuple(order)


def capture_diff(worktree_path: Path) -> str:
    """Capture the arm-run's full working-tree diff against the pinned
    base HEAD, as a single unified-diff string -- captured by the runner
    itself, never self-reported by the adapter (D6 wall-clock/diff
    capture discipline).

    New untracked files are staged intent-to-add first so they appear in
    the diff as additions (plain `git diff` otherwise omits untracked
    paths entirely).
    """
    _run_git(["add", "-A", "-N"], cwd=worktree_path)
    result = _run_git(["diff", "HEAD"], cwd=worktree_path)
    if result.returncode != 0:
        raise WorktreeError(
            f"git diff failed in {worktree_path}: {result.stderr.strip()}"
        )
    return result.stdout


@dataclasses.dataclass
class ArmRunResult:
    """One arm-run's outcome: everything the runner captured itself."""

    arm: str
    wall_clock_seconds: float
    diff: str
    adapter_result: Any


def run_arm(
    *,
    repo_root: Path,
    base_sha: str,
    dest: Path,
    arm: str,
    adapter: Callable[[Path], Any],
) -> ArmRunResult:
    """Run one arm in a fresh worktree: create, time + invoke the adapter,
    capture the diff, then always remove the worktree (D4/D8's
    create/run/capture/remove lifecycle). If the adapter raises, the
    worktree is still removed (idempotent cleanup on failure) and the
    exception propagates -- this module records outcomes, it does not
    swallow them.
    """
    start = time.monotonic()
    with worktree(repo_root, base_sha, dest) as wt_path:
        adapter_result = adapter(wt_path)
        diff = capture_diff(wt_path)
    elapsed = time.monotonic() - start
    return ArmRunResult(
        arm=arm,
        wall_clock_seconds=elapsed,
        diff=diff,
        adapter_result=adapter_result,
    )


def run_pair(
    *,
    task_id: str,
    repo_root: Path,
    base_sha: str,
    seed: int,
    adapters: dict,
    work_dir: Path,
    run_id: str = None,
) -> dict:
    """Orchestrate one matched pair's two arm-runs (D3/D4/D8): draw and
    record the seeded arm order, run each arm in its own fresh worktree
    forked from `base_sha` under `work_dir/<task_id>/<arm>/<run_id>/`, and
    return a deterministic, plain-JSON-shaped run record.

    `adapters` must map both "A" and "B" to a `Callable[[Path], Any]` --
    the sole model-in-the-loop boundary. This function never embeds task
    content or prompts itself (D8); it only supplies the worktree path and
    times/captures around whatever the adapter does with it.
    """
    if set(adapters) != set(ARMS):
        raise ValueError(
            f"adapters must provide exactly {ARMS}, got {sorted(adapters)}"
        )

    run_id = run_id or uuid.uuid4().hex
    order = draw_arm_order(seed)

    results = {}
    for arm in order:
        dest = work_dir / task_id / arm / run_id
        results[arm] = run_arm(
            repo_root=repo_root,
            base_sha=base_sha,
            dest=dest,
            arm=arm,
            adapter=adapters[arm],
        )

    return {
        "task_id": task_id,
        "run_id": run_id,
        "base_sha": base_sha,
        "seed": seed,
        "arm_order": list(order),
        "arms": {
            arm: {
                "wall_clock_seconds": result.wall_clock_seconds,
                "diff": result.diff,
                "adapter_result": result.adapter_result,
            }
            for arm, result in results.items()
        },
    }


def write_run_record(record: dict, path: Path) -> None:
    """Write a run record as deterministic, CRLF-safe UTF-8 JSON: sorted
    keys, explicit LF newlines regardless of platform default.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(record, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
