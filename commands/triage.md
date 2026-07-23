---
description: Triage a bug report into a ready queue task (Forge intake door 3)
argument-hint: "<bug report>"
---

Invoke the `forge:queue` skill, then spawn `forge-triage` (sonnet/medium) to
triage: $ARGUMENTS

- Auto-init `.forge/` if missing.
- forge-triage reproduces, classifies, and returns a task draft with repro +
  expected/actual. Bugs are pre-authorized — skip spec approval.
- If the classification is `bug`, create the task from the draft via the queue
  skill (`state: ready` if reproduced, else `backlog` with what's missing).
- If `needs-design-change`, do NOT create a task — tell the user to run
  `/forge:spec`. If `not-a-bug`, report why and create nothing.
- Reply with: classification, task id (if created), state, tier, and criteria.
- If a task landed `state: ready`, close with one line recommending
  `/forge:start` as the next step (or `/forge:verify` for a check-only look
  first); otherwise nothing else.
