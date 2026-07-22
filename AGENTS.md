# AGENTS.md

This repository uses **Forge** for autonomous development. This file re-exports
the project conventions so any agent tool inherits them (spec §7.5).

## Build / test / lint

- build: none (Claude plugin repo — no build step)
- test: `python -m pytest tools/ -q`
- lint: none (no linter configured)

## Conventions

See `.forge/map/conventions.md` for the full build/test/run commands,
patterns, naming, and gotchas. Highlights:

- **Markdown is the system; scripts are accelerators** (spec §2.1). Every hook
  and every Python tool duplicates a check the kernel/skills already perform
  in prose — no state may exist *only* in a script.
- **Explicit routing always.** Every agent spawn declares both `model` and
  `effort`; nothing inherits the session model implicitly.
- Judge/verify agents (`forge-verifier`, `forge-reviewer`, `forge-security`,
  `forge-ui-verifier`) carry a read-only `tools:` allowlist — they judge,
  never edit.
- Agents attach skills, don't inline them — each `agents/*.md` has an
  **Attached skills** section rather than duplicated skill prose.

## Environment invariants

- ports: no dev server owned by this repo (pure markdown + Python CLI tools;
  no long-running process to manage).
- processes: none started by this repo's own tooling.
- fixtures: hook/validator tests build scratch git repos under
  `tempfile.TemporaryDirectory()` — never touch this repo's own `.forge/` or
  working tree.
- os-traps: this repo is developed on Windows via Git Bash. Watch for UTF-8
  BOM on files written by PowerShell (`Out-File`/`Set-Content` default to
  UTF-16 or BOM'd UTF-8 — read with `utf-8-sig`), and mixed path separators.

## Forge state (source of truth)

- `.forge/forge.md` — routing overrides, budgets, gate commands.
- `.forge/constitution.md` — numbered non-negotiables (mechanically checked).
- `.forge/queue/tasks/` — the work queue (state in frontmatter).
- `.forge/map/` — the repo map.
- `.forge/memory/` — project memory.
- `.forge/agents/` — project-local custom agents (none yet).

Run `/forge:status` for the queue board, `/forge:start` to work the queue.
