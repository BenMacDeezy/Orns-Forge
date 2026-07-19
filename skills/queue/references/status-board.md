# Status board (reference)

Loaded by `skills/queue/SKILL.md` only when rendering "what's in the
queue" — `/forge:status` and a bare NL "what's queued" ask both reach this
exact definition; the two paths must never diverge in ordering, caps, or
content. NORMATIVE — moved verbatim from the queue skill, not summarized.
A kernel-loop session that never renders the board does not need this file.

## Status board

The canonical rendering for "what's in the queue." `/forge:status` and a bare
NL ask ("what's queued", "what's in the queue right now" — the frontmatter
trigger above) both reach this exact definition; the two paths must never
diverge in ordering, caps, or content.

Read every file in `.forge/queue/tasks/` frontmatter-first — do not read task
bodies except: blocked tasks' Outcome (one-line blocker), and backlog tasks'
Outcome/Attempt-log first line (needs-info note only, step 3).

Render, in this order:

1. **Blocked first**: each blocked task — id, title, one-line blocker from
   its Outcome. Also include any `ready` task whose `blocked-by` references a
   `dropped` or missing task id — flag it as blocked-for-display with that id
   as the reason, even if Waves hasn't yet formally transitioned it to
   `state: blocked`. An unsatisfiable dependency is never rendered as if the
   task were simply still `ready`.
2. **Board**: counts per state, then a table: id, title, state, tier,
   priority, blocked-by, claimed-by — ordered priority ascending, then
   created ascending (oldest first), same as wave order.
   - **Default scope**: non-done tasks only, capped at top 15 rows. If more
     non-done tasks exist beyond the cap, add one line after the table: "N
     more not shown — run `/forge:status all` to see everything (or
     `/forge:status <state>` to filter)."
   - **Widened scope** (a caller may ask for this explicitly — `all`, or a
     specific `<state>`): `all` shows every non-done task, uncapped, no "N
     more" line. A specific state shows only tasks in that state (including
     `done`/`dropped` — this is the only way to see them), uncapped, no "N
     more" line.
   - Queues at or under the cap render exactly as the default, uncapped and
     with no omission line — this view is unchanged for small queues.
3. **Backlog needing info**: list backlog tasks that qualify for either
   reason below (once each; show both markers if a task qualifies for both):
   - *Needs-info note*: it carries a needs-info/blocker note. Read only the
     first non-empty line of its Outcome section; if Outcome is empty or
     still `(pending)`, read the first non-empty line of Attempt log
     instead. Show that line verbatim as the note. A task whose
     Outcome/Attempt-log has no non-placeholder content doesn't qualify on
     this basis.
   - *Stale*: its `updated` date is older than the backlog-staleness
     threshold. forge.md's `claim-staleness-hours` governs active-claim
     recovery (default 0.5h), not backlog age, so use a default of 14 days
     for backlog staleness instead. Mark qualifying tasks `[stale-backlog]`.
   - Omit this section entirely if no backlog task qualifies.
4. **Stale claims**: any active claim older than forge.md's
   claim-staleness-hours, flagged.
5. If `.forge/` or the queue is missing/empty, say so in one line.

This section owns the rendering; a caller (a command or an NL ask) owns only
scope selection (default / `all` / `<state>`) and its own reply framing
around the board.
