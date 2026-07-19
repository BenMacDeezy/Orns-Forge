# Forge file conventions (v1 — Phase 1)

Single source of truth for `.forge/` artifact formats. The queue skill, kernel skill, and validator implement this contract exactly.

<!-- content-neutral exception to the tail-append rule: TOC + amended-by lines below are pure additions, no existing prose changed -->

**Table of contents** — topic-grouped; amending sections are nested under the parent topic(s) they amend, so a reader landing on a parent section can't miss its amendments.

- .forge/ layout (Phase 1 subset)
- Task files
  - Parallel dispatch (Waves amendment, 2026-07-17)
  - Claims and crash recovery — amendment (2026-07-17)
- forge.md (project config)
  - Budget keys — amendment (2026-07-17)
  - UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18
- Repo map files (`.forge/map/`) — Phase 2
- Project memory files (`.forge/memory/`) — Phase 2
  - Memory — agents tag + craft memory (2026-07-17)
  - Craft-memory bleed check — 2026-07
- Spec files (Phase 3)
- constitution.md (Phase 3)
- project.md (project charter)
- .forge/agents/ (project-local agents)
  - Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)
    - Agent promotion and retention — 2026-07-19 (fg-b0305+fg-b0306, spec-b71f3a)
- Trust boundary
  - Trust boundary — specs + NL scoping amendment (2026-07-17)
- Offline merge convention
- schema-version
- Asking the user questions (interactive skills)
- Features (forge.md)
  - Trust boundary — specs + NL scoping amendment (2026-07-17) (also amends Trust boundary, above)
- Loop patterns
- Workflow executor
- Run charter (2026-07-17)
- Model vocabulary — fable amendment (2026-07-17)
- Report tasks (finder pattern) — 2026-07-17
  - UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18 (also amends forge.md (project config), above)
  - Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)
    - Dispatch-provenance flag — 2026-07-19 (fg-b0310, spec-b71f3a)
- Prefer the agent factory over ad hoc generic dispatch — 2026-07-19
  - Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a) (also amends Report tasks (finder pattern), above)
- Freshness convention (date-sensitive skills) — 2026-07-18
- Capability-gap audits (equip) — 2026-07
- Latency rules — ship-review overlap, mechanical bounces, batch gates, sliding-window dispatch — 2026-07
- Low-risk verification (standard sub-class) — 2026-07
- Dispatch display labels — 2026-07
  - Dispatch display labels — persona amendment — 2026-07
  - Dispatch display labels — task-name amendment — 2026-07-18
  - Dispatch display labels — role-label amendment — 2026-07-18
- Telemetry vocabulary — 2026-07
  - Token capture — 2026-07-19 (fg-a10212)
- Routing-tuning recommendations (Evolve analogue) — 2026-07
- Verifier-finding filter (bounce pre-check) — 2026-07
  - Ship-judge widening + Critical-security exploit bar — 2026-07-18
- Inquest tribunal — 2026-07
- Idle-wait discipline — 2026-07
- Architect-plan refuter — 2026-07
- Design foundation artifact (`.forge/design/foundation.md`) — 2026-07-18
- Design-conformance elevation (Iris) — 2026-07-18
- Sharded fan-out — 2026-07-18
  - Sharded fan-out — per-shard write surfaces amendment (2026-07-19, fg-b0401)
- Grud routing (goblin grunt) — 2026-07-18
- Verification economics — 2026-07-18 (fg-a10901)
- Verification infrastructure — 2026-07-18 (fg-a10908)
- Clean-context debug escalation — 2026-07-18 (fg-a10701)
- Spec-time boundary maps — 2026-07-18 (fg-a10910)
- Finding severity + confidence — 2026-07-18 (fg-a10911)

### Shards manifest

Every section body now lives in one of the shard files below (`docs/conventions/<shard>.md`); this file is the index only — preamble, TOC (above), and this manifest. Each line maps one section name (as it appears in the TOC above) to the shard file holding its body. A section nested under two TOC parents (a multi-parent amendment) lists only the ONE shard holding its body — the secondary TOC parent is a name-only pointer, not a second copy.

