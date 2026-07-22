# Design

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## Design foundation artifact (`.forge/design/foundation.md`) — 2026-07-18

Response to fg-a10601 (parallel design-foundation track, human-ratified
2026-07-18): the user report that a Forge session shipped a functional MVP
with bare default shadcn UI ("dogshit ui, functional MVP not a product")
because UI tasks carried functional criteria but zero design direction, and
the ui-verifier had no design intent to check against. The fix: a project or
spec with UI work gets its design foundation established AT KICKOFF, in
PARALLEL with the technical decomposition — never a later, bolted-on phase.

**Location and cardinality.** `.forge/design/foundation.md` — one file per
project, not one per spec. The first spec whose pre-computed decomposition
includes a `ui` or `forge-animator` item creates it (`skills/spec/SKILL.md`,
"Design direction (UI work only)"); every later UI-touching spec amends it
in place via its `## Amendments` section rather than forking a parallel
file.

### Frontmatter (flat YAML, all fields required, exact names)

| Field | Type / values | Notes |
|---|---|---|
| status | draft \| approved \| superseded | `draft` while directions are proposed and unresolved; only a human sets `approved`, at the SAME gate that approves the owning spec's decomposition |
| spec | path or null | the spec whose approval gate ratified the current chosen direction |
| created | ISO-8601 date | |
| approved-date | ISO-8601 date or null | non-null iff status is `approved` (or `superseded`); null while `draft` |

### Body sections (all required, exact headings, in this order)

```
## Visual identity
## Token system
## Layout language
## Component patterns
## Interaction personality
## Candidate directions
## Amendments
```

- **Visual identity**: the chosen direction's name, one-paragraph
  description, and reference feel — what it should read as (e.g. "confident
  fintech, not playful consumer app").
- **Token system**: color / type / spacing / radius / shadow / motion
  scales — concrete values, not vague adjectives; motion links to
  `forge:motion-design-principles` rather than restating its rules.
- **Layout language**: grid/composition rules, density, information-
  hierarchy conventions.
- **Component patterns**: how common components (nav, cards, forms, tables,
  empty/loading/error states) should look and behave in this direction.
- **Interaction personality**: the motion/feedback character this direction
  implies — the "why" behind the Token system's motion scale.
- **Candidate directions**: the 2-3 DISTINCT professional design directions
  the design-lead persona (Pixel/`forge-ui` acting as design lead) proposed
  before the human's pick — kept as a permanent record even after one is
  chosen, so the rejected alternatives and reasoning survive.
- **Amendments**: dated entries when a later spec extends or refines the
  foundation (a new component pattern, a token added) —
  `### Amendment — <date> — from <task-id>`, append-only, same discipline as
  a spec's own Changelog deltas.

### Seed template

`skills/spec/references/design-foundation-template.md`.

### The gate — same one, not a second one

WHEN the foundation is drafted, THE SYSTEM SHALL have the design-lead
persona propose 2-3 DISTINCT professional design directions derived from
the project concept, presented to the human at the SAME approval gate as
the technical decomposition — the spec pipeline's one human gate
(`skills/spec/SKILL.md`, "Approval gate (the one human gate)"), never a
separate design-approval step. The human picks one, steers a synthesis, or
asks for a redraft; only that human pick gets written into `## Visual
identity` (and onward) as the chosen direction — the design lead proposes,
it never self-selects on the human's behalf.

### No-UI carve-out

WHEN no project or spec has UI work, THE SYSTEM SHALL NOT create
`.forge/design/foundation.md` — no ceremony where it does not apply. A
project that never touches UI simply never has this file, and no task is
ever blocked waiting on one that was never triggered.

### Binding — forge-ui / forge-animator task spawns

WHEN a `forge-ui` or `forge-animator` task dispatches in a project that has
`.forge/design/foundation.md`, THE SYSTEM SHALL bind the spawn contract to
it: the contract references the file by path, and the attached craft skills
(`visual-polish-and-craft`, `ui-behavior-correctness`,
`component-system-shadcn-radix`) pull tokens/patterns FROM the foundation
rather than reaching for bare framework defaults (`agents/forge-ui.md`,
"Foundation binding"; `agents/forge-animator.md` carries the same one-line
invariant). A project with no foundation file (per the no-UI carve-out,
above) dispatches exactly as before this change — the binding is
conditional on the file existing, never a hard requirement that blocks
dispatch.

## Design-conformance elevation (Iris) — 2026-07-18

Response to fg-a10602 (extends fg-a10601's design-foundation track to
`forge-ui-verifier`/Iris, the UI/animation gate): a project can reach a
UI-verify pass before any spec has run the Design direction step
(`skills/spec/SKILL.md`, "Design direction (UI work only)"), so
`.forge/design/foundation.md` can legitimately not exist yet when Iris
verifies. This section fixes the third failure mode the fg-a10601 human
report named: a UI-verifier with no design intent to check against either
rubber-stamps bare framework defaults (silent pass) or blocks the task on
a decision only a human can make (hard fail). Neither is acceptable; Iris's
output contract (`agents/forge-ui-verifier.md`, "Design conformance") never
resolves a missing foundation to either extreme.

**Conformance path (foundation exists).** Iris checks the rendered output
against the foundation's tokens/visual identity/layout language as part of
the acceptance bar, exactly like any other visual defect: a gap is a real
finding reported in her DESIGN CONFORMANCE field, tagged MECHANICAL or
JUDGMENT per the same FAIL-NOTES discipline as every other defect ("Latency
rules — ship-review overlap, mechanical bounces, batch gates,
sliding-window dispatch", above), and can drive VERDICT: FAIL through the
normal path — no separate design-only failure mode, no silent pass.

**Elevation path (no foundation).** Iris reports the gap in her ELEVATION
field instead: 2-3 concrete design directions proposed from the project
concept — the same shape as the design-lead proposal `forge-ui` makes at
spec kickoff (`agents/forge-ui.md`, "Design-lead capability (spec
kickoff)"), but authored by Iris from what she observed, since no spec ran
that step for this project. A missing foundation is never, by itself, a
FAIL — VERDICT is decided on the rest of the acceptance bar as normal.

**The channel is a human question, not a bounce-loop.** ELEVATION is not a
task-level defect the kernel routes back to the worker for a redo: it is a
decision only a human can make, so the kernel surfaces Iris's proposed
directions to the human the same way any other Forge decision point asks
one ("Asking the user questions (interactive skills)", above) — a
structured question when running interactively, prose with the same
discipline otherwise. The task's own verdict and integration proceed
independently of when or whether that question gets answered. If the
human's answer establishes a direction, it is written into
`.forge/design/foundation.md` through the normal spec/amendment path
("Design foundation artifact...", above), so later tasks bind to it and
later Iris runs check conformance against it instead of elevating again.

**Proportionality.** This is elevate-and-propose, never a bounce-loop on
subjective taste. Once a foundation exists, the human's chosen direction is
the sole arbiter: Iris judges only whether shipped work APPLIES that
direction, and never imposes a preferred aesthetic of her own — the same
discipline that keeps the `forge-ui` design lead proposing without
self-selecting.

