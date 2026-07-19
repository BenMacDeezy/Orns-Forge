---
description: Render the Forge queue board
argument-hint: "[all | <state>]"
---

Invoke the `forge:queue` skill's **Status board** section to render the
board — that section is the canonical rendering (it's the same board an NL
"what's in the queue" ask reaches; the two must never diverge). This
command's own job is only argument parsing and reply framing.

Parse `$ARGUMENTS` into the scope the Status board section expects:

- No argument: default scope (non-done, capped at 15 rows).
- `all`: non-done, uncapped.
- `<state>` (backlog/ready/active/blocked/done/dropped): filtered to that
  state only, uncapped — the only way to see done/dropped rows. If nothing
  matches, say so in one line instead of an empty table.
- Anything else unrecognized: say so and fall back to the default scope.
- `--graph` (combinable with any scope above): render the queue as a mermaid
  dependency DAG via `tools/queue_graph.py` instead of the table — the board
  may also offer this once, unprompted, when a scope contains 3+
  interdependent tasks.

Render exactly what the skill section defines for that scope — no commentary
beyond the board itself — and, if the board includes any `ready` task in
this scope, close with one line recommending `/forge:start` as the next
step; otherwise nothing else.

**Version-skew nudge (fg-a10907, once per session, never blocking):** before
rendering, compare the version segment of `${CLAUDE_PLUGIN_ROOT}`'s path
against the `forge@forge-local` version registered in
`~/.claude/plugins/installed_plugins.json`. If the installed version is
newer than the loaded one, prepend ONE line — "forge v<installed> installed,
this session runs v<loaded> — restart at the next milestone boundary to pick
up fixes" — then continue normally. Versions equal, file unreadable, or any
error: stay silent (fail-silent, zero protocol weight). Never repeat the
line later in the same session, and never surface it mid-wave.

If `.forge/` exists but `.forge/README.md` doesn't, offer once (before the
board or in the same reply) to add it from `forge:queue`'s
`references/forge-dir-readme-template.md` — never repeat this offer twice
in the same session once it's been made or accepted.
