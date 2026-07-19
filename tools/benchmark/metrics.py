"""A/B benchmark metrics layer (fg-a10405; T5 in the task decomposition of
docs/plans/2026-07-18-ab-benchmark-design.md §9).

Implements design decision **D6** ("Metrics: per pair, script-computable,
measured-or-proxy for tokens"), docs/plans/2026-07-18-ab-benchmark-design.md
lines ~196-211 (cited, never restated here). The proxy weight table is cited
verbatim from docs/audits/2026-07-18-protocol-overhead-audit.md §A.3
("Assumed weights (ESTIMATE, unverified)"), lines ~144-149.

Also honors **D7** ("Statistical honesty"), lines ~213-250: this module is
a *raw per-arm-run row* emitter only. It computes no aggregate, no blended
cost score, and nothing summed across arms -- "turns/attempts... Reported
per arm; never summed across arms (they count different things)" (D6). Any
pooled-within-class or cross-arm comparison belongs to the report layer
(T8), which must show every row behind any claim (D7, AC2).

-------------------------------------------------------------------------
INPUT CONTRACT -- this is the contract T3 (runner) and T7 (blinded-audit
harness) must produce for this module to consume. Kept minimal and
explicit per the fg-a10405 spawn brief; nothing here is inferred from
prose (e.g. Attempt-log FAIL notes are never string-parsed -- callers must
hand over structured `fail_item_ids`).

**RunRecord** (one JSON object per arm-run, produced by the runner):

    {
      "task_id":            str,   # e.g. "B1" -- matches design §3 task ids
      "arm":                "A" | "B",
      "run_id":              str,  # MUST be unique per arm-run across the
                                    # whole run_records list handed to
                                    # build_pair_rows -- NOT one id shared
                                    # by both arms of a pair. A runner that
                                    # emits one run_id per PAIR (e.g. the
                                    # pair's own run identifier) is not this
                                    # shape; the T6/T8 glue that flattens a
                                    # pair record into two RunRecords owns
                                    # deriving a per-arm id from it, e.g.
                                    # f"{pair_run_id}-{arm}". build_pair_rows
                                    # raises MetricsInputError on any
                                    # duplicate run_id rather than silently
                                    # guessing which arm a shared id belongs
                                    # to (fg-a10405 bounce 1).
      "model_tier":          str | null,  # "<model>/<effort>", e.g.
                                           # "sonnet/high" -- the builder's
                                           # tier; used only for the token
                                           # proxy (never for tokens
                                           # themselves)
      "wall_clock_seconds":  number,  # monotonic-clock seconds captured
                                       # by the runner, never self-reported
                                       # (D6 wall-clock row)
      "attempts": [
        {
          "kind": "dispatch" | "verify" | "re-verify" | "bounce",  # arm A
               # or "turn" for arm B (one entry per agent turn / tool
               # round-trip). The two vocabularies are disjoint by design
               # (ARM_A_ATTEMPT_KINDS / ARM_B_ATTEMPT_KINDS) -- an arm B
               # record must never carry an arm-A-shaped attempt and vice
               # versa, because "turns" count different things per arm
               # (D6) and must never be blended.
          "tokens": int | null,   # real usage reported by the harness
               # (fg-a10212's per-spawn capture) for this one attempt.
               # null means unreported for *this* attempt -- never a
               # stand-in for zero.
          "verdict": "PASS" | "FAIL" | "ESCALATE" | null,  # verify-kind
               # attempts only (arm A)
          "fail_item_ids": [str, ...]  # optional, default [];
               # checklist item ids (see ScorecardRecord below) the
               # verifier explicitly cited as the cause of a FAIL verdict
               # on *this* attempt. Structured, not prose -- this is how
               # compute_caught() works without parsing FAIL-note text.
        }, ...
      ]
    }

**ScorecardRecord** (one JSON object per labeled diff, produced by the
blinded-audit harness, joined back to (task_id, arm, run_id) only *after*
the sealed key is opened -- D5):

    {
      "task_id": str,
      "arm":     "A" | "B",
      "run_id":  str,
      "checklist_results": [
        {"item_id": str, "status": "satisfied" | "defect-present" | "n/a",
         "severity": "minor" | "important" | "critical" | null}
        # severity is required (non-null) when status == "defect-present",
        # otherwise ignored.
      ],
      "additional_defects": [
        {"description": str, "severity": "minor" | "important" | "critical"}
      ]
    }

Both shapes are validated defensively: a malformed record raises
MetricsInputError rather than being silently coerced or dropped, per the
task brief's "never invented" rule.
"""
import argparse
import json
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# Vocabulary / constants
# ---------------------------------------------------------------------------

VALID_ARMS = {"A", "B"}

