"""Render the Forge queue as a mermaid flowchart DAG: one node per non-done
task (id + short title), blocked-by edges (blocker --> blocked), node classes
by state (ready/active/blocked/backlog; dropped gets its own class too since
it is also non-done). Done tasks are omitted unless --all. Read-only: never
writes to any .forge/ path. Zero dependencies.

Backs /forge:status --graph and the queue skill's Status board offer for
multi-task waves (fg-a10202).
"""
import pathlib
import re
import sys

# Reuse validate_task's frontmatter/section helpers rather than re-implement
# them -- same fence-aware, line-anchored parsing every other tool in this
# repo relies on (same pattern as tools/telemetry.py).
_THIS_DIR = str(pathlib.Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import validate_task

TASK_DIR_DEFAULT = ".forge/queue/tasks"

MAX_TITLE_LEN = 40

NO_DIAGRAM_MESSAGE = "Queue is empty or all tasks are done -- nothing to graph."

# Stroke-based differentiation (fill:none) so nodes stay readable on both
# light and dark mermaid themes -- a fill color would wash out or clash
# depending on theme, a stroke color reads on either.
STATE_CLASSDEFS = {
    "ready": "fill:none,stroke:#2ecc71,stroke-width:3px,color:#2ecc71",
    "active": "fill:none,stroke:#3498db,stroke-width:3px,color:#3498db",
    "blocked": "fill:none,stroke:#e74c3c,stroke-width:3px,color:#e74c3c",
    "backlog": "fill:none,stroke:#95a5a6,stroke-width:2px,"
               "stroke-dasharray: 4 2,color:#95a5a6",
    "dropped": "fill:none,stroke:#7f8c8d,stroke-width:1px,"
               "stroke-dasharray: 2 2,color:#7f8c8d",
}

# Order classDef lines are emitted in -- deterministic, independent of dict
# insertion order.
_CLASSDEF_ORDER = ["ready", "active", "blocked", "backlog", "dropped"]


def _escape_title(title):
    """Make a task title safe to embed inside a mermaid `id["..."]` node
    label: no raw double-quotes (would terminate the quoted label early) and
    no raw square brackets (would break the node's own [...] delimiters)."""
    safe = title.replace('"', "'").replace("[", "(").replace("]", ")")
    safe = safe.replace("\n", " ").replace("\r", " ")
    if len(safe) > MAX_TITLE_LEN:
        safe = safe[: MAX_TITLE_LEN - 3].rstrip() + "..."
    return safe


def build_graph(task_dir, include_done=False):
    """Read every *.md task file in `task_dir`, return a plain-dict graph
    description. Read-only: never writes or transitions a task. Missing/
    empty directories yield a clean, empty graph rather than raising.
    Malformed task files are skipped, counted, never crash the build.
    """
    task_dir = pathlib.Path(task_dir)
    graph = {
        "nodes": [],  # [{"id", "title", "state"}, ...] sorted by id
        "edges": [],  # [(blocker_id, blocked_id), ...] sorted
        "skipped": 0,
    }

    try:
        paths = sorted(
            p for p in task_dir.glob("*.md") if p.is_file() and p.stat().st_size > 0
        )
    except OSError:
        paths = []

    tasks = {}  # id -> {"title", "state", "blocked_by": [...]}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            graph["skipped"] += 1
            continue

        fm, fm_errors, body = validate_task._parse_frontmatter(text)
        if fm is None or body is None:
            graph["skipped"] += 1
            continue

        # A malformed blocks/blocked-by inline list (e.g. an unclosed
        # bracket) still parses to a usable fm/body, but _parse_frontmatter
        # flags it in fm_errors. Discarding those errors let the field
        # silently degrade to an opaque string -> wrapped as a single-item
        # "dependency" that never matches a real id -> dropped edge, with
        # skipped staying 0 the whole time. The malformation must surface as
        # a skip instead of vanishing without a trace (fg-a10504).
        if any("inline list" in err for err in fm_errors):
            graph["skipped"] += 1
            continue

        task_id = fm.get("id")
        state = fm.get("state")
        if not task_id or state not in validate_task.STATES:
            graph["skipped"] += 1
            continue

        title = fm.get("title") or task_id
        blocked_by = fm.get("blocked-by")
        if not isinstance(blocked_by, list):
            blocked_by = [] if blocked_by in (None, "", "[]") else [blocked_by]

        tasks[task_id] = {
            "title": title,
            "state": state,
            "blocked_by": [b for b in blocked_by if b],
        }

    rendered_ids = {
        task_id
        for task_id, t in tasks.items()
        if include_done or t["state"] != "done"
    }

    for task_id in sorted(rendered_ids):
        t = tasks[task_id]
        graph["nodes"].append(
            {"id": task_id, "title": t["title"], "state": t["state"]}
        )

    edges = set()
    for task_id in rendered_ids:
        for blocker_id in tasks[task_id]["blocked_by"]:
            if blocker_id in rendered_ids:
                edges.add((blocker_id, task_id))
    graph["edges"] = sorted(edges)

    return graph


def render_mermaid(graph):
    """Render a graph dict (from build_graph) as a fenced mermaid flowchart
    block, or the no-diagram message if there is nothing to draw."""
    if not graph["nodes"]:
        return NO_DIAGRAM_MESSAGE

    lines = ["```mermaid", "flowchart TD"]

    for node in graph["nodes"]:
        label = f"{node['id']}<br/>{_escape_title(node['title'])}"
        lines.append(f'    {node["id"]}["{label}"]')

    for blocker_id, blocked_id in graph["edges"]:
        lines.append(f"    {blocker_id} --> {blocked_id}")

    states_present = sorted({node["state"] for node in graph["nodes"]})
    for state in _CLASSDEF_ORDER:
        if state in states_present:
            lines.append(f"    classDef {state} {STATE_CLASSDEFS[state]}")

    for node in graph["nodes"]:
        if node["state"] in STATE_CLASSDEFS:
            lines.append(f'    class {node["id"]} {node["state"]}')

    lines.append("```")

    if graph["skipped"]:
        noun = "file" if graph["skipped"] == 1 else "files"
        lines.append("")
        lines.append(
            f"({graph['skipped']} malformed task {noun} skipped -- not rendered.)"
        )

    return "\n".join(lines)


def main(argv):
    task_dir = TASK_DIR_DEFAULT
    if "--dir" in argv:
        i = argv.index("--dir")
        if i + 1 < len(argv):
            task_dir = argv[i + 1]

    include_done = "--all" in argv

    graph = build_graph(task_dir, include_done=include_done)
    print(render_mermaid(graph))
    return 0  # read-only reporter: always exits 0 on a valid run


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
