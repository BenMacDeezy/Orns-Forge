# Agents lifecycle

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## .forge/agents/ (project-local agents)

> Amended by: "Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)"

Custom agents the agent factory (`forge:agent-factory`, spec §6.4) generates for a single project live in `.forge/agents/<name>.md`, git-tracked with the repo. Agents worth reusing across projects go in the plugin's `agents/` instead. The file format is the standing-roster format (spec §6.1) plus a provenance block.

Because the harness discovers agents under `.claude/agents/`, the factory also mirrors each project-local agent to `.claude/agents/<name>.md`; the `.forge/agents/` copy is canonical (git-tracked, tool-agnostic, GUI-parseable) and the mirror is a load shim.

### Frontmatter (flat YAML, exact names)

| Field | Type / values | Notes |
|---|---|---|
| name | string | unique kebab-case; prefix with the project or role (e.g. `acme-fixture-builder`) to avoid clashing with roster names |
| description | string | one line — when the router should pick this agent |
| model | haiku \| sonnet \| opus | the default-route model; effort is stated in the body (spec §6.1) |
| tools | comma-separated list, or omitted | optional allowlist; omit to inherit defaults |

### Body sections (exact headings, in this order)

```
## Mission          single purpose, one paragraph
## Attached skills   skills invoked on start (names), or "none"
## Default routing   `<model> / <effort>` + one-line justification
## Rules             how it works within scope
## Output contract   the exact structured final-message shape
## Forbidden actions what it must never do (always includes: never touch .forge/)
## Provenance        created / by / rationale / source-task (see below)
```

The **Provenance** section is four fields, one per line:

```
- created: <ISO-8601 date>
- by: forge-agent-factory
- rationale: <why this agent was needed — the recurring task type no roster agent fit>
- source-task: <task id that triggered creation, or "onboard">
```

### Rules

- The factory checklist (single mission · output contract defined · forbidden actions stated · routing default justified · no roster duplication) gates creation. An agent failing any item is not written.
- `forge-librarian` flags project-local agents unused for a long span; deletion is **human-approved only** (spec §6.4). The roster never regrows into a graveyard.

## Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)

> Amended by: "Agent promotion and retention — 2026-07-19 (fg-b0305+fg-b0306, spec-b71f3a)"

NORMATIVE. Response to `.forge/specs/2026-07-19-universal-agent-dispatch-
lifecycle.md` (spec-b71f3a, AC-Ephemeral). Defines `.forge/agents/archive/
<name>.md` as a third agent-file tier, alongside the roster (`agents/`) and
project-local standing (`.forge/agents/`) tiers ".forge/agents/
(project-local agents)" (above) documents:

- **Kernel-minted, fast path only.** An archive-tier file is written by the
  kernel's fast-path minting flow (`skills/agent-factory/SKILL.md`, "Fast
  path" — the mint-flow mechanics themselves land with fg-b0302, not here);
  never by `/forge:agent`'s interactive flow, and never hand-authored.
