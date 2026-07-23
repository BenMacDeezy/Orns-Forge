---
description: Edit a non-terminal Forge queue task's fields
argument-hint: "<id> [changes]"
---

Invoke the `forge:queue` skill to edit task: $ARGUMENTS

- Auto-init `.forge/` if missing (repo-root resolved).
- Refuse if the task's `state` is `done` or `dropped` — those are terminal;
  explain why and suggest `/forge:add` for follow-on work instead.
- Refuse if the task's `state` is `active` (claimed, in-flight) AND the
  requested edit affects plan-dependent fields (`tier`, Acceptance criteria,
  `blocked-by`). Explain that editing plan assumptions mid-flight would break
  the worker's contract. Suggest `/forge:cancel` to unclaim it first (or
  wait for it to complete). Metadata-only edits (`title`, `priority`) on
  active tasks are allowed.
- Otherwise apply the requested changes to the task's editable fields (queue
  skill, "Edit a task"): `title`, `priority`, `tier`, Acceptance criteria,
  `blocked-by`. Touch `updated` and append one line to Attempt log describing
  what changed and why.
- If the requested change is ambiguous or targets a non-editable field
  (`id`, `state`, `claimed-by`, `created`), say so and make no edit.
- Reply with: task id, fields changed (before → after), and new `updated`
  timestamp — nothing else.
