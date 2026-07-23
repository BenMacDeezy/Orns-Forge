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
- **Archive (kernel fast-path minting only):** write
  `.forge/agents/archive/<name>.md` — never mirrored, never standing-team
  membership on creation (`docs/conventions.md`, "Ephemeral agent tier —
  2026-07-19 (fg-b0301, spec-b71f3a)"). `/forge:agent`'s human-initiated
  flow never targets this tier; the fast-path mint flow that writes here
  is fg-b0302's own build.

## Build the agent (anatomy — spec §6.1)

Start from `references/agent-template.md` and fill every section: mission (single
purpose), attached skills, default routing (model + effort + one-line
justification), optional tool allowlist, output contract (exact structured
shape), forbidden actions (always incl. "never touch `.forge/`"), and provenance.
Adapt a battle-tested source prompt (e.g. `wshobson/agents`,
`VoltAgent/awesome-claude-code-subagents`) where one fits — never a verbatim
copy. Target length scales with the role: 40–70 lines for a simple builder
with a short mission; a protocol-heavy judge or a role with a detailed
output contract (see `forge-verifier`, `forge-ui-verifier`) commonly runs
80–150 lines. Match the mission's real complexity — don't pad, but don't
force-fit a rich role into an artificially short file.

## Gate: the factory checklist

Run `references/factory-checklist.md`. An agent that fails any item (single
mission · output contract defined · forbidden actions stated · routing justified ·
no roster duplication) is NOT written. Record the pass/fail outcome.

## Log every creation

Always record it in the loop/session report: name, scope, rationale, source-task
id. If `.forge/memory/` exists, also file a `reference` memory fact.
The agent's own Provenance section carries the same trail.

## Promotion (usage-earned, human-ratified)

Response to `.forge/specs/2026-07-19-universal-agent-dispatch-lifecycle.md`
(spec-b71f3a, "Usage-based promotion" AC13-AC18). Full normative text:
`docs/conventions.md`, "Agent promotion and retention — 2026-07-19
(fg-b0305+fg-b0306, spec-b71f3a)" — cited here, not restated. An archive-tier
ephemeral agent (above, "Archive (kernel fast-path minting only)") that
keeps getting matched earns its way onto the standing team; this is the
Pruning section's symmetric counterpart — the anti-graveyard control that
moved off CREATION now lives on both ends: Promotion for agents worth
keeping, Pruning (below) for agents that aren't.

- **Threshold.** 3+ dispatches within any rolling 14-day window, measured
  via `tools/agent_usage.py` (`count_dispatches`, `--window-days`, `--now`)
  against `.forge/agents/usage/<name>.jsonl`.
- **Who proposes, and when.** `forge-librarian` files the promotion
  PROPOSAL — never automatic — at its next off-critical-path pass (session
  start or idle; never inside a task dispatch, its existing scoping
  unchanged).
- **Interactive.** A structured `AskUserQuestion`, mirroring
  `/forge:agent`'s own "Placement" question (`commands/agent.md`):
  project-local `.forge/agents/<name>.md` (recommended default), with
  global `agents/<name>.md` offered only when the mission reads as
  project-agnostic.
- **Headless / standing-consent.** No blocking gate — record the proposal
  prominently in the session report instead, the same surfacing style as
  the existing unratified-spec-delta flag at SYNC.
- **On APPROVE.** Move archive → destination, mirror to `.claude/agents/`
  per the existing project-local mirroring rule (above), set `lifecycle:
  standing`, and append `- promoted: <ISO-8601 date> — evidence: N
  dispatches in M days` to Provenance — append-only, the same discipline
  `/forge:seed`'s own Provenance line follows. Also add the promoted
  agent's slug to `tools/telemetry.py`'s `AGENT_SLUGS` so its dispatches
  attribute in telemetry from promotion onward — a manual edit at
  promotion time, not dynamic discovery.
- **On DECLINE.** Record a `decision` fact via `forge:memory` (what/why/when)
  — mirroring `forge:equip`'s skip-decision memory — and never re-propose
  until usage has doubled again from the count at decline.
- **Tools never widen at promotion.** A judge's `tools:` allowlist is
  copied verbatim from the ephemeral original — never widened here; only a
  later, separate, human-invoked `/forge:seed` pass may touch it, and even
  then never to widen a judge's allowlist ("Seeding rules," below —
  unchanged, inherited).

