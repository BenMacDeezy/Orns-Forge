#!/usr/bin/env python3
"""Forge watchdog (fg-a10211): stdlib-only, read-only detector for hung
workers, runaway agents, stale claims, duplicate tasks, and attempt-cap
breaches -- plus a --check-report mode that mechanically verifies a
worker's RETURN report against reality. Zero dependencies (frontmatter and
section parsing reuse validate_task's private helpers, per the task
contract, instead of a YAML dependency).

Canonical thresholds live in ONE dated conventions section: docs/conventions.md,
"Watchdog thresholds -- 2026-07-20" (defaults: hung 10 min, runaway 2 MB or
5 identical repeats, stale claim 4 h, title similarity 0.85, attempt cap 3),
overridable per-project via `.forge/forge.md`'s `## Features` section as
`watchdog-<name>: <value>` bullet lines.

Transcript convention: the harness task-output dir passed via --task-dir
holds one plain-text transcript file per in-flight task, named
"<task-id>.transcript". Lines beginning with "$ " are treated as command
echoes; RUNAWAY's repeat check inspects the most recent COMMAND_TAIL such
lines for a run of identical repeats.

Quiet by default: a healthy run prints NOTHING and exits 0, so it is safe
to run on every kernel fallback wakeup at ~zero token cost (docs/conventions.md,
"Idle-wait discipline -- 2026-07"). Each flag prints exactly one line.
"""
import argparse
import difflib
import pathlib
import re
import sys
from datetime import datetime, timezone

_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_task  # frontmatter + section-body helpers, no YAML dep

# ---------------------------------------------------------------------------
# Canonical defaults (docs/conventions.md, "Watchdog thresholds — 2026-07-20")
# ---------------------------------------------------------------------------

DEFAULTS = {
    "hung-minutes": 10.0,
    "runaway-bytes": 2 * 1024 * 1024,
    "runaway-repeats": 5,
    "runaway-commands": 50,
    "stale-claim-hours": 4.0,
    "title-similarity": 0.85,
    "attempt-cap": 3,
}

# How many trailing "$ " command lines RUNAWAY's repeat check inspects.
COMMAND_TAIL = 20

CLAIMED_BY_RE = re.compile(
    r"^sess-[0-9a-f]{4} @ (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$")
ATTEMPT_LINE_RE = re.compile(r"(?m)^attempt (\d+)\b")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
FEATURES_ITEM_RE = re.compile(r"(?m)^-\s*watchdog-([a-z-]+):\s*(\S+)")
_NORM_STRIP_RE = re.compile(r"[^a-z0-9 ]+")