# Disjoint by construction (D6: "Reported per arm; never summed across arms
# -- they count different things"). Checked by test_arm_kind_sets_are_disjoint.
ARM_A_ATTEMPT_KINDS = {"dispatch", "verify", "re-verify", "bounce"}
ARM_B_ATTEMPT_KINDS = {"turn"}

VERIFY_LIKE_KINDS = {"verify", "re-verify", "bounce"}

VALID_STATUSES = {"satisfied", "defect-present", "n/a"}
VALID_SEVERITIES = {"minor", "important", "critical"}

MODEL_TIER_RE = re.compile(r"^(haiku|sonnet|opus|fable)/(low|medium|high)$")

# Cited verbatim from docs/audits/2026-07-18-protocol-overhead-audit.md
# §A.3, "Assumed weights (ESTIMATE, unverified)" -- model multiplier x
# effort multiplier. Used ONLY as the turns-based cost proxy when no
# measured [tokens] data exists for a run (D6 tokens row); never used to
# adjust or override a measured figure.
PROXY_WEIGHTS = {
    ("haiku", "low"): 1,
    ("haiku", "medium"): 1.6,
    ("haiku", "high"): 2.5,
    ("sonnet", "low"): 5,
    ("sonnet", "medium"): 8,
    ("sonnet", "high"): 12.5,
    ("opus", "low"): 15,
    ("opus", "medium"): 24,
    ("opus", "high"): 37.5,
}


