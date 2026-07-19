---
description: Set up Forge end to end in this repository (init .forge/, map, constitution, forge.md, scout pass, AGENTS.md)
---

Invoke the `forge:onboard` skill and run the full setup for the current repo.

- Init `.forge/` and resolve the forge.md gate commands from the repo.
- Build the map by running the `forge:map` skill.
- Seed `.forge/constitution.md` (starter) if absent.
- Run a `forge:scout` pass and present the vetted shortlist — install NOTHING.
- Generate a root `AGENTS.md` re-exporting the project conventions.
- Never overwrite existing files; report created-vs-present, then the next command.
