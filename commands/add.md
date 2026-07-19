---
description: Create a Forge queue task from a description
argument-hint: "<task description>"
---

Invoke the `forge:queue` skill, then create ONE task from: $ARGUMENTS

- Auto-init `.forge/` if missing.
- Duplicate check (queue skill, "Create a task", step 0): scan existing
  non-done task titles for a close match. On a strong match, surface the
  existing id + title and ask whether to proceed anyway, link the new task as
  `blocked-by` it, or cancel. Advisory only — never silently skip creation
  when there's no match.
- Draft EARS acceptance criteria; set tier/priority/parallel-safe per the
  skill's rules. If criteria can't be made testable from the description,
  create it as `backlog` and say what's missing.
- Reply with: task id, filename, state, tier, and the drafted criteria —
  nothing else.