- **Never mirrored to `.claude/agents/`.** Unlike a project-local standing
  agent, whose file "the factory also mirrors ... to `.claude/agents/
  <name>.md`" (above), an archive-tier file stays un-mirrored — it is never
  a directly-nameable harness `subagent_type` on its own; the kernel
  dispatches it by injecting the file's content as the spawn contract into
  the harness's generic transport (spec-b71f3a AC5).
- **Never a standing-team member.** An archive-tier agent occupies no
  moment, even transiently, on the roster or the project-local standing
  team; it joins one only through the human-gated promotion flow
  (spec-b71f3a AC-Promotion) — the promotion flow and the retention/pruning
  rules bounding an unpromoted file's lifespan land with fg-b0305 and
  fg-b0306 respectively; this section defines the tier's shape only, cited
  forward rather than built here.
- **Naming.** Follows the existing project-local naming convention verbatim
  (above: prefix with the project or role, e.g. `acme-fixture-builder`) —
  never prefixed `forge-`, so an archive-tier file can never be mistaken for
  a shipped roster agent by name alone.
- **Lifecycle.** Every archive-tier file's Provenance carries `lifecycle:
  ephemeral` (`skills/agent-factory/references/agent-template.md`); the
  field flips to `standing` only at promotion, never in place beforehand.

## Agent promotion and retention — 2026-07-19 (fg-b0305+fg-b0306, spec-b71f3a)

> Amends: "Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)" (above).

NORMATIVE. Response to `.forge/specs/2026-07-19-universal-agent-dispatch-
lifecycle.md` (spec-b71f3a), "Usage-based promotion" and "Retention and
pruning." Both land in this one append per the spec's own collision
mitigation (Risks, "`docs/conventions.md` append collision") — promotion
(fg-b0305) and the pruning-scope extension (fg-b0306) are the two halves
of the single anti-graveyard control the ephemeral tier moved from
CREATION to here (above, "Universal Forge-agent dispatch — 2026-07-19
(fg-b0303, spec-b71f3a)," "Why now, not before").

### Usage-based promotion (fg-b0305)

An archive-tier ephemeral agent (`.forge/agents/archive/<name>.md`, above,
"Ephemeral agent tier") that keeps getting matched earns its way onto the
standing team — always a PROPOSAL, never an automatic promotion.

- **Threshold.** 3 or more dispatches within any rolling 14-day window,
  measured by `tools/agent_usage.py`'s `count_dispatches` against
  `.forge/agents/usage/<name>.jsonl` (`--window-days`, `--now`) — the
  independent, `tools/telemetry.py`-free usage aggregator "Universal
  Forge-agent dispatch" (above) already establishes.
- **Who, and when.** `forge-librarian` (Page) files the proposal at its
  next off-critical-path pass — session start or idle, never inside a task
  dispatch, its existing scoping (`agents/forge-librarian.md`) unchanged.
- **Interactive proposal.** A structured `AskUserQuestion` — per "Asking
  the user questions" (above) — mirroring `/forge:agent`'s own "Placement"
  question (`commands/agent.md`, step 2): project-local
  `.forge/agents/<name>.md` is the recommended default; global
  `agents/<name>.md` is offered as an explicit alternative only when the
  agent's mission reads as project-agnostic.
- **Headless / standing-consent.** No interactive gate this session —
  record the proposal prominently in the session report instead of
  blocking, the same surfacing style `forge:kernel`'s SYNC step already
  uses for unratified spec deltas (`skills/kernel/SKILL.md`, "Unratified
  spec deltas").
- **On APPROVE.** Move the file from `.forge/agents/archive/<name>.md` to
  the approved destination, mirror it to `.claude/agents/<name>.md` per the
  existing project-local mirroring rule (".forge/agents/ (project-local
  agents)," above), set `lifecycle: standing`
  (`skills/agent-factory/references/agent-template.md`'s Provenance
  field), and append `- promoted: <ISO-8601 date> — evidence: N dispatches
  in M days` to Provenance — append-only, the same discipline `/forge:seed`
  already applies to its own Provenance line ("Seeding rules,"
  `skills/agent-factory/SKILL.md`).
- **On DECLINE.** Record a `decision` fact via `forge:memory` (what was
  declined, why, when) — mirroring `forge:equip`'s skip-decision memory
  ("Capability-gap audits (equip) — 2026-07," above) — and do NOT
  re-propose that agent until its usage count has doubled again from the
  count at decline time, so one decline doesn't renew nagging on every
  later dispatch.
- **Tools never widen at promotion.** A judge agent's `tools:` allowlist is
  copied verbatim from the ephemeral original at promotion — never
  widened; only a later, separate, human-invoked `/forge:seed` pass may
  touch it, and even then never to widen a judge's allowlist ("Seeding
  rules," `skills/agent-factory/SKILL.md` — unchanged, inherited).

### Retention and pruning scope extension (fg-b0306)

Extends the existing librarian pruning rule — "`forge-librarian` flags
project-local agents unused for a long span; deletion is human-approved
only" (`skills/agent-factory/SKILL.md`, "Pruning") — to explicitly cover
`.forge/agents/archive/*.md` alongside `.forge/agents/*.md`. Wording/scope
extension only; no new deletion mechanism.

- WHEN an archive-tier agent is older than 90 days and has never crossed
  the promotion threshold above, `forge-librarian` flags it as a pruning
  candidate at its next off-critical-path pass — the same pass as the
  threshold check above, not a second one.
- Deletion remains human-approved only, identical to standing pruning; the
  librarian proposes, a human disposes.