## Pruning

`forge-librarian` flags project-local agents unused for a long span —
explicitly including archive-tier ephemeral agents
(`.forge/agents/archive/*.md`, not just `.forge/agents/*.md`; see
`docs/conventions.md`, "Agent promotion and retention — 2026-07-19
(fg-b0305+fg-b0306, spec-b71f3a)" for the 90-day/never-crossed-threshold
rule) — deletion is **human-approved only**. The factory creates; the
librarian proposes removal; the human decides.

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

## Fast path (kernel-initiated ephemeral minting)

Response to `.forge/specs/2026-07-19-universal-agent-dispatch-lifecycle.md`
(spec-b71f3a, AC4-AC8). WHEN the kernel (ROUTE + DISPATCH,
`skills/kernel/SKILL.md`) needs to dispatch and no roster, project-local, or
archive-tier agent's mission already fits, it mints an ephemeral agent
itself — the mechanical portion of `references/factory-checklist.md`, run
inline, no separate spawn, no `AskUserQuestion` (AC4). This is a third,
kernel-only creation surface alongside the two commands above; `/forge:agent`
stays the untouched human-initiated route.

- **First decision unchanged.** "First decision: agent or skill?" above still
  applies first — a reusable procedure defers to `skill-creator`, never a
  fast-path agent.
- **Three-namespace dup scan.** Before minting, scan `agents/*.md`,
  `.forge/agents/*.md`, and `.forge/agents/archive/*.md` by name +
  description — the same scan `commands/agent.md` step 1 performs. A match
  in ANY namespace routes the dispatch to that existing agent instead of
  minting (AC5).
- **Checklist, run inline.** Run `references/factory-checklist.md`'s five
  items against the kernel's own inferred mission/routing/skills — no spawn,
  no `AskUserQuestion`. A failing item means the file is NOT written; the
  kernel falls through to the nearest fitting existing agent (roster,
  project-local, or archive) instead — never an ungated dispatch (AC7).
- **Template fill, direct write.** On a clean pass, fill all six body
  sections (Mission, Attached skills, Default routing, Rules, Output
  contract, Forbidden actions) plus Provenance with `lifecycle: ephemeral`,
  and write directly to `.forge/agents/archive/<name>.md` — never mirrored
  to `.claude/agents/`, never `.forge/agents/` proper (AC6, "Ephemeral agent
  tier — 2026-07-19 (fg-b0301, spec-b71f3a)"). Identical shape to a
  human-initiated creation; only WHO decides name/mission/routing/skills
  (the kernel, inferring from the task at hand) and the absent approval
  gate differ.
- **Log every mint.** Every fast-path mint is recorded in the session
  report — name, scope, rationale, source-task id — per "Log every
  creation" above, with no reduction for being non-interactive (AC8).
- **Operator-profile pause point (reserved, inert until spec-4d2a ships).**
  WHERE an approved, active operator-profile preset
  (`.forge/specs/2026-07-18-operator-profile-system.md`, spec-4d2a, once
  shipped) marks agent creation as a pause point, a structured
  `AskUserQuestion` confirm precedes the ephemeral file write here, like any
  other profile-designated pause point. WHERE no approved profile system
  exists yet, or none is active, this fast path proceeds exactly as
  specified above with zero added latency — the hook is inert-but-correct
  and needs no revisit when spec-4d2a ships. IF a human declines a
  profile-gated mint, THEN only that dispatch blocks pending human
  direction — never a fallthrough to raw generic dispatch (the
  universal-dispatch invariant, `docs/conventions.md` "Universal
  Forge-agent dispatch — 2026-07-19" section, cited not restated).

Dispatch mechanics (harness transport, injecting the archive file as the
spawn contract) and the "Prefer the agent factory..." mandatory-amendment
land with fg-b0303, not here.

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
- `/forge:seed` growth is expected to push a file past the creation-time
  target in "Build the agent" over an agent's life — that target governs
  shape at creation, not size after repeated seeding, so growth alone is
  not a violation.
