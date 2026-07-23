# Task CRUD — Create / Edit / Cancel (reference)

Loaded by `skills/queue/SKILL.md` only on the command that needs it:
`/forge:add` reads "Create a task", `/forge:edit` reads "Edit a task",
`/forge:cancel` reads "Cancel a task" (also read by the kernel's LEARN step
when it creates a capability-gap backlog task — the only case a pure loop
session touches this file). NORMATIVE — moved verbatim from the queue
skill, not summarized.

## Create a task

0. **Duplicate check (advisory).** Before creating, scan the titles of existing non-`done` tasks (`backlog`/`ready`/`active`/`blocked` — a `dropped` title is fair game again) for a close match to the new title: case-insensitive token overlap (most significant words in common) or a substring match either direction. On a strong match, surface the existing task's id + title and offer three options — proceed anyway (create it), link the new task as `blocked-by` the existing one, or cancel (don't create). This check never silently blocks creation: if there's no match, or the human picks "proceed anyway", continue to step 1 normally.
1. Generate id: a human-readable kebab-case name describing the work (e.g. `database-migration`, `color-refactor`; 3-40 chars, `[a-z0-9][a-z0-9-]*[a-z0-9]`, no `--`) per spec-f0c2 Amendments item 2 (2026-07-20 ratification). Check it unique against every id in `.forge/queue/tasks/`; on a collision, pick a different descriptive name (or append `-2`, `-3`, ... if reusing the same name deliberately) rather than falling back to a hex id. Legacy `fg-`/`spec-` hex ids already in the queue are never renamed to this scheme.
2. Copy the template. Fill frontmatter; filename `<id>-<kebab-slug-max-40-chars>.md`.
3. Draft EARS acceptance criteria from the request — every clause `WHEN [trigger], THE SYSTEM SHALL [behavior]`, each independently checkable. If you cannot write at least one testable clause, the task stays `state: backlog` with a note in Outcome about what's unclear.
4. Assign tier: `trivial` = single-file, no behavior-contract change, reversible in one commit (typos, comments, config tweaks, doc edits). `full` = requires/links a spec (new subsystem, security-sensitive area, breaking change). Everything else `standard`.
5. Assign priority (default 2; bugs affecting users get 1) and `parallel-safe` (false if it touches shared config, lockfiles, schema/migrations, or the same files as another open task).
6. Set `state: ready` if criteria are complete and dependencies known; else `backlog`.

**UI+motion split.** When the work described spans BOTH structural UI and
non-trivial motion, do not create one mixed task — split it into two linked
tasks instead: a `ui`-shaped task and a `blocked-by` animator task (motion
`blocked-by` structure), each with its own EARS criteria drafted per step 3
above, scoped to its own surface. Trivial micro-transitions (hover/focus
states) stay on the `ui` task. See `docs/conventions.md`, "UI+motion task
splitting" for the canonical rule and the trivial-motion carve-out.

## Edit a task

Editable fields on a **non-terminal** task (`state` not `done`/`dropped`): `title`, `priority`, `tier`, Acceptance criteria, `blocked-by`. Not editable via this operation: `id`, `state`, `claimed-by`, `created` (state changes go through the transitions below; `claimed-by` through Claim/release).

1. Refuse and explain if `state` is `done` or `dropped` — those are terminal; the caller wants a new task, not an edit to a closed one.
2. Refuse and explain if `state` is `active` (claimed, in-flight) AND the requested edit would change `tier`, Acceptance criteria, or `blocked-by`. These are plan-dependent fields — a dispatched worker is currently planning and building against their current values. Editing them mid-flight breaks the worker's contract. Instead, suggest `/forge:cancel` to release the task (so it returns to `ready` for another attempt), or wait for the current attempt to finish. Metadata-only edits (`title`, `priority`) on active tasks are permitted.
3. Apply the requested field changes in one edit.
4. Touch `updated` (real `date -u` timestamp).
5. Append one line to Attempt log: what changed (field: before → after) and why.

## Cancel a task (= dropped)

Cancelling a task is the `any → dropped` human-decision transition (`forge:queue`, Legal state transitions) — there is no separate "cancelled" state. In addition to the normal transition bookkeeping (`state`, `updated`, `claimed-by: null`, Attempt log line):

- Write the reason to Outcome.
- If the task was `active` when cancelled, note explicitly in Outcome that any in-flight work for it is abandoned — a worker or verifier that was mid-flight on this task should stop; its output, if any, is not integrated.
