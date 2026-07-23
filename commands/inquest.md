---
description: Run an adversarial deep-debug tribunal (finder → refuter → judge) to hunt bugs already in the tree
argument-hint: "<scope> [--budget <n>]"
---

Invoke the `forge:inquest` skill and run one tribunal pass over: $ARGUMENTS

- **Gate first.** This command itself is the human-ask trigger the skill's
  gating rule requires (or, if reached via an accepted recommendation card,
  the card's acceptance is) — never run this from a loop or standing
  schedule. State the charter (scope, budget, stop conditions) before the
  first FINDER spawn.
- **Ask the model first.** Before the first FINDER spawn, ask the human
  which model to run the tribunal on (any read-capable model — a Claude tier
  works immediately; a provider model like `codex/gpt-5.6-sol` routes through
  the gated read-only provider path), per the skill's "Model selection —
  ask first" rule; apply the choice to all three roles.
- Run the tribunal: FINDER lens(es) → REFUTER per finding → JUDGE synthesis,
  per the skill's routing tiers and boundary rules.
- CONFIRMED findings become ready queue-task drafts via `forge:queue`
  (repro + expected/actual, constitution rule 1 applies); DISMISSED findings
  are recorded with the refuter's reason; UNRESOLVED findings are surfaced
  directly in the reply — nothing silently dropped.
- Reply with: the charter, a per-finding table (claim, verdict, routing),
  and any task ids created.
- If any CONFIRMED finding produced a `state: ready` task, close with one
  line recommending `/forge:start` as the next step; otherwise nothing else.
