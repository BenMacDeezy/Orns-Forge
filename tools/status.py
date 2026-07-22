"""Render the canonical Forge queue status board (fg-a10214). Zero
dependencies. This is the SCRIPT-ONLY fast path for /forge:status: a pure
data query over `.forge/queue/tasks/*.md` frontmatter, previously rendered
by an LLM (skill load + N task-file reads + generated table), which in a
real session took 90+ seconds for what is under a second of real work.

The canonical rendering rules this module implements are NORMATIVE in
skills/queue/references/status-board.md -- that file and this module must
never diverge; this module IS the renderer of record, the reference is its
normative spec (and the fallback path when this script errors).

Reuses validate_task's frontmatter/section parsing and validate_config's
forge.md section parsing rather than reinventing either -- same pattern
tools/queue_graph.py already established for frontmatter reuse.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys

_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import scope_guard
import validate_config
import validate_task

TASK_DIR_DEFAULT = ".forge/queue/tasks"
FORGE_MD_DEFAULT = ".forge/forge.md"

DEFAULT_CAP = 15
BACKLOG_STALE_DAYS = 14
DEFAULT_CLAIM_STALENESS_HOURS = 0.5

STATE_ORDER = ("backlog", "ready", "active", "blocked", "done", "dropped")

OMISSION_TEMPLATE = (
    "{n} more not shown — run `/forge:status all` to see everything "
    "(or `/forge:status <state>` to filter)."
)

_CLAIMED_BY_TS_RE = re.compile(
    r"^sess-[0-9a-f]{4} @ (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$"
)


# ---------------------------------------------------------------------------
# Date/time helpers
# ---------------------------------------------------------------------------

def _iso_to_dt(value):
    """Parse a created/updated/claimed-by-style ISO date or datetime string
    to an aware UTC datetime, or None if unparseable. Accepts 'YYYY-MM-DD'
    (treated as midnight UTC) or 'YYYY-MM-DDTHH:MM:SSZ'. Never raises."""
    if not isinstance(value, str) or not value:
        return None
    value = value.strip()
    try:
        if value.endswith("Z") and len(value) == 20:
            return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt.timezone.utc
            )
        if len(value) == 10:
            return dt.datetime.strptime(value, "%Y-%m-%d").replace(
                tzinfo=dt.timezone.utc
            )
    except ValueError:
        return None
    return None


# ---------------------------------------------------------------------------
# Task loading -- reuses validate_task._parse_frontmatter (same pattern as
# tools/queue_graph.py). Malformed/missing frontmatter, bad state, and
# duplicate ids are all skipped with a one-line note, never crash.
# ---------------------------------------------------------------------------

def load_tasks(task_dir):
    """Read every *.md task file in task_dir. Returns (tasks, skipped)
    where tasks maps id -> record dict and skipped is a list of one-line
    human-readable notes for files that could not be parsed as a valid
    task. Never raises; a missing/unreadable directory yields ({}, [])."""
    task_dir = pathlib.Path(task_dir)
    tasks = {}
    skipped = []
    try:
        paths = sorted(
            p for p in task_dir.glob("*.md")
            if p.is_file() and p.stat().st_size > 0
        )
    except OSError:
        return tasks, skipped

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            skipped.append(f"{path.name} (unreadable)")
            continue

        fm, fm_errors, body = validate_task._parse_frontmatter(text)
        if fm is None or body is None:
            skipped.append(f"{path.name} (missing or malformed frontmatter)")
            continue
        if any("inline list" in err for err in fm_errors):
            skipped.append(f"{path.name} (malformed blocked-by/blocks list)")
            continue

        task_id = fm.get("id")
        state = fm.get("state")
        if not task_id or state not in validate_task.STATES:
            skipped.append(f"{path.name} (missing id or bad state)")
            continue
        if task_id in tasks:
            skipped.append(f"{path.name} (duplicate id {task_id!r})")
            continue

        blocked_by = fm.get("blocked-by")
        if not isinstance(blocked_by, list):
            blocked_by = [] if blocked_by in (None, "", "[]") else [blocked_by]
        blocked_by = [b.strip() if isinstance(b, str) else b for b in blocked_by if b]

        priority_raw = fm.get("priority")
        try:
            priority = int(priority_raw)
        except (TypeError, ValueError):
            priority = 999

        tasks[task_id] = {
            "id": task_id,
            "title": fm.get("title") or task_id,
            "state": state,
            "tier": fm.get("tier") or "",
            "priority": priority,
            "blocked_by": blocked_by,
            "claimed_by": fm.get("claimed-by") or "null",
            "created": fm.get("created") or "",
            "updated": fm.get("updated") or "",
            "body": body,
        }

    return tasks, skipped


def _sort_key(t):
    return (t["priority"], t["created"] or "", t["id"])


# ---------------------------------------------------------------------------
# Outcome / Attempt-log helpers, shared by the blocked-first and
# backlog-needs-info sections.
# ---------------------------------------------------------------------------

# Known empty-section markers, per docs/conventions.md ("(pending)" for an
# unstarted Execution plan/Attempt log/Outcome) and real-world usage in this
# queue ("(none)" -- 5 live task files use it as their Attempt-log empty
# marker; tools/telemetry.py recognizes the same token). Deliberately an
# exact-match set, not a "any parenthesized text" pattern -- a real note can
# also be a single fully-parenthesized line (e.g. fg-a10702's Attempt log,
# "(backlog -- created from the 2026-07-18 scout audit; loop in on user's
# word)"), and a broad regex would wrongly swallow that as a placeholder.
_PLACEHOLDER_MARKERS = ("(pending)", "(none)")


def _placeholder_or_empty(section_text):
    if not section_text:
        return True
    t = section_text.strip()
    return t == "" or t in _PLACEHOLDER_MARKERS


def _first_nonempty_line(section_text):
    if not section_text:
        return None
    for line in section_text.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def needs_info_note(body):
    """First non-empty line of Outcome; if Outcome is empty/'(pending)',
    fall back to the first non-empty line of Attempt log. None if neither
    has non-placeholder content (task doesn't qualify as needs-info)."""
    outcome = validate_task._section_body(body, "## Outcome")
    if not _placeholder_or_empty(outcome):
        return _first_nonempty_line(outcome)
    attempt = validate_task._section_body(body, "## Attempt log")
    if not _placeholder_or_empty(attempt):
        return _first_nonempty_line(attempt)
    return None


def blocked_reason(body):
    """One-line blocker note from a blocked task's Outcome section."""
    outcome = validate_task._section_body(body, "## Outcome")
    if not _placeholder_or_empty(outcome):
        line = _first_nonempty_line(outcome)
        if line:
            return line
    return "no blocker note recorded"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def build_blocked_section(tasks):
    """1. Blocked first: every `blocked`-state task (id, title, one-line
    Outcome blocker), plus any `ready` task whose blocked-by references a
    `dropped` or missing task id, flagged as blocked-for-display."""
    lines = []
    for task_id in sorted(tasks, key=lambda i: _sort_key(tasks[i])):
        t = tasks[task_id]
        if t["state"] == "blocked":
            lines.append(f"- {task_id}: {t['title']} — {blocked_reason(t['body'])}")
        elif t["state"] == "ready":
            for bid in t["blocked_by"]:
                blocker = tasks.get(bid)
                if blocker is None:
                    lines.append(
                        f"- {task_id}: {t['title']} — blocked-for-display: "
                        f"blocked-by references {bid} (missing)"
                    )
                    break
                if blocker["state"] == "dropped":
                    lines.append(
                        f"- {task_id}: {t['title']} — blocked-for-display: "
                        f"blocked-by references {bid} (dropped)"
                    )
                    break
    return lines


def build_board_section(tasks, scope):
    """2. Board: counts per state, then the id/title/state/tier/priority/
    blocked-by/claimed-by table, priority ascending then created ascending.

    scope is None (default: non-done AND non-dropped, capped at 15 +
    omission line), "all" (non-done and non-dropped, uncapped), or a
    specific state (that state only, uncapped -- the ONLY way to see
    done/dropped rows, per the reference)."""
    counts = {s: 0 for s in STATE_ORDER}
    for t in tasks.values():
        counts[t["state"]] = counts.get(t["state"], 0) + 1
    counts_line = "Counts — " + ", ".join(
        f"{s}: {counts[s]}" for s in STATE_ORDER
    )

    omitted = 0
    if scope is None:
        pool = sorted(
            (t for t in tasks.values() if t["state"] not in ("done", "dropped")),
            key=_sort_key,
        )
        rows = pool[:DEFAULT_CAP]
        omitted = len(pool) - len(rows)
    elif scope == "all":
        rows = sorted(
            (t for t in tasks.values() if t["state"] not in ("done", "dropped")),
            key=_sort_key,
        )
    else:
        rows = sorted(
            (t for t in tasks.values() if t["state"] == scope), key=_sort_key
        )

    lines = [counts_line, ""]
    if not rows:
        if scope in (None, "all"):
            lines.append("No tasks to show.")
        else:
            lines.append(f"No tasks in state `{scope}`.")
        return lines

    lines.append("| id | title | state | tier | priority | blocked-by | claimed-by |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for t in rows:
        title = str(t["title"]).replace("|", "\\|")
        blocked_by = ", ".join(t["blocked_by"]) if t["blocked_by"] else "-"
        claimed_by = t["claimed_by"] if t["claimed_by"] not in (None, "", "null") else "-"
        lines.append(
            f"| {t['id']} | {title} | {t['state']} | {t['tier']} | "
            f"{t['priority']} | {blocked_by} | {claimed_by} |"
        )
    if omitted > 0:
        lines.append("")
        lines.append(OMISSION_TEMPLATE.format(n=omitted))
    return lines


def build_backlog_section(tasks, now):
    """3. Backlog needing info: needs-info note and/or [stale-backlog]
    (updated older than BACKLOG_STALE_DAYS). A task with neither is
    omitted entirely."""
    lines = []
    for task_id in sorted(tasks, key=lambda i: _sort_key(tasks[i])):
        t = tasks[task_id]
        if t["state"] != "backlog":
            continue
        note = needs_info_note(t["body"])
        updated_dt = _iso_to_dt(t["updated"])
        stale = False
        if updated_dt is not None:
            age_days = (now - updated_dt).total_seconds() / 86400.0
            stale = age_days > BACKLOG_STALE_DAYS
        if note is None and not stale:
            continue
        markers = "[needs-info]" if note is not None else ""
        if stale:
            markers = (markers + " [stale-backlog]").strip()
        if note is not None:
            lines.append(f"- {task_id} {markers}: {note}")
        else:
            lines.append(f"- {task_id} {markers}")
    return lines


def build_stale_claims_section(tasks, now, claim_staleness_hours):
    """4. Stale claims: any active claim older than forge.md's
    claim-staleness-hours."""
    lines = []
    for task_id in sorted(tasks, key=lambda i: _sort_key(tasks[i])):
        t = tasks[task_id]
        if t["state"] != "active":
            continue
        claimed = t["claimed_by"]
        if not claimed or claimed == "null":
            continue
        m = _CLAIMED_BY_TS_RE.match(claimed)
        if not m:
            continue
        claimed_dt = _iso_to_dt(m.group(1))
        if claimed_dt is None:
            continue
        age_hours = (now - claimed_dt).total_seconds() / 3600.0
        if age_hours > claim_staleness_hours:
            lines.append(
                f"- {task_id}: claimed {claimed} "
                f"(stale, > {claim_staleness_hours}h)"
            )
    return lines


# ---------------------------------------------------------------------------
# forge.md's claim-staleness-hours -- reuses validate_config's section/item
# parsing rather than reinventing forge.md's bullet-line format.
# ---------------------------------------------------------------------------

def load_claim_staleness_hours(forge_md_path):
    path = pathlib.Path(forge_md_path)
    if not path.is_file():
        return DEFAULT_CLAIM_STALENESS_HOURS
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return DEFAULT_CLAIM_STALENESS_HOURS
    text = validate_config._strip_html_comments(text)
    queue_body = validate_config._section_body(text, "## Queue")
    if not queue_body:
        return DEFAULT_CLAIM_STALENESS_HOURS
    items = validate_config._parse_items(queue_body, [], "Queue")
    v = items.get("claim-staleness-hours")
    if v is None:
        return DEFAULT_CLAIM_STALENESS_HOURS
    try:
        parsed = float(v)
    except ValueError:
        return DEFAULT_CLAIM_STALENESS_HOURS
    return parsed if parsed > 0 else DEFAULT_CLAIM_STALENESS_HOURS


# ---------------------------------------------------------------------------
# Scope guard advisory (project-scope-guard, 2026-07-20) -- status.py is a
# READ-ONLY surface, so unlike the kernel SYNC guard and the queue-skill
# write-path guard (which STOP and ask a human), a mismatch or git-error
# here is one advisory line, never a block. Full rule:
# skills/kernel/references/scope-guard.md (NORMATIVE).
# ---------------------------------------------------------------------------

def scope_warning(forge_dir, project_dir=None, env=None):
    """One advisory line if `forge_dir` is not the current project's
    root-level `.forge/`, or project git resolution fails. Never blocks.

    Project identity precedence is explicit `project_dir`, then
    `CLAUDE_PROJECT_DIR`, then the real process cwd. In particular,
    `--root` selects the state to display; it does not self-validate that
    state as the current project.
    """
    forge_path = pathlib.Path(forge_dir)
    if project_dir is None:
        project_dir = scope_guard.resolve_project_dir(
            env=env, cwd=os.getcwd()
        )
    result = scope_guard.check_scope(
        forge_path, project_dir=project_dir,
    )
    if result.match:
        return None
    if result.reason == "git-error":
        return (
            f"SCOPE WARNING: Git could not resolve this project's "
            f"toplevel, so Forge cannot verify this .forge/ "
            f"({result.actual}). Advisory only, not blocking "
            "(docs/conventions.md, \"Project scope guard — "
            "2026-07-20 (project-scope-guard)\")."
        )
    return (
        f"SCOPE WARNING: this .forge/ ({result.actual}) is not this "
        f"project's own — expected {result.expected}. Advisory only, "
        "not blocking (docs/conventions.md, \"Project scope guard — "
        "2026-07-20 (project-scope-guard)\")."
    )


# ---------------------------------------------------------------------------
# Top-level render
# ---------------------------------------------------------------------------

def render_board(task_dir, forge_md_path, scope=None, now=None,
                  project_dir=None, env=None):
    """Render the full board (sections 1-5) as a plain markdown string,
    per skills/queue/references/status-board.md. Never raises. When
    `task_dir`'s `.forge/` is not canonical-path-equal to this project's
    root-level `.forge/`, prepends one advisory line -- never blocks."""
    now = now or dt.datetime.now(dt.timezone.utc)
    task_dir = pathlib.Path(task_dir)
    forge_dir = task_dir.parent.parent  # <root>/.forge/queue/tasks -> <root>/.forge
    warning = scope_warning(forge_dir, project_dir=project_dir, env=env)
    prefix = (warning + "\n\n") if warning else ""

    if not task_dir.is_dir():
        return prefix + "`.forge/queue/tasks` not found — nothing to show."

    tasks, skipped = load_tasks(task_dir)
    if not tasks:
        return prefix + "`.forge/queue/tasks` is empty — nothing to show."

    claim_staleness_hours = load_claim_staleness_hours(forge_md_path)

    out = []

    blocked_lines = build_blocked_section(tasks)
    if blocked_lines:
        out.append("## Blocked")
        out.extend(blocked_lines)
        out.append("")

    out.append("## Board")
    out.extend(build_board_section(tasks, scope))
    out.append("")

    backlog_lines = build_backlog_section(tasks, now)
    if backlog_lines:
        out.append("## Backlog needing info")
        out.extend(backlog_lines)
        out.append("")

    stale_lines = build_stale_claims_section(tasks, now, claim_staleness_hours)
    if stale_lines:
        out.append("## Stale claims")
        out.extend(stale_lines)
        out.append("")

    if skipped:
        noun = "file" if len(skipped) == 1 else "files"
        out.append(
            f"({len(skipped)} malformed task {noun} skipped: "
            f"{', '.join(skipped)})"
        )

    return prefix + "\n".join(out).rstrip("\n")


# ---------------------------------------------------------------------------
# Version-skew nudge (fg-a10907, absorbed into the script per fg-a10214) --
# resolves the installed plugin key PREFIX-TOLERANTLY (any `forge@*`,
# preferring `forge@orns-forge`), exactly mirroring the resolution order in
# tools/banner_install.py's _installed_plugin_root -- replacing the dead
# hardcoded `forge@forge-local` key the LLM-authored nudge used to compare
# against. Fail-silent throughout: any error, absence, equal versions, or a
# dev-path plugin root with no version segment all resolve to no nudge.
# ---------------------------------------------------------------------------

def _resolve_forge_plugin_entries(plugins):
    if isinstance(plugins.get("forge@orns-forge"), list) and plugins["forge@orns-forge"]:
        return plugins["forge@orns-forge"]
    candidates = sorted(
        (k, v) for k, v in plugins.items()
        if isinstance(k, str) and k.startswith("forge@") and v
    )
    return candidates[0][1] if candidates else None


def _parse_dotted_version(value):
    """Parse a dotted numeric version ('0.12.0') into a tuple of ints, or
    None if it doesn't look like one -- e.g. a dev-checkout directory name
    ('forge') carries no version segment and must resolve to None so the
    nudge stays silent rather than comparing against garbage."""
    if not isinstance(value, str) or not value.strip():
        return None
    parts = value.strip().split(".")
    if not parts or not all(re.match(r"^\d+$", p) for p in parts):
        return None
    return tuple(int(p) for p in parts)


def resolve_installed_version(installed_plugins_path):
    """The installed forge plugin's version, from
    ~/.claude/plugins/installed_plugins.json, or None on any failure."""
    try:
        text = pathlib.Path(installed_plugins_path).read_text(encoding="utf-8-sig")
        data = json.loads(text)
        plugins = data.get("plugins", {}) if isinstance(data, dict) else {}
        entries = _resolve_forge_plugin_entries(plugins)
        if not entries:
            return None
        version = entries[0].get("version") if isinstance(entries[0], dict) else None
        return _parse_dotted_version(version)
    except Exception:
        return None


def resolve_loaded_version(plugin_root):
    """The version segment of a `${CLAUDE_PLUGIN_ROOT}`-style path, or None
    for a dev-checkout root with no version segment (e.g. D:\\forge)."""
    if not plugin_root:
        return None
    try:
        segment = pathlib.PurePath(str(plugin_root)).name
    except Exception:
        return None
    return _parse_dotted_version(segment)


def version_skew_nudge(plugin_root, installed_plugins_path):
    """One-line nudge string if the installed plugin is newer than the
    loaded one, else None. Never raises."""
    try:
        installed = resolve_installed_version(installed_plugins_path)
        loaded = resolve_loaded_version(plugin_root)
        if installed is None or loaded is None:
            return None
        if installed > loaded:
            installed_str = ".".join(str(p) for p in installed)
            loaded_str = ".".join(str(p) for p in loaded)
            return (
                f"forge v{installed_str} installed, this session runs "
                f"v{loaded_str} — restart at the next milestone boundary "
                "to pick up fixes"
            )
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _normalize_scope(raw):
    """Returns (scope, error). scope is None (default), "all", or a state
    name. error is a message string if raw was unrecognized."""
    if raw is None:
        return None, None
    if raw == "all":
        return "all", None
    if raw in validate_task.STATES:
        return raw, None
    return None, f"unrecognized scope: {raw!r} (want: all, or one of {sorted(validate_task.STATES)})"


def _default_installed_plugins_path():
    return str(pathlib.Path.home() / ".claude" / "plugins" / "installed_plugins.json")


def main(argv=None):
    # See validate_task.py's main() for why: em dashes in this module's own
    # output would otherwise crash under a legacy Windows OEM codepage.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="status.py",
        description="Render the canonical Forge queue status board.",
    )
    parser.add_argument("scope", nargs="?", default=None,
                         help="all, or a specific state (default: capped, non-done)")
    parser.add_argument("--root", default=".",
                         help="project root containing .forge/ (default: cwd)")
    parser.add_argument("--plugin-root", default=None,
                         help="${CLAUDE_PLUGIN_ROOT} -- used for the version-skew nudge")
    parser.add_argument("--installed-plugins-path", default=None,
                         help="override for testing; default is "
                              "~/.claude/plugins/installed_plugins.json")
    parser.add_argument("--project-dir", default=None,
                         help="override for testing; default is "
                              "CLAUDE_PROJECT_DIR env var, else cwd "
                              "(scope-guard advisory)")
    args = parser.parse_args(argv)

    scope, err = _normalize_scope(args.scope)
    if err:
        print(err, file=sys.stderr)
        return 1

    root = pathlib.Path(args.root)
    task_dir = root / ".forge" / "queue" / "tasks"
    forge_md = root / ".forge" / "forge.md"

    installed_plugins_path = (
        args.installed_plugins_path or _default_installed_plugins_path()
    )
    nudge = version_skew_nudge(args.plugin_root, installed_plugins_path)

    board_text = render_board(
        task_dir, forge_md, scope=scope, project_dir=args.project_dir
    )

    lines = []
    if nudge:
        lines.append(nudge)
        lines.append("")
    lines.append(board_text)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
