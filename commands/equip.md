---
description: Audit this project's capability surface (skills/agents/MCPs/CLIs) against its charter and propose find/create/wire actions
argument-hint: "[focus, e.g. \"frontend\" or \"testing\"]"
---

Invoke the `forge:equip` skill and run one capability-gap audit. Optional
focus: $ARGUMENTS

- Run the trust preamble; if `.forge/project.md` is missing or still
  `draft`, offer discovery/onboard first rather than inventing goals.
- Inventory the current capability surface (skills, agent roster +
  attachments, connected MCP servers checked via tool-listing evidence, a
  short stack-relevant CLI probe, hooks/validators) as a compact table.
- Diff against the charter, the map, and backlog themes; classify every
  finding MISSING / WEAK / MISWIRED.
- Present a ranked proposal via structured option cards — FIND / CREATE /
  WIRE / SKIP per gap. Install, create, queue, or enable NOTHING without
  explicit approval on the cards.
- Reply with the capability table, the gap diff, and the proposal cards —
  nothing else.

Once any CREATE items are approved and queued, recommend `/forge:start` as
the next step to work them.
