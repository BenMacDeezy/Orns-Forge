"""Rolling-window usage-index aggregator for kernel-minted archive-tier
agents (fg-b0304, spec-b71f3a "Usage tracking" AC10-AC12).

The kernel appends one record per archive-tier dispatch to
`.forge/agents/usage/<name>.jsonl` -- `{"ts": "<ISO-8601 UTC>", "task":
"<task-id or 'inline'>"}` -- as a kernel-owned write (workers never touch
`.forge/`), in the same dispatch step that increments the session's
dispatch count (skills/kernel/SKILL.md, ROUTE + DISPATCH,
"Mint-before-dispatch" / "Archive-tier"). This module reads those files
and computes per-agent dispatch counts within a caller-supplied rolling
window.

This is a NEW, independent artifact: it does not import from, and does
not modify, tools/telemetry.py -- that module's AGENT_SLUGS list and
Attempt-log parsing are untouched (AC11-AC12; tools/telemetry.py is being
actively modified by an in-flight worker per spec-b71f3a's Non-goals).
Usable both as a CLI and as a plain module import (fg-b0305,
usage-based promotion: 3+ dispatches within any rolling 14-day window).

Zero third-party dependencies.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

USAGE_DIR_DEFAULT = ".forge/agents/usage"
DEFAULT_WINDOW_DAYS = 14  # matches the usage-based promotion threshold


def _parse_ts(raw):
    """Parse an ISO-8601 UTC timestamp string into an aware UTC datetime.

    Accepts a trailing 'Z' (datetime.fromisoformat only accepts an
    explicit '+00:00'-style offset on Python < 3.11) as well as any
    other valid ISO-8601 offset. A naive timestamp (no offset, no 'Z')
    is treated as UTC, since the contract's records are always
    "<ISO-8601 UTC>". Raises ValueError on anything unparseable --
    callers treat that as a malformed line/value.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("ts is not a non-empty string")
    text = raw.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _normalize_now(now):
    if now is None:
        return dt.datetime.now(dt.timezone.utc)
    if isinstance(now, str):
        return _parse_ts(now)
    if now.tzinfo is None:
        return now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(dt.timezone.utc)


def load_usage(usage_dir):
    """Read every `<name>.jsonl` file under usage_dir.

    Returns `{agent_name: [aware UTC datetime, ...]}`, each agent's list
    sorted ascending. A missing or empty usage_dir returns `{}` -- never
    an error. A malformed line (invalid JSON, not a JSON object, missing
    or empty `ts`/`task`, or an unparseable `ts`) is skipped with a
    one-line note to stderr; it never raises and never aborts the rest
    of the file or the other files in the directory.
    """
    usage_dir = pathlib.Path(usage_dir)
    result = {}
    if not usage_dir.is_dir():
        return result

    for path in sorted(usage_dir.glob("*.jsonl")):
        agent_name = path.stem
        timestamps = []
        try:
            raw_text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            print(
                f"agent_usage: skipping unreadable file {path}: {exc}",
                file=sys.stderr,
            )
            continue

        for lineno, line in enumerate(raw_text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("line is not a JSON object")
                task = record.get("task")
                if not isinstance(task, str) or not task.strip():
                    raise ValueError("'task' is not a non-empty string")
                ts = _parse_ts(record.get("ts"))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                print(
                    f"agent_usage: skipping malformed line {lineno} in "
                    f"{path.name}: {exc}",
                    file=sys.stderr,
                )
                continue
            timestamps.append(ts)

        if timestamps:
            timestamps.sort()
            result[agent_name] = timestamps

    return result


def count_dispatches(usage_dir, window_days, now=None):
    """Per-agent dispatch counts within the rolling window
    `[now - window_days days, now]` (both ends inclusive).

    `now` defaults to the current UTC time; pass an ISO-8601 string or a
    datetime (naive datetimes are treated as UTC) for deterministic
    tests. An agent with zero dispatches inside the window is omitted
    from the result -- a missing/empty usage dir yields `{}`.
    """
    now = _normalize_now(now)
    window_start = now - dt.timedelta(days=window_days)

    usage = load_usage(usage_dir)
    counts = {}
    for agent_name, timestamps in usage.items():
        n = sum(1 for ts in timestamps if window_start <= ts <= now)
        if n:
            counts[agent_name] = n
    return counts


def _parse_now_arg(raw):
    try:
        return _parse_ts(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--now must be an ISO-8601 timestamp: {exc}"
        )


def main(argv=None):
    # Windows-safe: an em dash or similar in this module's own output
    # would otherwise crash under a legacy Windows OEM codepage (same
    # rationale as tools/status.py / tools/validate_task.py).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="agent_usage.py",
        description="Per-agent dispatch counts within a rolling window, "
                     "from .forge/agents/usage/*.jsonl.",
    )
    parser.add_argument(
        "--usage-dir", default=USAGE_DIR_DEFAULT,
        help=f"directory of <name>.jsonl usage-index files "
             f"(default: {USAGE_DIR_DEFAULT})",
    )
    parser.add_argument(
        "--window-days", type=int, default=DEFAULT_WINDOW_DAYS,
        help="rolling window size in days (default: "
             f"{DEFAULT_WINDOW_DAYS}, matching the usage-based promotion "
             "threshold)",
    )
    parser.add_argument(
        "--now", type=_parse_now_arg, default=None,
        help="ISO-8601 UTC override for 'now' (testability); default is "
             "the current UTC time",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="emit JSON instead of a text table",
    )
    args = parser.parse_args(argv)

    if args.window_days <= 0:
        print("agent_usage: --window-days must be positive", file=sys.stderr)
        return 1

    counts = count_dispatches(args.usage_dir, args.window_days, now=args.now)

    if args.json:
        print(json.dumps(counts, indent=2, sort_keys=True))
    elif not counts:
        print("(no dispatches in window)")
    else:
        width = max(len(name) for name in counts)
        for name in sorted(counts, key=lambda n: (-counts[n], n)):
            print(f"{name:<{width}}  {counts[name]}")

    return 0  # read-only reporter: always exits 0 on a valid run


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
