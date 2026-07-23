# AGENTS.md

This repository uses **Forge** for autonomous development. This file re-exports
the project conventions so any agent tool inherits them (spec §7.5).

## Build / test / lint

<!-- filled by onboard from .forge/forge.md Gates, resolved from the repo -->
- build: <command>
- test: <command>
- lint: <command>

## Conventions

<!-- If .forge/map/conventions.md exists (repo map built), its contents are
     embedded or linked here. Otherwise this points at .forge/forge.md. -->
See `.forge/map/conventions.md` (if present) for build/test/run commands,
patterns, naming, and gotchas.

## Environment invariants

<!-- filled by onboard from what it learns about THIS machine/repo; dispatch
     contracts CITE this section instead of restating it per contract
     (docs/conventions.md, "Verification infrastructure — 2026-07-18").
     Examples of what belongs here: port etiquette (which ports are owned by
     other services; kill only your own PID, never by image name), dev-server
     start/stop commands and who tears them down, fixture/throwaway-route
     hygiene, OS-specific traps (CRLF, path separators, encoding). -->
- ports: <owned ports and etiquette>
- processes: <kill-own-PID-only rules>
- fixtures: <throwaway-route/fixture hygiene>
- os-traps: <platform-specific gotchas>

## Forge state (source of truth)

- `.forge/forge.md` — routing overrides, budgets, gate commands.
- `.forge/constitution.md` — numbered non-negotiables (mechanically checked).
- `.forge/queue/tasks/` — the work queue (state in frontmatter).
- `.forge/map/` — the repo map (if built).
- `.forge/memory/` — project memory (if present).
- `.forge/agents/` — project-local custom agents.

Run `/forge:status` for the queue board, `/forge:start` to work the queue.
