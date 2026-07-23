# Design foundation + Iris elevation

Canonical protocol: [`docs/conventions.md`](../conventions.md), "Design
foundation artifact (`.forge/design/foundation.md`) — 2026-07-18" and
"Design-conformance elevation (Iris) — 2026-07-18".

## Why this exists

A Forge session shipped a functional MVP with bare default shadcn UI —
"dogshit ui, functional MVP not a product" — because UI tasks carried
functional criteria but zero design direction, and the UI-verifier had no
design intent to check output against. The fix: a project or spec with UI
work gets its design foundation established **at kickoff**, in parallel
with the technical decomposition, never a later bolted-on phase.

## The artifact

`.forge/design/foundation.md` — one file per project, not one per spec. The
first spec whose decomposition includes a `ui` or `forge-animator` item
creates it; every later UI-touching spec amends it in place via its
`## Amendments` section rather than forking a parallel file. Body sections,
in order: Visual identity, Token system, Layout language, Component
patterns, Interaction personality, Candidate directions, Amendments.

The chosen direction is written only after a human picks it at the spec
pipeline's [one approval gate](../architecture.md#data-flow-the-spec-pipeline)
— the design-lead persona (Pixel/`forge-ui` acting as design lead) proposes
2-3 **distinct** professional directions (distinct in visual identity and
tone, not palette variations of one idea) and holds them as candidates,
never self-selecting on the human's behalf. Rejected alternatives stay in
`## Candidate directions` even after one is chosen, so the reasoning
survives.

A project with no UI work never gets this file — no ceremony where it
doesn't apply, and no task is ever blocked waiting on a foundation that was
never triggered.

## Binding

When a `forge-ui` or `forge-animator` task dispatches in a project that has
a foundation file, the spawn contract references it by path, and the
attached craft skills (`visual-polish-and-craft`, `ui-behavior-correctness`,
`component-system-shadcn-radix`) pull tokens/patterns from the foundation
rather than reaching for bare framework defaults. A project with no
foundation file dispatches exactly as before — the binding is conditional,
never a hard requirement.

## Iris elevation — the missing-foundation case

A project can reach a UI-verify pass before any spec ever ran the design
direction step, so a foundation can legitimately not exist yet when Iris
(`forge-ui-verifier`) verifies. Her output contract never resolves that gap
to either extreme — rubber-stamping bare defaults (silent pass) or hard
blocking a task on a decision only a human can make.

- **Conformance path (foundation exists).** Iris checks rendered output
  against the foundation's tokens/visual identity/layout language as part
  of the acceptance bar. A gap is a real finding in her DESIGN CONFORMANCE
  field, tagged MECHANICAL or JUDGMENT like any other defect, and can drive
  `VERDICT: FAIL` through the normal path.
- **Elevation path (no foundation).** Iris reports the gap in her ELEVATION
  field instead — 2-3 concrete design directions proposed from what she
  observed, the same shape as the design-lead's spec-kickoff proposal, but
  authored by her since no spec ran that step for this project. A missing
  foundation is never, by itself, a FAIL.

The channel is a **human question**, not a bounce-loop: ELEVATION is a
decision only a human can make, surfaced the same way any other Forge
decision point asks one. The task's own verdict and integration proceed
independently of when or whether that question gets answered. If the human
picks a direction, it's written into the foundation through the normal
spec/amendment path, so later tasks bind to it and later Iris runs check
conformance instead of elevating again.

Once a foundation exists, the human's chosen direction is the sole arbiter
— Iris judges only whether shipped work *applies* that direction, never
imposing a preferred aesthetic of her own. This is elevate-and-propose,
never a bounce-loop on subjective taste.
