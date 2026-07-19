---
name: agent-factory
description: Generate a custom Forge agent on demand when a recurring task type fits no standing-roster agent. Writes a vetted agent into .forge/agents/ (project) or the plugin agents/ (global), gated by the factory checklist. Defers to skill-creator when the right artifact is a skill, not an agent.
---

# Forge agent factory

When the loop meets a recurring task type no roster agent fits, mint a new agent —
deliberately, gated, and logged. The roster must never regrow into a graveyard
(spec §6.4).

## First decision: agent or skill?

- A reusable *procedure or body of knowledge* → it's a **skill**: defer to
  `skill-creator`. Do not build an agent for it.
- A *role that gets spawned with its own context, model, and output contract* →
  it's an **agent**: continue here.

## Scope: project-local vs. global

- **Project-local (default):** write `.forge/agents/<name>.md`, git-tracked with
  the repo (format: `docs/conventions.md` → ".forge/agents/"). Then mirror the
  file to `.claude/agents/<name>.md` so the running harness discovers it; the
  `.forge/` copy is canonical.
- **Global (only when useful across projects):** write to the plugin's `agents/`.

## Build the agent (anatomy — spec §6.1)

Start from `references/agent-template.md` and fill every section: mission (single
purpose), attached skills, default routing (model + effort + one-line
justification), optional tool allowlist, output contract (exact structured
shape), forbidden actions (always incl. "never touch `.forge/`"), and provenance.
Adapt a battle-tested source prompt (e.g. `wshobson/agents`,
`VoltAgent/awesome-claude-code-subagents`) where one fits — never a verbatim
copy. Keep it 40–70 lines.

## Gate: the factory checklist

Run `references/factory-checklist.md`. An agent that fails any item (single
mission · output contract defined · forbidden actions stated · routing justified ·
no roster duplication) is NOT written. Record the pass/fail outcome.

## Log every creation

Always record it in the loop/session report: name, scope, rationale, source-task
id. If `.forge/memory/` exists, also file a `reference` memory fact.
The agent's own Provenance section carries the same trail.

## Pruning

`forge-librarian` flags project-local agents unused for a long span; deletion is
**human-approved only**. The factory creates; the librarian proposes removal;
the human decides.

## Command surfaces

Two commands drive this skill; both are also natural-language-invocable
(subject to `forge.md`'s `natural-language-invocation` toggle and the
human-turn-only rule, `docs/conventions.md` "Trust boundary — specs + NL
scoping amendment") and both gate every write behind a structured-question
approval — this skill never creates or edits an agent silently.

- **Creation — `/forge:agent`.** Establish the recurring task type → check
  the roster first (this skill's no-roster-fit precondition — stop if an
  existing agent already fits) → one batched structured-question flow
  (name, mission, builder vs judge, default routing, skills to attach,
  placement) → generate from `references/agent-template.md`, gated by
  `references/factory-checklist.md` → report the file, the routing match,
  and suggest `/forge:seed` for later enrichment. Full flow:
  `commands/agent.md`.
- **Seeding — `/forge:seed`.** Enrich an EXISTING roster or project-local
  agent: pick it, inventory its current Attached skills / `tools:` /
  Default routing, then a repeatable proposal-and-multi-select loop
  (unattached library skills, external/plugin skills, rules worth adding,
  memory facts to tag) until the user says "nothing else — done". Full
  flow: `commands/seed.md`.

This skill remains the single source of truth for the agent template and
the Provenance contract; both commands reference it rather than duplicating
the template or the checklist.

## Seeding rules

Enriching an existing agent (`/forge:seed`) follows the same template
contract creation does, plus:

- **Judge `tools:` allowlists are never widened by seeding — hard rule.**
  A read-only judge's tool set is a creation-time (factory-gated) decision
  only; seeding may attach skills and add rules, never expand `tools:`.
- Additions must fit the existing template contract: attached skills are
  appended one line each in the file's existing bullet style; added rules
  live under `## Rules` and must never weaken or remove an existing rule or
  anything under `## Forbidden actions`.
- Every seed run appends one line to `## Provenance` — `- seeded
  <ISO-8601 date>: <what changed>` — append-only, alongside the original
  `created`/`by`/`rationale`/`source-task` fields, so an agent's file
  carries a full history of how it was built and grown.
