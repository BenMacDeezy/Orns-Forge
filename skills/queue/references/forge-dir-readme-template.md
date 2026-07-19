# .forge/ — Forge's project state

This folder holds Forge's state for *this project*: queue, map, memory,
specs, and settings. Plain markdown, safe to read, safe to poke around in —
the Forge kernel owns it, but nothing here is a mystery format.

- `queue/tasks/` — work items, one markdown file per task (state lives in frontmatter).
- `map/` — the repo map: `architecture.md` plus deep-dive `subsystems/*.md`.
- `memory/` — durable project facts and decisions, indexed by `MEMORY.md`.
- `specs/` — approved feature specs: goal, EARS criteria, task decomposition.
- `forge.md` — this project's settings: Features toggles and Gate commands.
- `constitution.md` — this project's non-negotiable rules and conventions.
- `project.md` — the project charter: vision, users, stack, roadmap.
- `.provenance` / `.trust-local` — machine-local trust markers proving this
  `.forge/` was created or confirmed on this machine; both are git-ignored,
  never committed.

**Not here:** agents, skills, commands, and hooks are NOT in this folder —
they live in the Forge plugin and are shared by all your projects, not
copied per-repo. The one exception is `.forge/agents/`, which appears only
once you create a project-local agent via `/forge:agent`.

Manage this from chat, not by hand: `/forge:status` renders the queue board,
`/forge:settings` edits `forge.md`. Full docs live in the Forge plugin repo.
