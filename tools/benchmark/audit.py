"""Blinded-audit harness (fg-a10407, benchmark T7).

Implements the auditor-consumption half of design **D5**
(docs/plans/2026-07-18-ab-benchmark-design.md, "D5 -- Blinded audit:
normalize -> shuffle -> sealed key; checklist frozen at design time" -- cited
here, never restated). blinding.py (T4) owns normalization, label shuffling,
and writing the sealed key; ground-truth/checklists/*.json (T2) owns the
frozen per-task checklist. This module is the harness *around* the blinded
auditor -- the auditor itself is a spawned agent (T8 time, model-in-the-loop,
per the fg-a10407 spawn brief); nothing here calls a model.

Three responsibilities, in the strict order D5 requires:

1. **build_audit_packet(task_id, presentations, checklist)** -- the exact
   material a blinded auditor receives: labeled normalized diffs + the
   frozen checklist's scoring-relevant fields + scoring instructions.
   Two loud-error guards run before anything is packaged:
     - **Tamper check.** `verify_checklist_integrity()` recomputes the
       checklist's `content_sha256` (sha256 over canonical JSON of
       `{task_id, class, items}`, sorted keys, no whitespace -- confirmed
       against every shipped checklist in ground-truth/checklists/) and
       raises `AuditError` on any mismatch, a missing hash field, or a
       `checklist["task_id"]` that doesn't match the `task_id` argument.
     - **Fingerprint tripwire.** Every presentation's diff text is checked
       for a surviving `fg-xxxx` id or an in-text `.forge/...` path --
       either one surviving means `blinding.normalize_diff()` was not
       applied, or was bypassed, to that diff. `build_audit_packet` refuses
       loudly rather than silently handing a de-blinding leak to the
       auditor. This is a tripwire, not a second normalization pass: it
       does NOT re-run blinding.py's fingerprint list, it only checks for
       the two starkest un-normalized markers (see blinding.py's own
       module docstring for the full scrub list this module trusts T4 to
       have already applied).

2. **BlindedScoreLedger.record_scores(label, checklist_results,
   additional_defects=None)** -- accumulates one labeled diff's scoring
   into a label-keyed dict, per this run's ledger. Each call is structurally
   validated against metrics.py's own `VALID_STATUSES` /
   `VALID_SEVERITIES` vocabulary (imported, not restated -- unlike
   blinding.py's deliberate independence from the *live protocol runtime*,
   metrics.py is this same benchmark subsystem's contract owner for the
   ScorecardRecord shape this module must emit, so importing it directly
   avoids the vocabulary drifting out of sync with what
   `metrics.build_pair_rows` will actually accept).

3. **BlindedScoreLedger.unseal(sealed_key_path, run_ids_by_task)** -- the
   ONLY method that reads the sealed key (`blinding.write_sealed_key`'s
   output; T7's deny path for the auditor spawn is
   `blinding.SEALED_KEY_DIR`, see auditor-contract.md). Refuses if any
   label present in the sealed key lacks a recorded score (scoring must be
   complete before the key opens). Once a ledger has been unsealed,
   `record_scores` refuses on that same ledger -- ordering is enforced by
   construction (one ledger instance = one run's scoring session), not by
   caller discipline. Free functions cannot enforce "no further recording
   after this key was opened" without hidden module-level state, which
   would be worse than an explicit, small, per-run object; `record_scores`
   and `unseal` are therefore instance methods on `BlindedScoreLedger`
   rather than bare module functions, while keeping the exact method names
   the fg-a10407 Execution plan (b)/(c) name.

   **run_ids_by_task -- interface seam.** `blinding.write_sealed_key`'s
   sealed-key entries are `{label: {"task": task_id, "arm": "A"|"B"}}` --
   no `run_id` at all (D5's sealed key is scoped to the whole benchmark
   run, not one pair; `blinding.py`'s own docstring: "A run covers many
   task pairs... merges into any existing file for the same runid"). To
   produce a genuinely `metrics.py`-compatible `ScorecardRecord` (which
   requires a `run_id` matching the *pair's own* run_id, per-arm, exactly
   as `glue.flatten_pair_record` derives it: `f"{pair_run_id}-{arm}"`),
   `unseal` needs that pair-level run_id back from its caller. T8 already
   has it (it is `runner.run_pair`'s own `run_id` return field, the same
   value T8 hands to `glue.flatten_pair_record`) -- `run_ids_by_task` is
   simply `{task_id: pair_run_id, ...}` for every task pair in the run.
   `unseal` derives each record's `run_id` as
   `f"{run_ids_by_task[task_id]}-{arm}"`, matching `glue.py`'s derivation
   exactly so the two sides always join by construction.

**What this module does NOT check.** Checklist items declare their own
`severity`; when the auditor marks an item `defect-present`, D5/the
auditor-contract instruct it to echo that fixed severity verbatim rather
than inventing one. `record_scores` validates the *supplied* severity is a
member of `metrics.VALID_SEVERITIES` -- it cannot cross-check it against
the checklist's own declared value, because a label carries no task
identity until `unseal()` (that is the whole point of blinding); doing the
cross-check post-unseal would need the checklist wired through `unseal`
too, which is out of this task's minimal contract. This is a stated,
instruction-level control (auditor-contract.md), not a machine-enforced
one -- see the task's own honesty rule: "severity fixed by the checklist,
not the auditor."
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Dict, List, Optional, Sequence, Tuple

from metrics import VALID_SEVERITIES, VALID_STATUSES

# Fingerprint tripwire -- deliberately narrow (see module docstring point 1).
# Mirrors blinding.py's own _FG_ID_RE / _FORGE_PATH_RE so "surviving
# fingerprint" means the exact same thing on both sides of the normalize/
# audit boundary.
_FG_ID_RE = re.compile(r"\bfg-[0-9a-f]{4,8}\b", re.I)
_FORGE_PATH_RE = re.compile(r"\.forge[\\/][\w.\\/-]*")

SCORING_INSTRUCTIONS = (
    "Score each labeled diff independently against the checklist items "
    "below. For each item, report status \"satisfied\" (the diff meets it), "
    "\"defect-present\" (the diff fails it -- echo the item's own fixed "
    "severity verbatim, never invent one), or \"n/a\" (not applicable to "
    "this diff, OR you genuinely cannot determine it from the diff alone -- "
    "never guess). List any additional defects you find beyond the "
    "checklist, each with your own severity (minor/important/critical). "
    "Score only what the diff shows; do not infer intent, do not assume "
    "the other labeled diff's approach, and do not attempt to identify "
    "which arm produced either diff."
)


class AuditError(ValueError):
    """Raised on a checklist integrity failure, a surviving blinding
    fingerprint, a malformed score, or an ordering violation between
    recording scores and opening the sealed key. Always loud, never a
    silent default or a guessed value (fg-a10407 spawn brief)."""


# ---------------------------------------------------------------------------
# 1. Checklist integrity (tamper check)
# ---------------------------------------------------------------------------

def checklist_content_hash(checklist: dict) -> str:
    """sha256 over canonical JSON of {task_id, class, items} only (sorted
    keys, no whitespace) -- the exact formula named in every shipped
    checklist's own `content_sha256_note` field, confirmed against all of
    ground-truth/checklists/*.json by this module's tests."""
    for key in ("task_id", "class", "items"):
        if key not in checklist:
            raise AuditError(
                f"checklist missing required key {key!r} -- cannot compute "
                "its content hash"
            )
    canonical = json.dumps(
        {"task_id": checklist["task_id"], "class": checklist["class"], "items": checklist["items"]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_checklist_integrity(checklist: dict) -> None:
    """Raise AuditError if `checklist["content_sha256"]` doesn't match a
    freshly recomputed hash over its own {task_id, class, items} -- the
    tamper check `build_audit_packet` must run before packaging anything
    (fg-a10407 spawn brief, build_audit_packet requirement (a))."""
    if "content_sha256" not in checklist:
        raise AuditError(
            f"checklist for task {checklist.get('task_id')!r} has no "
            "content_sha256 -- cannot verify it was frozen before any arm "
            "ran; refusing to package it for the auditor"
        )
    expected = checklist["content_sha256"]
    actual = checklist_content_hash(checklist)
    if actual != expected:
        raise AuditError(
            f"checklist content_sha256 mismatch for task "
            f"{checklist.get('task_id')!r}: stored={expected!r} "
            f"recomputed={actual!r} -- checklist was tampered with or "
            "edited after freezing; refusing to package it for the auditor"
        )


# ---------------------------------------------------------------------------
# Fingerprint tripwire
# ---------------------------------------------------------------------------

def _check_fingerprint_free(label: str, diff_text: Optional[str]) -> None:
    if not diff_text:
        return
    if _FG_ID_RE.search(diff_text):
        raise AuditError(
            f"presentation {label!r} contains a surviving fg-id fingerprint "
            "-- this looks like raw un-normalized diff text (blinding."
            "normalize_diff was not applied, or was bypassed, to this "
            "diff); refusing to build an audit packet that could de-blind "
            "the auditor"
        )
    if _FORGE_PATH_RE.search(diff_text):
        raise AuditError(
            f"presentation {label!r} contains a surviving .forge/ path "
            "fingerprint -- this looks like raw un-normalized diff text; "
            "refusing to build an audit packet that could de-blind the "
            "auditor"
        )


# ---------------------------------------------------------------------------
# build_audit_packet
# ---------------------------------------------------------------------------

def build_audit_packet(
    task_id: str,
    presentations: Sequence[Tuple[str, Optional[str]]],
    checklist: dict,
) -> dict:
    """Build the exact material a blinded auditor receives for one task
    pair: labeled normalized diffs + the frozen checklist's scoring fields
    + scoring instructions. Never includes arm identity, the sealed key, or
    any checklist metadata beyond what scoring needs (item_id, description,
    how_to_detect, severity).

    `presentations` is `blinding.shuffle_pair()`'s first return value --
    `[(label, normalized_diff), ...]` in presentation order, carrying no
    arm identity. `checklist` is one task's already-loaded frozen checklist
    dict (ground-truth/checklists/<task_id>.checklist.json).

    Raises AuditError (loud, never silent) if:
      - the checklist's content_sha256 doesn't match its own content (tamper)
      - the checklist's task_id doesn't match the `task_id` argument
      - any presentation's label is duplicated
      - fewer than 2 presentations are given (not a matched pair)
      - any presentation's diff text carries a surviving fg-id or .forge/
        path fingerprint (the tripwire)
    """
    verify_checklist_integrity(checklist)

    if checklist.get("task_id") != task_id:
        raise AuditError(
            f"checklist task_id {checklist.get('task_id')!r} does not "
            f"match requested task_id {task_id!r} -- refusing to package a "
            "mismatched checklist"
        )

    packaged_presentations = []
    seen_labels = set()
    for label, diff_text in presentations:
        if label in seen_labels:
            raise AuditError(f"duplicate label {label!r} in presentations")
        seen_labels.add(label)
        _check_fingerprint_free(label, diff_text)
        packaged_presentations.append({"label": label, "diff": diff_text})

    if len(packaged_presentations) < 2:
        raise AuditError(
            f"expected at least 2 presentations for a matched pair, got "
            f"{len(packaged_presentations)}"
        )

    checklist_items = [
        {
            "item_id": item["item_id"],
            "description": item["description"],
            "how_to_detect": item["how_to_detect"],
            "severity": item["severity"],
        }
        for item in checklist["items"]
    ]

    return {
        "task_id": task_id,
        "instructions": SCORING_INSTRUCTIONS,
        "checklist_items": checklist_items,
        "presentations": packaged_presentations,
    }


# ---------------------------------------------------------------------------
# Score validation (shared by record_scores)
# ---------------------------------------------------------------------------

def _validate_checklist_results(checklist_results) -> None:
    for item in checklist_results:
        for key in ("item_id", "status"):
            if key not in item:
                raise AuditError(
                    f"checklist_results item missing required key {key!r}: {item!r}"
                )
        status = item["status"]
        if status not in VALID_STATUSES:
            raise AuditError(
                f"checklist_results item {item.get('item_id')!r} has unknown "
                f"status {status!r} (expected one of {sorted(VALID_STATUSES)})"
            )
        if status == "defect-present":
            severity = item.get("severity")
            if severity not in VALID_SEVERITIES:
                raise AuditError(
                    f"checklist_results item {item.get('item_id')!r} is "
                    f"defect-present but has invalid severity {severity!r} "
                    f"(expected one of {sorted(VALID_SEVERITIES)})"
                )


def _validate_additional_defects(additional_defects) -> None:
    for extra in additional_defects:
        severity = extra.get("severity")
        if severity not in VALID_SEVERITIES:
            raise AuditError(
                f"additional defect {extra.get('description')!r} has invalid "
                f"severity {severity!r} (expected one of {sorted(VALID_SEVERITIES)})"
            )


# ---------------------------------------------------------------------------
# BlindedScoreLedger -- record_scores / unseal
# ---------------------------------------------------------------------------

class BlindedScoreLedger:
    """One run's blinded-scoring session: accumulates label-keyed scores
    (`record_scores`) and opens the sealed key exactly once, after every
    keyed label has a recorded score (`unseal`). See module docstring
    responsibility 2/3 for the full design rationale (why this is a small
    stateful object rather than bare functions).
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._scorecards_by_label: Dict[str, dict] = {}
        self._unsealed = False

    @property
    def scorecards_by_label(self) -> Dict[str, dict]:
        """Read-only view of everything recorded so far."""
        return dict(self._scorecards_by_label)

    def record_scores(
        self,
        label: str,
        checklist_results: List[dict],
        additional_defects: Optional[List[dict]] = None,
    ) -> Dict[str, dict]:
        """Record one labeled diff's scoring. Returns the full label-keyed
        scorecards dict accumulated so far. Raises AuditError if this
        ledger has already been unsealed (scoring must freeze strictly
        before the sealed key opens, D5), or if `checklist_results` /
        `additional_defects` don't conform to metrics.py's ScorecardRecord
        vocabulary.
        """
        if self._unsealed:
            raise AuditError(
                f"cannot record scores for label {label!r}: run_id "
                f"{self.run_id!r} has already been unsealed -- scoring must "
                "freeze strictly before the sealed key is opened (D5)"
            )

        additional_defects = additional_defects if additional_defects is not None else []
        _validate_checklist_results(checklist_results)
        _validate_additional_defects(additional_defects)

        self._scorecards_by_label[label] = {
            "checklist_results": checklist_results,
            "additional_defects": additional_defects,
        }
        return dict(self._scorecards_by_label)

    def unseal(
        self,
        sealed_key_path,
        run_ids_by_task: Dict[str, str],
    ) -> List[dict]:
        """Open the sealed key and join it against every recorded score,
        producing metrics-compatible ScorecardRecords. The ONLY method on
        this class (or in this module) that reads a sealed key file.

        Raises AuditError if:
          - this ledger has already been unsealed once,
          - the sealed key file is missing or unparsable,
          - any label present in the sealed key has no recorded score,
          - a keyed label's task has no entry in `run_ids_by_task` (cannot
            derive a metrics-compatible run_id for it -- see module
            docstring's "run_ids_by_task -- interface seam").
        """
        if self._unsealed:
            raise AuditError(
                f"run_id {self.run_id!r} has already been unsealed -- the "
                "sealed key may only be opened once per ledger"
            )

        path = pathlib.Path(sealed_key_path)
        if not path.is_file():
            raise AuditError(f"no such sealed key file: {sealed_key_path}")
        try:
            sealed_key = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise AuditError(
                f"could not read/parse sealed key {sealed_key_path}: {exc}"
            ) from exc

        missing = sorted(
            label for label in sealed_key if label not in self._scorecards_by_label
        )
        if missing:
            raise AuditError(
                f"unseal refused: label(s) {missing} appear in the sealed "
                f"key {sealed_key_path} but have no recorded score -- "
                "scoring must be complete before the key is opened (D5)"
            )

        records = []
        for label, mapping in sealed_key.items():
            task_id = mapping["task"]
            arm = mapping["arm"]
            if task_id not in run_ids_by_task:
                raise AuditError(
                    f"unseal refused: label {label!r} unseals to task "
                    f"{task_id!r}, which has no entry in run_ids_by_task -- "
                    "cannot derive a metrics-compatible run_id for it"
                )
            scored = self._scorecards_by_label[label]
            records.append({
                "task_id": task_id,
                "arm": arm,
                "run_id": f"{run_ids_by_task[task_id]}-{arm}",
                "checklist_results": scored["checklist_results"],
                "additional_defects": scored["additional_defects"],
            })

        self._unsealed = True
        return records
