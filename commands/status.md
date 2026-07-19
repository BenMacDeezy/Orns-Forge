---
description: Render the Forge queue board
argument-hint: "[all | <state>]"
---

**Script-only fast path (fg-a10214):** the board is a pure data query, not
an LLM generation task — rendering it via skill-load + per-task-file reads
+ generated table took 90+ seconds in practice. Run
`python "${CLAUDE_PLUGIN_ROOT}/tools/status.py" <scope-args> --plugin-root "${CLAUDE_PLUGIN_ROOT}"`
via Bash and print its stdout VERBATIM — no reformatting, no commentary, no
skill load, no per-task file reads, no LLM table generation. This command's
own job is only argument parsing (translating `$ARGUMENTS` into the
script's scope argument, below), passing `--plugin-root`, and reply
framing around the script's output.

The LLM rendering path through the `forge:queue` skill's **Status board**
section (`skills/queue/references/status-board.md`) is now only an
EXPLICIT FALLBACK, used solely when the script exits nonzero — that
reference names `tools/status.py` as the canonical renderer, so the two
definitions can never diverge. If the script errors, fall back to invoking
the skill's Status board section exactly as before, and note in the reply
that the fast path failed.

Parse `$ARGUMENTS` into the scope argument the script expects:

- No argument: default scope (non-done, capped at 15 rows) — pass no scope
  argument.
- `all`: non-done, uncapped — pass `all`.
- `<state>` (backlog/ready/active/blocked/done/dropped): filtered to that
  state only, uncapped — the only way to see done/dropped rows — pass
  `<state>`.
- Anything else unrecognized: say so and fall back to the default scope
  (pass no scope argument to the script).
- `--graph` (combinable with any scope above): render the queue as a mermaid
  dependency DAG via `tools/queue_graph.py` instead of the table — bypasses
  `tools/status.py` entirely — the board may also offer this once,
  unprompted, when a scope contains 3+ interdependent tasks.

Print exactly what the script outputs for that scope — no commentary
beyond the board itself — and, if the printed board includes any `ready`
task in this scope, close with one line recommending `/forge:start` as the
next step; otherwise nothing else.

**Version-skew nudge (fg-a10907, once per session, never blocking):** the
script computes this itself now — it resolves the installed plugin key
PREFIX-TOLERANTLY (any `forge@*` key in
`~/.claude/plugins/installed_plugins.json`, preferring `forge@orns-forge`,
matching `tools/banner_install.py`'s resolution order — not the dead
`forge@forge-local` key the LLM-authored version of this nudge used to
hardcode) and compares it against the version segment of the
`--plugin-root` path passed above. If the installed version is newer than
the loaded one, the script's stdout already starts with ONE line — "forge
v<installed> installed, this session runs v<loaded> — restart at the next
milestone boundary to pick up fixes" — printed verbatim as part of the
output above; nothing else to do here. Versions equal, the file
unreadable, a dev-checkout `--plugin-root` with no version segment (e.g.
`D:\forge`), or any error: stay silent (fail-silent, zero protocol weight)
— the script prints no such line. Never repeat the line later in the same
session, and never surface it mid-wave.

If `.forge/` exists but `.forge/README.md` doesn't, offer once (before the
board or in the same reply) to add it from `forge:queue`'s
`references/forge-dir-readme-template.md` — never repeat this offer twice
in the same session once it's been made or accepted.