- `.forge/ layout (Phase 1 subset)` -> `docs/conventions/artifact-formats.md`
- `Task files` -> `docs/conventions/artifact-formats.md`
- `forge.md (project config)` -> `docs/conventions/config-and-features.md`
- `Repo map files (`.forge/map/`) — Phase 2` -> `docs/conventions/artifact-formats.md`
- `Project memory files (`.forge/memory/`) — Phase 2` -> `docs/conventions/memory.md`
- `Spec files (Phase 3)` -> `docs/conventions/artifact-formats.md`
- `constitution.md (Phase 3)` -> `docs/conventions/artifact-formats.md`
- `project.md (project charter)` -> `docs/conventions/artifact-formats.md`
- `.forge/agents/ (project-local agents)` -> `docs/conventions/agents-lifecycle.md`
- `Trust boundary` -> `docs/conventions/trust-and-security.md`
- `Offline merge convention` -> `docs/conventions/artifact-formats.md`
- `schema-version` -> `docs/conventions/artifact-formats.md`
- `Asking the user questions (interactive skills)` -> `docs/conventions/config-and-features.md`
- `Parallel dispatch (Waves amendment, 2026-07-17)` -> `docs/conventions/artifact-formats.md`
- `Claims and crash recovery — amendment (2026-07-17)` -> `docs/conventions/artifact-formats.md`
- `Budget keys — amendment (2026-07-17)` -> `docs/conventions/config-and-features.md`
- `Features (forge.md)` -> `docs/conventions/config-and-features.md`
- `Loop patterns` -> `docs/conventions/dispatch-and-routing.md`
- `Workflow executor` -> `docs/conventions/dispatch-and-routing.md`
- `Run charter (2026-07-17)` -> `docs/conventions/dispatch-and-routing.md`
- `Model vocabulary — fable amendment (2026-07-17)` -> `docs/conventions/dispatch-and-routing.md`
- `Memory — agents tag + craft memory (2026-07-17)` -> `docs/conventions/memory.md`
- `Trust boundary — specs + NL scoping amendment (2026-07-17)` -> `docs/conventions/trust-and-security.md`
- `Report tasks (finder pattern) — 2026-07-17` -> `docs/conventions/dispatch-and-routing.md`
- `UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18` -> `docs/conventions/dispatch-and-routing.md`
- `Prefer the agent factory over ad hoc generic dispatch — 2026-07-19` -> `docs/conventions/dispatch-and-routing.md`
- `Freshness convention (date-sensitive skills) — 2026-07-18` -> `docs/conventions/config-and-features.md`
- `Capability-gap audits (equip) — 2026-07` -> `docs/conventions/config-and-features.md`
- `Latency rules — ship-review overlap, mechanical bounces, batch gates, sliding-window dispatch — 2026-07` -> `docs/conventions/dispatch-and-routing.md`
- `Low-risk verification (standard sub-class) — 2026-07` -> `docs/conventions/verification.md`
- `Dispatch display labels — 2026-07` -> `docs/conventions/telemetry-and-labels.md`
- `Dispatch display labels — persona amendment — 2026-07` -> `docs/conventions/telemetry-and-labels.md`
- `Dispatch display labels — task-name amendment — 2026-07-18` -> `docs/conventions/telemetry-and-labels.md`
- `Dispatch display labels — role-label amendment — 2026-07-18` -> `docs/conventions/telemetry-and-labels.md`
- `Telemetry vocabulary — 2026-07` -> `docs/conventions/telemetry-and-labels.md`
- `Routing-tuning recommendations (Evolve analogue) — 2026-07` -> `docs/conventions/telemetry-and-labels.md`
- `Verifier-finding filter (bounce pre-check) — 2026-07` -> `docs/conventions/verification.md`
- `Craft-memory bleed check — 2026-07` -> `docs/conventions/memory.md`
- `Inquest tribunal — 2026-07` -> `docs/conventions/verification.md`
- `Ship-judge widening + Critical-security exploit bar — 2026-07-18` -> `docs/conventions/verification.md`
- `Idle-wait discipline — 2026-07` -> `docs/conventions/verification.md`
- `Architect-plan refuter — 2026-07` -> `docs/conventions/verification.md`
- `Design foundation artifact (`.forge/design/foundation.md`) — 2026-07-18` -> `docs/conventions/design.md`
- `Design-conformance elevation (Iris) — 2026-07-18` -> `docs/conventions/design.md`
- `Sharded fan-out — 2026-07-18` -> `docs/conventions/dispatch-and-routing.md`
- `Sharded fan-out — per-shard write surfaces amendment (2026-07-19, fg-b0401)` -> `docs/conventions/dispatch-and-routing.md`
- `Grud routing (goblin grunt) — 2026-07-18` -> `docs/conventions/dispatch-and-routing.md`
- `Verification economics — 2026-07-18 (fg-a10901)` -> `docs/conventions/verification.md`
- `Verification infrastructure — 2026-07-18 (fg-a10908)` -> `docs/conventions/verification.md`
- `Clean-context debug escalation — 2026-07-18 (fg-a10701)` -> `docs/conventions/verification.md`
- `Spec-time boundary maps — 2026-07-18 (fg-a10910)` -> `docs/conventions/verification.md`
- `Finding severity + confidence — 2026-07-18 (fg-a10911)` -> `docs/conventions/verification.md`
- `Token capture — 2026-07-19 (fg-a10212)` -> `docs/conventions/telemetry-and-labels.md`
- `Ephemeral agent tier — 2026-07-19 (fg-b0301, spec-b71f3a)` -> `docs/conventions/agents-lifecycle.md`
- `Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)` -> `docs/conventions/dispatch-and-routing.md`
- `Dispatch-provenance flag — 2026-07-19 (fg-b0310, spec-b71f3a)` -> `docs/conventions/dispatch-and-routing.md`
- `Agent promotion and retention — 2026-07-19 (fg-b0305+fg-b0306, spec-b71f3a)` -> `docs/conventions/agents-lifecycle.md`

