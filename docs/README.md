# Forge documentation

Forge is a markdown-defined autonomous development system for Claude Code. It
turns approved work into queue tasks, routes builders and independent judges,
and records what it learns so a project can improve without making automation
opaque. For the connected view, start with the [systems overview](systems.md).

## Architecture

- [Architecture deep-dive](architecture.md) — kernel and spec-pipeline flows,
  plus their hand-off points.

## Feature guides

### Orchestration

- [Queue format + EARS](features/queue-and-ears.md) — task lifecycle and
  checkable acceptance criteria.
- [Cross-model orchestration](features/cross-model-orchestration.md) — gated
  providers, routing, checkpoints, and bounded consensus.
- [Sharded fan-out](features/sharded-fan-out.md) — splitting disjoint work
  across workers and reassembling it safely.

### Verification

- [Verification economics](features/verification-economics.md) — grouped
  verification, finding filters, marginal-gain limits, and ship review.
- [Inquest tribunal](features/inquest.md) — the finder, refuter, and judge
  workflow for deep investigations.

### Providers & autonomy

- [Autonomy and control](features/autonomy-and-control.md) — initiation
  levels, non-negotiable gates, and bounded workflow loops.
- [Configuration reference](features/configuration.md) — Features, budgets,
  queue controls, profiles, and routing overrides.

### Memory & trust

- [Memory + craft store](features/memory.md) — project facts, reusable craft
  knowledge, and supersession.
- [Trust model](features/trust-model.md) — how Forge handles unfamiliar
  repository state before acting on it.

### Lifecycle

- [Design foundation + Iris elevation](features/design-foundation.md) — visual
  direction and rendered UI verification.
- [Agent roster](features/roster.md) — Forge roles, routing tiers, and judge
  boundaries.
- [Telemetry + Evolve](features/telemetry-and-evolve.md) — evidence-led
  routing recommendations and human ratification.
- [Update system](features/update-system.md) — update checks and the explicit
  update workflow.

## Reference and operations

- [Conventions corpus](conventions.md) — normative artifact, routing,
  verification, security, memory, and telemetry conventions.
- [Profile comparison](profile-comparison.md) — the available operating
  profiles and their trade-offs.
- [Releasing](releasing.md) — how the filtered public distribution is made.
- [Customization persistence](customization-persistence.md) — which settings
  survive an update and where they live.
