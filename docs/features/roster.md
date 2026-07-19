# Agent roster

Twenty routed agents, each spawned by the kernel with an explicit model and
effort (Hard Rule 1 — spawning without both is a protocol violation).
Personas are a display-layer convention only —
[`docs/conventions.md`](../conventions.md), "Dispatch display labels —
persona amendment — 2026-07" — a persona name never appears where a slug is
load-bearing (Routing record, spawn contract, Attempt log, commit history
all use the `forge-*` slug). The kernel itself introduces session reports
and run charters under a twenty-first persona, **örn** — the orchestrator
is not backed by an `agents/*.md` file.

Six agents are **judges** — read-only, never edit: Vera, Iris, Rook, Aegis,
Lex, and (structurally) the JUDGE role inside an inquest tribunal, which has
no standing roster agent of its own.

| Persona | Slug | Default routing | Role | Verified by |
|---|---|---|---|---|
| Brokk | `forge-worker` | routed per task (sonnet/medium typical) | Implements one well-specified queue task from a spawn contract | `forge-verifier` / `forge-ui-verifier` |
| Vera | `forge-verifier` | equal-or-higher than the work it checks | Adversarially verifies a diff against its EARS criteria, gates, and the constitution | the kernel's finding filter |
| Iris | `forge-ui-verifier` | equal-or-higher than the work it checks | Verifies UI/animation output visually — renders and observes, never re-reads code | the kernel's finding filter |
| Rook | `forge-reviewer` | opus/high | Full-tier code review: correctness, silent failures, simplification | the kernel's finding filter (ship-judge widening) |
| Aegis | `forge-security` | opus/high | Security review for auth, input handling, secrets, payment flows | the kernel's finding filter + the Critical-security exploit bar |
| Lex | `forge-legal` | sonnet/medium | Engineering-side license/ToS/compliance checks — judges only, never drafts legal documents | the kernel's finding filter (source-exists check only, never the risk call) |
| Blue | `forge-architect` | judgment-heavy: opus/high | Designs the approach and execution plan for complex or ambiguous tasks | the architect-plan refuter, when the plan touches the tier-escalation checklist |
| Hex | `forge-debugger` | judgment-heavy: opus/high | Roots out one bug via hypothesis→evidence→fix, ships a regression test | `forge-verifier` |
| Pixel | `forge-ui` | well-specified building | Implements frontend/UI work with accessibility and Core Web Vitals built in; also the design-lead persona at spec kickoff | `forge-ui-verifier` (Iris) |
| Flux | `forge-animator` | well-specified building | Implements motion/animation to the project's design system | `forge-ui-verifier` (Iris) |
| Tess | `forge-test-writer` | well-specified building | Writes or repairs tests, closing coverage gaps with a right-sized test pyramid | `forge-verifier` |
| Sage | `forge-researcher` | well-specified / research | Researches docs/web/codebase, returns a distilled implementation brief | kernel synthesis (report task) |
| Tern | `forge-migrator` | well-specified building | Executes mechanical sweeps needing judgment about *what* to change — renames, codemods, dependency bumps | `forge-verifier` |
| Scout | `forge-scout` | well-specified / research | Discovers and vets skills/MCP servers/CLIs — proposes, never installs | kernel synthesis (report task) |
| Atlas | `forge-mapper` | well-specified building | Builds or refreshes the repo map (`.forge/map/`) | `forge-verifier` (low-risk-eligible, docs-only) |
| Page | `forge-librarian` | haiku/low, off the critical path | Consolidates memory, checks map freshness, queue hygiene | not independently verified — consolidation-only, never edits task outcomes |
| Quill | `forge-spec-writer` | sonnet/high | Drafts a brainstormed idea into an approvable spec with EARS criteria | the human at the one approval gate |
| Doc | `forge-triage` | well-specified / research | Bug intake — reproduces, classifies, drafts a ready task | the human/kernel accepting the triage draft |
| Rune | `forge-data` | judgment-heavy for schema/migration work | Owns one database task — schema design, migration, or query tuning | `forge-verifier` |
| Grud | `forge-grunt` | **haiku/low, always** | Executes fully-specified, zero-judgment bulk work; refuses and bounces back when a judgment call is needed | cheapest sufficient path under the Low-risk predicate — never a looser bar for being mechanical-tier |

## Routing tiers, at a glance

| Profile | Model | Effort |
|---|---|---|
| Mechanical, low risk (Grud's permanent home) | haiku | low |
| Well-specified building | sonnet | medium |
| Well-specified, risky | sonnet | high |
| Judgment-heavy (debug unknowns, architecture, review) | opus | high |
| Critical/forensic (security, final gate on big merges) | opus | max |

`opus` is the strongest tier the router ever assigns on its own. `fable` is
a human-authorized escalation only, never a route — see
[Telemetry + Evolve](telemetry-and-evolve.md) for where this ceiling also
binds the routing-tuning recommendation engine.

## Who verifies whom, structurally

- Every builder (Brokk, Pixel, Flux, Tess, Tern, Atlas, Rune, Grud) is
  judged by a separate spawn — `forge-verifier` or `forge-ui-verifier` —
  never by itself (Hard Rule 3), capped at one per task (see
  [Panel policy](verification-economics.md#panel-policy--the-per-task-ceiling)).
- `tier: full` work additionally takes the per-task ship checklist: Rook
  always, Aegis only on a named trigger, Lex only when the diff adds/bumps a
  dependency, vendors code, or adds a service. See
  [Ship/judge panel flow](verification-economics.md#shipjudge-panel-flow-full-tier).
  Standard-tier work never sees this per-task panel — Rook instead runs
  ONCE at wave end over the wave's integrated diff (skipped for an
  all-docs, pin-covered wave, sampled every 4th skip).
- Blue's plans get one adversarial refuter pass — a second architect-tier
  spawn — only when the plan touches the spec pipeline's tier-escalation
  checklist.
- Quill's specs are judged by the human at the one approval gate — never by
  another agent.
- Page (librarian) and Scout/Sage/Doc (research and intake roles) are
  off the adversarial-verify critical path by design — their output feeds
  the next human or kernel decision rather than shipping as a diff.