def _parse_iso(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Threshold + task loading
# ---------------------------------------------------------------------------

def load_thresholds(forge_md_path):
    """Read watchdog-* overrides from forge.md's `## Features` section
    (bullet lines `- watchdog-<key>: <value>`). Any key absent, malformed,
    or unrecognized silently keeps the canonical DEFAULTS value -- matching
    the "every missing toggle behaves as its default" Features rule."""
    thresholds = dict(DEFAULTS)
    path = pathlib.Path(forge_md_path)
    if not path.is_file():
        return thresholds
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return thresholds
    body = validate_task._section_body(text, "## Features")
    if not body:
        return thresholds
    for m in FEATURES_ITEM_RE.finditer(body):
        key, raw = m.group(1), m.group(2)
        if key not in DEFAULTS:
            continue
        try:
            value = float(raw) if "." in raw else int(raw)
        except ValueError:
            continue
        thresholds[key] = value
    return thresholds


def load_tasks(forge_dir):
    """[{id, title, state, claimed_by, body, path}, ...] for every *.md file
    directly under <forge_dir>/queue/tasks/. Malformed files (no parseable
    frontmatter) are silently skipped -- watchdog is a best-effort read-only
    reporter, not a validator (that's tools/validate_task.py's job)."""
    tasks = []
    tasks_dir = pathlib.Path(forge_dir) / "queue" / "tasks"
    if not tasks_dir.is_dir():
        return tasks
    for p in sorted(tasks_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        fields, _errors, body = validate_task._parse_frontmatter(text)
        if fields is None:
            continue
        tasks.append({
            "id": fields.get("id", p.stem),
            "title": fields.get("title", ""),
            "state": fields.get("state", ""),
            "claimed_by": fields.get("claimed-by", "null"),
            "body": body or "",
            "path": p,
        })
    return tasks


def _transcript_path(task_dir, task_id):
    p = pathlib.Path(task_dir) / f"{task_id}.transcript"
    return p if p.is_file() else None


# ---------------------------------------------------------------------------
# Flag classes
# ---------------------------------------------------------------------------

def check_hung(tasks, task_dir, now, threshold_minutes):
    """HUNG: a claimed (state: active) task whose worker transcript file has
    not grown (mtime) for >= threshold_minutes."""
    flags = []
    for t in tasks:
        if t["state"] != "active" or not t["claimed_by"] or t["claimed_by"] == "null":
            continue
        tp = _transcript_path(task_dir, t["id"])
        if tp is None:
            continue
        mtime = datetime.fromtimestamp(tp.stat().st_mtime, tz=timezone.utc)
        idle_minutes = (now - mtime).total_seconds() / 60.0
        if idle_minutes >= threshold_minutes:
            flags.append(
                f"HUNG {t['id']}: transcript {tp} idle {idle_minutes:.1f}m "
                f"(>= {threshold_minutes}m threshold) -- suggested: check "
                f"worker liveness, consider killing and recovering the claim"
            )
    return flags


def check_runaway(tasks, task_dir, byte_budget, repeat_threshold,
                  command_budget=None):
    """RUNAWAY: transcript beyond a byte budget, an identical "$ " command
    repeated >= repeat_threshold times in the trailing command tail, OR the
    total "$ " command count >= command_budget (a hard per-worker
    tool/command ceiling — catches a worker churning many DISTINCT commands,
    which the identical-repeat check alone misses; e.g. a palette task that
    fans out to 80 tool calls). command_budget=None disables that check."""
    flags = []
    for t in tasks:
        if t["state"] != "active" or not t["claimed_by"] or t["claimed_by"] == "null":
            continue
        tp = _transcript_path(task_dir, t["id"])
        if tp is None:
            continue
        size = tp.stat().st_size
        if size > byte_budget:
            flags.append(
                f"RUNAWAY {t['id']}: transcript {tp} size {size}B "
                f"(> {byte_budget}B budget) -- suggested: inspect the "
                f"transcript, consider killing/re-dispatching the worker"
            )
            continue
        try:
            lines = tp.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        commands = [ln for ln in lines if ln.startswith("$ ")]
        if command_budget is not None and len(commands) >= command_budget:
            flags.append(
                f"RUNAWAY {t['id']}: transcript {tp} ran {len(commands)} "
                f"commands (>= {command_budget} budget) -- suggested: worker "
                f"is over its tool/command ceiling, kill/re-dispatch with a "
                f"tighter scope"
            )
            continue
        tail = commands[-COMMAND_TAIL:]
        if not tail:
            continue
        last = tail[-1]
        run = 0
        for ln in reversed(tail):
            if ln == last:
                run += 1
            else:
                break
        if run >= repeat_threshold:
            flags.append(
                f"RUNAWAY {t['id']}: transcript {tp} repeated command "
                f"{last[2:].strip()!r} x{run} (>= {repeat_threshold} "
                f"threshold) -- suggested: worker likely stuck in a retry "
                f"loop, kill/re-dispatch"
            )
    return flags


def check_stale_claim(tasks, now, threshold_hours):
    """STALE-CLAIM: claimed-by older than threshold_hours with no new
    Attempt-log line since the claim -- judged statelessly by comparing the
    claim timestamp to the latest ISO timestamp found in the Attempt log
    body (no timestamp at/after the claim => no activity since claiming)."""
    flags = []
    for t in tasks:
        if t["state"] != "active":
            continue
        m = CLAIMED_BY_RE.match(t["claimed_by"] or "")
        if not m:
            continue
        claimed_at = _parse_iso(m.group(1))
        age_hours = (now - claimed_at).total_seconds() / 3600.0
        if age_hours < threshold_hours:
            continue
        attempt_body = validate_task._section_body(t["body"], "## Attempt log") or ""
        timestamps = [_parse_iso(ts) for ts in TIMESTAMP_RE.findall(attempt_body)]
        if timestamps and max(timestamps) >= claimed_at:
            continue  # attempt log has activity at/after the claim
        flags.append(
            f"STALE-CLAIM {t['id']}: claimed-by {t['claimed_by']} age "
            f"{age_hours:.1f}h (>= {threshold_hours}h threshold), no "
            f"Attempt-log activity since claim -- suggested: recover the "
            f"claim (reset claimed-by to null, requeue)"
        )
    return flags


def _normalize_title(title):
    t = (title or "").strip().strip('"').strip("'").lower()
    t = _NORM_STRIP_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def check_duplicates(tasks, similarity_threshold):
    """DUPLICATE-TASK: non-done tasks whose normalized titles' similarity
    (difflib.SequenceMatcher ratio) meets or exceeds similarity_threshold."""
    flags = []
    candidates = [t for t in tasks if t["state"] != "done"]
    seen_pairs = set()
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a, b = candidates[i], candidates[j]
            na, nb = _normalize_title(a["title"]), _normalize_title(b["title"])
            if not na or not nb:
                continue
            ratio = difflib.SequenceMatcher(None, na, nb).ratio()
            if ratio >= similarity_threshold:
                pair = tuple(sorted((a["id"], b["id"])))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                flags.append(
                    f"DUPLICATE-TASK {pair[0]}/{pair[1]}: title similarity "
                    f"{ratio:.2f} (>= {similarity_threshold} threshold) -- "
                    f"suggested: review for merge, drop the redundant task"
                )
    return flags


def check_attempt_cap(tasks, cap):
    """ATTEMPT-CAP: highest "attempt N" number in the Attempt log exceeds
    the bounce cap."""
    flags = []
    for t in tasks:
        attempt_body = validate_task._section_body(t["body"], "## Attempt log") or ""
        numbers = [int(n) for n in ATTEMPT_LINE_RE.findall(attempt_body)]
        if not numbers:
            continue
        highest = max(numbers)
        if highest > cap:
            flags.append(
                f"ATTEMPT-CAP {t['id']}: attempt {highest} (> {cap} bounce "
                f"cap) -- suggested: escalate tier/model or route to "
                f"forge-architect instead of another bounce"
            )
    return flags


# ---------------------------------------------------------------------------
# --check-report mode
# ---------------------------------------------------------------------------

_FILES_SECTION_RE = re.compile(
    r"(?ms)^FILES CHANGED:\s*\n(.*?)(?=^[A-Z][A-Z -]*:\s*$|\Z)")
_FILE_BULLET_RE = re.compile(r"(?m)^-\s*([^:\n]+):")
_BACKTICK_PATH_RE = re.compile(r"`([\w./\\-]+\.[A-Za-z0-9_]+)`")
_GATE_COUNT_RE = re.compile(r"(\d+)\s+passed")


def check_report(report_text, repo_root, gate_output_text=None):
    """Mechanically verify a worker RETURN report's checkable claims:
    - every path named in "FILES CHANGED:" bullets exists
    - every backtick-quoted path elsewhere in the report resolves
    - (when gate_output_text is supplied) the report's most recently cited
      "N passed" count matches gate_output_text's most recent "N passed"

    Prose-quality judgment (is the summary accurate) is explicitly out of
    scope -- this only checks claims a script can verify mechanically.
    Returns one "REPORT-MISMATCH ..." line per mismatch found.
    """
    flags = []
    repo_root = pathlib.Path(repo_root)

    claimed_paths = []
    m = _FILES_SECTION_RE.search(report_text)
    if m:
        claimed_paths.extend(p.strip() for p in _FILE_BULLET_RE.findall(m.group(1)))
    claimed_paths.extend(_BACKTICK_PATH_RE.findall(report_text))

    seen = set()
    for raw in claimed_paths:
        raw = raw.strip().strip("`")
        if not raw or raw in seen:
            continue
        seen.add(raw)
        p = pathlib.Path(raw)
        if not p.is_absolute():
            p = repo_root / p
        if not p.exists():
            flags.append(
                f"REPORT-MISMATCH file: claimed {raw!r} exists, actual not found"
            )

    if gate_output_text is not None:
        claimed = _GATE_COUNT_RE.findall(report_text)
        actual = _GATE_COUNT_RE.findall(gate_output_text)
        if claimed and actual and claimed[-1] != actual[-1]:
            flags.append(
                f"REPORT-MISMATCH test-count: claimed {claimed[-1]} passed, "
                f"actual gate output shows {actual[-1]} passed"
            )

    return flags


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Forge watchdog: read-only detector for hung/runaway "
                     "workers, stale claims, duplicate tasks, and "
                     "attempt-cap breaches. Quiet on a healthy run.")
    parser.add_argument("--forge-dir", default=".forge",
                         help="path to the .forge/ directory (default: .forge)")
    parser.add_argument("--task-dir", default=None,
                         help="harness worker-output dir holding "
                              "<task-id>.transcript files, for HUNG/RUNAWAY")
    parser.add_argument("--now", default=None,
                         help="ISO8601 UTC override for 'now' (testing)")
    parser.add_argument("--check-report", action="store_true",
                         help="read a worker RETURN report on stdin and "
                              "check mechanical claims instead of scanning")
    parser.add_argument("--gate-output", default=None,
                         help="file with real gate output text, for "
                              "--check-report test-count verification")
    parser.add_argument("--repo-root", default=".",
                         help="root paths are resolved against in "
                              "--check-report mode (default: .)")
    args = parser.parse_args(argv)

    now = _parse_iso(args.now) if args.now else datetime.now(timezone.utc)

    if args.check_report:
        report_text = sys.stdin.read()
        gate_text = None
        if args.gate_output:
            gate_text = pathlib.Path(args.gate_output).read_text(encoding="utf-8")
        for line in check_report(report_text, args.repo_root, gate_text):
            print(line)
        return 0

    thresholds = load_thresholds(pathlib.Path(args.forge_dir) / "forge.md")
    tasks = load_tasks(args.forge_dir)

    flags = []
    if args.task_dir:
        flags += check_hung(tasks, args.task_dir, now, thresholds["hung-minutes"])
        flags += check_runaway(
            tasks, args.task_dir, thresholds["runaway-bytes"],
            thresholds["runaway-repeats"], thresholds["runaway-commands"])
    flags += check_stale_claim(tasks, now, thresholds["stale-claim-hours"])
    flags += check_duplicates(tasks, thresholds["title-similarity"])
    flags += check_attempt_cap(tasks, thresholds["attempt-cap"])

    for line in flags:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
