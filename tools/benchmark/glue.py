"""Record-reshaping seam (fg-a10406, benchmark T6).

INTERFACE SEAM (runner-verifier finding, 2026-07-18, restated in the
fg-a10406 Execution plan): `runner.run_pair` (T3) emits ONE pair-shaped
record -- `{task_id, run_id, base_sha, seed, arm_order, arms: {A/B:
{wall_clock_seconds, diff, adapter_result}}}` -- with `adapter_result`
opaque to the runner. `metrics.py`'s documented RunRecord contract (its
module docstring, "INPUT CONTRACT") instead expects one FLAT record PER
ARM-RUN -- `{task_id, arm, run_id, model_tier, wall_clock_seconds,
attempts}` -- with `run_id` UNIQUE per arm-run, never one id shared by both
arms of a pair.

`flatten_pair_record` is that reshaping. It relies on `arms.py`'s adapters
(T6, this same task) shaping their `adapter_result` as `{"arm",
"model_tier", "attempts", ...}` -- see arms.py's module docstring -- and
reads exactly those two extra keys (`model_tier`, `attempts`) back out,
combining them with the pair record's shared/per-arm fields.

Per-arm `run_id` is derived as `f"{run_id}-{arm}"`, exactly as the
Execution plan names it and as metrics.py's `_validate_unique_run_ids`
requires (a shared per-pair run_id is rejected outright, not silently
guessed at).
"""
from __future__ import annotations

from typing import List


class RecordShapeError(ValueError):
    """Raised when a pair record or an arm's adapter_result is missing a
    field this reshaping needs. Never silently defaulted or guessed --
    mirrors metrics.py's MetricsInputError fail-loud discipline for the
    seam this module owns (D7's "never invented" rule extends to the glue
    between the runner and the metrics layer, not just metrics.py itself).
    """


def flatten_pair_record(pair_record: dict) -> List[dict]:
    """Reshape one `runner.run_pair()` pair record into two
    metrics-consumable RunRecords (one per arm), per the fg-a10406
    interface seam note above.

    Returns a list of exactly two dicts, in arm order ("A" then "B"), each
    shaped `{task_id, arm, run_id, model_tier, wall_clock_seconds,
    attempts}` -- ready to hand to `metrics.build_pair_rows` alongside
    scorecards. Raises `RecordShapeError` if the pair record or either
    arm's `adapter_result` is missing a field this reshaping depends on;
    it never invents a `model_tier` or an empty `attempts` list to paper
    over a malformed adapter_result.
    """
    for key in ("task_id", "run_id", "arms"):
        if key not in pair_record:
            raise RecordShapeError(f"pair record missing required key {key!r}")

    rows = []
    for arm in ("A", "B"):
        if arm not in pair_record["arms"]:
            raise RecordShapeError(f"pair record missing arm {arm!r} in 'arms'")
        arm_data = pair_record["arms"][arm]

        for key in ("wall_clock_seconds", "adapter_result"):
            if key not in arm_data:
                raise RecordShapeError(
                    f"pair record arm {arm!r} missing required key {key!r}"
                )

        adapter_result = arm_data["adapter_result"]
        if not isinstance(adapter_result, dict):
            raise RecordShapeError(
                f"arm {arm!r} adapter_result must be a dict, got "
                f"{type(adapter_result).__name__}"
            )
        for key in ("model_tier", "attempts"):
            if key not in adapter_result:
                raise RecordShapeError(
                    f"arm {arm!r} adapter_result missing required key {key!r} "
                    "-- adapters (arms.py) must set both"
                )

        rows.append({
            "task_id": pair_record["task_id"],
            "arm": arm,
            "run_id": f"{pair_record['run_id']}-{arm}",
            "model_tier": adapter_result["model_tier"],
            "wall_clock_seconds": arm_data["wall_clock_seconds"],
            "attempts": adapter_result["attempts"],
        })

    return rows
