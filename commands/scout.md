---
description: Run a Forge tooling-discovery pass now (skills, MCP servers, CLIs, repos)
argument-hint: "[focus, e.g. \"testing\" or \"docs\"]"
---

Invoke the `forge:scout` skill and run one discovery pass. Optional focus: $ARGUMENTS

- Auto-init `.forge/` if missing (so any gap tasks can be filed).
- Profile the stack, search sources in priority order, vet each candidate, and
  return the ranked shortlist per the skill's template.
- Install NOTHING and edit no config — present exact install commands for the
  human to run. File any capability gaps as `backlog` tooling tasks.
- If the search is large, delegate to `forge-scout` (sonnet/medium) rather than
  polluting this context.