class MetricsInputError(ValueError):
    """Raised on a malformed RunRecord/ScorecardRecord, an unsupported
    arm/kind combination, or any other input that would otherwise force
    this module to guess or invent a value. Fail loud, never silently
    default (fg-a10405 brief: "metrics NEVER summed across arms, NEVER
    invented")."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require(condition, message):
    if not condition:
        raise MetricsInputError(message)


def _validate_run_record(rec):
    for key in ("task_id", "arm", "run_id", "wall_clock_seconds", "attempts"):
        _require(key in rec, f"run record missing required key {key!r}")
    _require(rec["arm"] in VALID_ARMS,
              f"run record has unknown arm {rec['arm']!r} (expected A or B)")
    allowed_kinds = ARM_A_ATTEMPT_KINDS if rec["arm"] == "A" else ARM_B_ATTEMPT_KINDS
    for attempt in rec["attempts"]:
        kind = attempt.get("kind")
        _require(
            kind in allowed_kinds,
            f"run record arm {rec['arm']!r} attempt kind {kind!r} not in "
            f"{sorted(allowed_kinds)} (arm A and arm B attempt vocabularies "
            "are disjoint -- they count different things, D6)",
        )


def parse_model_tier(model_tier):
    """Parse a "<model>/<effort>" string into (model, effort). Raises
    MetricsInputError on any shape or vocabulary this repo doesn't use --
    never guesses a nearest match."""
    _require(isinstance(model_tier, str) and MODEL_TIER_RE.match(model_tier),
              f"malformed model_tier {model_tier!r}; expected "
              "'<haiku|sonnet|opus|fable>/<low|medium|high>'")
    model, effort = model_tier.split("/", 1)
    return model, effort


# ---------------------------------------------------------------------------
# Per-run metrics
# ---------------------------------------------------------------------------

def compute_turns(run_record):
    """D6 "turns/attempts" row: arm A counts Attempt-log dispatch lines
    (build + verify + bounce + re-verify); arm B counts agent turns / tool
    round-trips. Never comparable/summable across arms."""
    _validate_run_record(run_record)
    return len(run_record["attempts"])


def compute_tokens(run_record):
    """D6 "tokens" row. Measured when at least one attempt carries a real
    `tokens` value (summed; flagged incomplete if some attempts are still
    null). Proxy (turns x audit A.3 weight, clearly labeled ESTIMATE) when
    none do and a model_tier is available. "unavailable" -- never a
    fabricated number -- when neither measured data nor a usable
    model_tier exists.

    Returns {"regime": "measured"|"proxy"|"unavailable",
             "value": number|None, "complete": bool|None, "note": str}.
    """
    _validate_run_record(run_record)
    attempts = run_record["attempts"]
    token_values = [a.get("tokens") for a in attempts]
    reported = [t for t in token_values if t is not None]

    if reported:
        value = sum(reported)
        complete = len(reported) == len(token_values)
        note = "measured: summed reported [tokens] suffix(es)"
        if not complete:
            missing = len(token_values) - len(reported)
            note += (f"; {missing} attempt(s) missing token data -- partial "
                      "sum only, nothing invented for the gap")
        return {"regime": "measured", "value": value, "complete": complete, "note": note}

    turns = len(attempts)
    model_tier = run_record.get("model_tier")
    if not model_tier:
        return {
            "regime": "unavailable", "value": None, "complete": None,
            "note": "tokens: unreported and no model_tier to compute a turn-based proxy",
        }

    model, effort = parse_model_tier(model_tier)
    weight = PROXY_WEIGHTS[(model, effort)]
    value = turns * weight
    note = (
        f"PROXY ESTIMATE (audit A.3 weights, unverified): {turns} turn(s) "
        f"x {weight} ({model_tier}) = {value}; tokens: unreported"
    )
    return {"regime": "proxy", "value": value, "complete": False, "note": note}


def compute_defects(scorecard):
    """D6 "defects (blinded)" row: checklist items marked defect-present
    plus any additional defects the auditor found, for one labeled diff.
    Returns a list of {"source": "checklist"|"additional", "item_id":
    str|None, "severity": str, "description": str|None}."""
    for key in ("task_id", "arm", "run_id", "checklist_results"):
        _require(key in scorecard, f"scorecard missing required key {key!r}")

    defects = []
    for item in scorecard["checklist_results"]:
        status = item.get("status")
        _require(status in VALID_STATUSES,
                  f"scorecard checklist item {item.get('item_id')!r} has "
                  f"unknown status {status!r}")
        if status != "defect-present":
            continue
        severity = item.get("severity")
        _require(severity in VALID_SEVERITIES,
                  f"scorecard checklist item {item.get('item_id')!r} is "
                  f"defect-present but has invalid severity {severity!r}")
        defects.append({
            "source": "checklist",
            "item_id": item.get("item_id"),
            "severity": severity,
            "description": None,
        })

    for extra in scorecard.get("additional_defects", []):
        severity = extra.get("severity")
        _require(severity in VALID_SEVERITIES,
                  f"scorecard additional defect {extra.get('description')!r} "
                  f"has invalid severity {severity!r}")
        defects.append({
            "source": "additional",
            "item_id": None,
            "severity": severity,
            "description": extra.get("description"),
        })

    return defects


def compute_caught(run_record, final_scorecard):
    """D6 "verifier-caught vs escaped" row, caught(armA) half:
    "defects appearing in a verifier FAIL note AND absent from the final
    diff." Arm-A only -- arm B has no verifier by construction (D6), so it
    can never have a caught set.

    `run_record` is arm A's own run record (its verify/re-verify/bounce
    attempts carry `fail_item_ids`); `final_scorecard` is the blinded
    auditor's scoring of arm A's *final* diff. Returns a sorted list of
    checklist item ids."""
    _validate_run_record(run_record)
    _require(run_record["arm"] == "A",
              "compute_caught is arm-A-only -- arm B has no verifier stage (D6)")
    _require(final_scorecard.get("arm") == "A",
              "final_scorecard must be arm A's own scoring, not a mismatched arm")

    fail_ids = set()
    for attempt in run_record["attempts"]:
        if attempt.get("kind") in VERIFY_LIKE_KINDS:
            fail_ids.update(attempt.get("fail_item_ids") or [])

    escaped_ids = {
        d["item_id"] for d in compute_defects(final_scorecard) if d["item_id"] is not None
    }
    return sorted(fail_ids - escaped_ids)


# ---------------------------------------------------------------------------
# Raw table -- per-pair, per-arm-run rows. No aggregate (D7/AC2).
# ---------------------------------------------------------------------------

def _validate_unique_run_ids(run_records):
    """run_id must be unique per arm-run across the whole list (see the
    RunRecord docstring). The historical defect this guards: a runner that
    emits one run_id per PAIR (shared by both arm A and arm B) would let
    build_pair_rows join a scorecard to the wrong arm silently. Refuse to
    consume an unreshaped pair-shaped record at all -- loud, before any
    join is attempted (fg-a10405 bounce 1)."""
    seen = set()
    dupes = set()
    for run in run_records:
        run_id = run.get("run_id")
        if run_id in seen:
            dupes.add(run_id)
        seen.add(run_id)
    if dupes:
        raise MetricsInputError(
            f"duplicate run_id(s) in run_records: {sorted(dupes)} -- run_id "
            "must be unique per arm-run (a shared per-pair run_id, e.g. "
            "runner.run_pair's raw output shape, must first be reshaped by "
            "the T6/T8 glue into per-arm ids such as f'{run_id}-{arm}'); "
            "refusing to guess which arm a shared id belongs to"
        )


def _index_by_run_id(scorecards):
    index = {}
    for sc in scorecards:
        run_id = sc.get("run_id")
        _require(run_id, "scorecard missing run_id -- cannot join to a run record")
        if run_id in index:
            raise MetricsInputError(
                f"duplicate run_id {run_id!r} across scorecards -- cannot "
                "join unambiguously; each scorecard must carry a run_id "
                "unique to the one arm-run it scores"
            )
        index[run_id] = sc
    return index


def build_pair_rows(run_records, scorecards):
    """Join RunRecords with ScorecardRecords (by run_id, post-key-unseal
    per D5) into one raw row per arm-run. A row never carries a value
    summed across arms -- only per-arm-run figures plus, for arm A, the
    caught/escaped split against its own final scorecard.

    Joins are validated, never assumed: run_id must be unique per arm-run
    (_validate_unique_run_ids), a scorecard's arm must match the run
    record's arm it joins to (never a cross-arm join on a shared id), and
    every scorecard must be consumed by exactly one run record -- an
    orphaned scorecard (run_id matching no run) raises rather than being
    silently dropped (fg-a10405 bounce 1: honesty over convenience)."""
    _validate_unique_run_ids(run_records)
    scorecard_index = _index_by_run_id(scorecards)
    consumed_run_ids = set()
    rows = []

    for run in run_records:
        _validate_run_record(run)
        turns = compute_turns(run)
        tokens = compute_tokens(run)

        row = {
            "task_id": run["task_id"],
            "arm": run["arm"],
            "run_id": run["run_id"],
            "wall_clock_seconds": run["wall_clock_seconds"],
            "turns": turns,
            "tokens_regime": tokens["regime"],
            "tokens_value": tokens["value"],
            "tokens_complete": tokens["complete"],
            "tokens_note": tokens["note"],
            "defects_escaped_count": None,
            "defects_escaped": None,
            "defects_caught_count": None,
            "defects_caught": None,
            "note": "",
        }

        scorecard = scorecard_index.get(run["run_id"])
        if scorecard is None:
            row["note"] = "no scorecard joined yet for this run_id"
            rows.append(row)
            continue

        consumed_run_ids.add(run["run_id"])
        _require(
            scorecard.get("arm") == run["arm"],
            f"scorecard for run_id={run['run_id']!r} has arm "
            f"{scorecard.get('arm')!r} but the run record it joins to is "
            f"arm {run['arm']!r} -- refusing a cross-arm join",
        )

        defects = compute_defects(scorecard)
        row["defects_escaped_count"] = len(defects)
        row["defects_escaped"] = defects

        if run["arm"] == "A":
            caught = compute_caught(run, scorecard)
            row["defects_caught_count"] = len(caught)
            row["defects_caught"] = caught
        # arm B: defects_caught_count/defects_caught stay None -- by
        # construction arm B has no verifier stage, so "caught" does not
        # apply to it (D6); this is a structural absence, not a zero.

        rows.append(row)

    orphaned = set(scorecard_index) - consumed_run_ids
    if orphaned:
        raise MetricsInputError(
            f"scorecard(s) with run_id(s) {sorted(orphaned)} do not match "
            "any run record -- orphaned scorecard, refusing to silently "
            "drop it"
        )

    return rows


def render_table(rows, fmt="text"):
    """Emit the raw per-arm-run table -- plain text or JSON, both
    script-computable, both row-for-row (no aggregate/summed-across-arm
    value is ever emitted here; that is out of scope for this module, D7)."""
    if fmt == "json":
        return json.dumps(rows, indent=2, sort_keys=True)

    _require(fmt == "text", f"unknown render_table format {fmt!r} (expected 'text' or 'json')")

    if not rows:
        return "(no rows)"

    columns = [
        "task_id", "arm", "run_id", "wall_clock_seconds", "turns",
        "tokens_regime", "tokens_value", "defects_escaped_count",
        "defects_caught_count",
    ]
    widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(row.get(c))))

    def _fmt_row(values):
        return "  ".join(str(v).ljust(widths[c]) for c, v in zip(columns, values))

    lines = [_fmt_row(columns), _fmt_row(["-" * widths[c] for c in columns])]
    for row in rows:
        lines.append(_fmt_row([row.get(c) for c in columns]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_json_records(path):
    """Load a JSON file expected to contain a top-level list of dicts
    (RunRecords or ScorecardRecords). Raises MetricsInputError on a
    missing file, unparsable JSON, or a non-list top level -- never
    returns a silently-empty list for a real error."""
    p = pathlib.Path(path)
    if not p.is_file():
        raise MetricsInputError(f"no such file: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetricsInputError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, list):
        raise MetricsInputError(f"{path} must contain a top-level JSON list, got {type(data).__name__}")
    return data


def main(argv):
    parser = argparse.ArgumentParser(prog="metrics", add_help=False)
    parser.add_argument("--run-records")
    parser.add_argument("--scorecards")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    if not args.run_records:
        sys.stderr.write("metrics: --run-records <path> is required\n")
        return 2

    try:
        run_records = load_json_records(args.run_records)
        scorecards = load_json_records(args.scorecards) if args.scorecards else []
        rows = build_pair_rows(run_records, scorecards)
        fmt = "json" if args.json else "text"
        print(render_table(rows, fmt=fmt))
    except MetricsInputError as exc:
        sys.stderr.write(f"metrics: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
