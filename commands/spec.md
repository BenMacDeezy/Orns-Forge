---
description: Brainstorm an idea into an approvable spec, then decompose it into linked tasks
argument-hint: "<feature idea>"
---

Invoke the `forge:spec` skill and run the spec pipeline for: $ARGUMENTS

- Brainstorm → draft (forge-spec-writer) → resolve every `[NEEDS CLARIFICATION]`
  → HUMAN approval gate → save to `.forge/specs/` → decompose into linked
  `tier: full` tasks.
- Never approve on the user's behalf, and never queue tasks while a
  clarification marker remains or the spec is not `approved`.
- If the argument names an existing spec, surface that spec's UNRATIFIED
  changelog deltas for ratification instead of starting a new draft.
- Reply with: spec id/path, status, open clarifications (if any), and — once
  approved and decomposed — the created task ids.
- Once decomposition has queued tasks, close with one line recommending
  `/forge:start` as the next step (or `/forge:verify` for a check-only look
  first); otherwise nothing else.
