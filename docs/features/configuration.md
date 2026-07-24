# Configuration reference (`.forge/forge.md`)

Canonical template:
`skills/kernel/references/forge-config-template.md`. Format contract:
[`docs/conventions.md`](../conventions.md), "forge.md (project config)" and
"Features (forge.md)". `/forge:settings` is the canonical viewer/editor for
everything on this page.

Current provider configuration and cross-model dispatch are documented in
[Cross-model orchestration](cross-model-orchestration.md). That page is the
current-status companion to the historical rollout notes retained below.

```markdown
# Forge config

## Routing overrides
(none)

## Features
- natural-language-invocation: on
- continuous-loop: on
- auto-queue-capture: on
- express-lane: on
- workflow-executor: on
- providers: off

## Budgets
- max-tasks-per-session: none
- session-token-cap: none
- max-provider-dispatches-per-session: none
- provider-dispatch-checkpoint-every: 10

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: auto

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
```

A `forge.md` written before a section existed simply has no entries there —
every missing toggle or key behaves as its default; `/forge:settings`
offers to write the section in.

## Routing overrides

Optional lines, `<pattern or area>: <model>/<effort> — <reason>`. Checked
first, before the ROUTE+DISPATCH table, with one stated line of reasoning
required for any override. A `fable/<effort>` line is also valid here —
writing one **is** the human authorization the kernel needs to use `fable`
for that area; the router never picks it on its own.

## Features — six toggles; every one defaults `on` except `providers`

| Toggle | Default | Meaning |
|---|---|---|
| `natural-language-invocation` | on | Forge skills fire from plain conversation. `off` = command-only. |
| `continuous-loop` | on | Completing a wave re-checks the queue once for newly-ready tasks and continues. `off` = exactly one wave per invocation. |
| `auto-queue-capture` | on | Task-shaped ideas mentioned without an execution ask are OFFERED for capture — one structured offer, never a silent create. |
| `express-lane` | on | Standard-tier ideas skip the full spec pipeline via one structured confirm card. Never applies to `tier: full`. |
| `workflow-executor` | on | Parallel-eligible waves and full-tier ship reviews run as deterministic Workflow scripts when the harness offers the Workflow tool; identical `.forge/` state transitions either way. |
| `providers` | off | External providers (second opinions, cross-model review, and — Phase 2 — worker dispatch) may be enabled for this repo. **The one toggle that defaults off** — `off` means Forge never invokes an external provider CLI. `on` unlocks per-provider enablement, each still gated by its own once-per-provider-per-repo-per-machine trust confirmation; see [Trust model](trust-model.md) and `docs/conventions.md`, "Providers Feature — per-repo opt-in and per-provider trust gate — 2026-07-19." |

`continuous-loop: on` is standing human authorization for the loop to keep
pulling waves — granted by enabling the setting. No toggle ever overrides a
budget cap, the spec approval gate for full-tier work, or the trust
boundary.

## Budgets

- `max-tasks-per-session` — the **primary enforced cap**. The kernel counts
  dispatches per session and stops with a session report when it's reached.
  A `budget-guard` PreToolUse hook may additionally deny dispatches past the
  cap, as a backstop; the kernel's own count is the portable mechanism.
- `session-token-cap` — **advisory only**. The model may stop early on its
  own spend estimate; it is not an enforcement mechanism.
- `max-provider-dispatches-per-session` (default `none`) — counts
  external-provider dispatches and is checked at ROUTE time. `none` uses
  the shipped checkpoint model instead of a hard ceiling; a NUMERIC value
  retains the original hard-cap semantics, dispatches no further external
  work at that cap, and states so in the session report. Never folded into
  `session-token-cap` — no cross-currency estimate ever.
- `provider-dispatch-checkpoint-every` (default `10`) — at each multiple,
  the kernel posts the one-line checkpoint with the running tally,
  per-provider counts, and exact model slugs, then continues unless the
  human objects. Provider rate-limit errors are surfaced verbatim. See
  `docs/conventions.md`, "Provider dispatch checkpoints — 2026-07-22."

Before the 2026-07-22 amendment,
`max-provider-dispatches-per-session` (default `10`) was the shipped hard
ceiling; this is historical context, not the current default.

## Queue

- `claim-staleness-hours` (default `0.5`) — how long an `active` claim can
  sit before SYNC resets it to `ready` (unless uncommitted edits in its
  declared scope mean it goes to `blocked` for human review instead).
- `max-parallel-tasks` (default `auto`) — the sliding-window concurrency cap
  on simultaneous worker spawns. It caps *how many run at once*, never how
  many eligible tasks a session may eventually run — surplus tasks dispatch
  the moment a slot frees. Wave-parallel batches and shard swarms
  ([sharded fan-out](sharded-fan-out.md)) share this ONE cap; there is no
  second, shard-private window.

  Accepts `auto` (default), `none`, or a positive integer:
  - **`auto`** derives the window from the machine — `min(cores - 2, 16)`,
    floored at 1. Two cores stay free so the orchestrating session remains
    responsive while workers build, and the ceiling stops N concurrent
    worktree installs/builds from thrashing disk and RAM. (Past the physical
    ceiling you get slower, flakier runs — and bogus build failures cost real
    tokens on bounce + re-verify.) On a 32-core box that is 16, not 3.
  - **`none`** removes the window entirely — unbounded simultaneous spawns.
    Supported deliberately, but whoever sets it owns the resource contention
    and any rate-limit fallout.
  - **a positive integer** is used verbatim, no derivation.

  This is a *throughput* knob, not a spend guard — total cost is bounded
  separately by `max-tasks-per-session`, `session-token-cap`,
  `max-provider-dispatches-per-session`, and `budget-guard`, none of which
  this setting can override.

## Gates

`build` / `test` / `lint` accept exact shell commands, or `(auto-detect)` to
let the kernel infer them from the repo (package.json scripts, Makefile,
pyproject, etc.) and write what it found back into this file. If
`.forge/forge.md` exists but can't be parsed and the repo has recognizable
tooling, the kernel treats it like `(auto-detect)` and recovers the file. A
genuinely empty repo (no tooling, no source files) enters GATES-PENDING mode
instead of halting — see [`docs/conventions.md`](../conventions.md),
"Empty-repo gates-pending mode." An **untrusted** `.forge/`'s stored Gates
commands are never executed regardless — see
[Trust model](trust-model.md).

## Historical rollout notes

External workers and cross-model judges now route through the same provider
gates described on this page. The kernel remains Claude-native: it records
and controls the workflow while a provider fills only a routed role. For the
current role precedence, gate sequence, labels, and review floor, see
[Cross-model orchestration](cross-model-orchestration.md).
