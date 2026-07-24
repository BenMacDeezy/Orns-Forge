---
description: Cancel a Forge queue task (transition to dropped)
argument-hint: "<id> [reason]"
---

Invoke the `forge:queue` skill to cancel task: $ARGUMENTS

- Auto-init `.forge/` if missing (repo-root resolved).
- Transition the task `state: dropped` (the legal `any → dropped` human
  decision). Set `claimed-by: null`, touch `updated`, and append one line to
  Attempt log recording the cancellation.
- Write the reason (from $ARGUMENTS, or "no reason given") to Outcome. If the
  task was `active`, note explicitly in Outcome that any in-flight work for
  it is abandoned.
- `done` and `dropped` are already terminal — if the task is already in
  either state, report that and make no change.
- Reply with: task id, prior state, and the recorded reason — nothing else.
