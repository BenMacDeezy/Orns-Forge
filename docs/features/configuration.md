# Configuration reference (`.forge/forge.md`)

Canonical template:
`skills/kernel/references/forge-config-template.md`. Format contract:
[`docs/conventions.md`](../conventions.md), "forge.md (project config)" and
"Features (forge.md)". `/forge:settings` is the canonical viewer/editor for
everything on this page.

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

## Budgets
- max-tasks-per-session: none
- session-token-cap: none

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

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

## Features — five toggles, all default `on`

| Toggle | Default | Meaning |
|---|---|---|
| `natural-language-invocation` | on | Forge skills fire from plain conversation. `off` = command-only. |
| `continuous-loop` | on | Completing a wave re-checks the queue once for newly-ready tasks and continues. `off` = exactly one wave per invocation. |
| `auto-queue-capture` | on | Task-shaped ideas mentioned without an execution ask are OFFERED for capture — one structured offer, never a silent create. |
| `express-lane` | on | Standard-tier ideas skip the full spec pipeline via one structured confirm card. Never applies to `tier: full`. |
| `workflow-executor` | on | Parallel-eligible waves and full-tier ship reviews run as deterministic Workflow scripts when the harness offers the Workflow tool; identical `.forge/` state transitions either way. |

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

## Queue

- `claim-staleness-hours` (default `0.5`) — how long an `active` claim can
  sit before SYNC resets it to `ready` (unless uncommitted edits in its
  declared scope mean it goes to `blocked` for human review instead).
- `max-parallel-tasks` (default `3`) — the sliding-window concurrency cap on
  simultaneous worker spawns. It caps *how many run at once*, never how many
  eligible tasks a session may eventually run — surplus tasks dispatch the
  moment a slot frees. Wave-parallel batches and shard swarms
  ([sharded fan-out](sharded-fan-out.md)) share this ONE cap; there is no
  second, shard-private window.

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

## Roadmap — not yet shipped

One spec is queued (`spec: pending`, `state: ready`, awaiting its
spec-pipeline approval gate) that would extend this file. It is not shipped;
nothing below exists in `forge.md` today.

- **`fg-a10902` — provider profiles.** A `## Providers` config surface for
  model-agnostic workers and cross-model judging via external CLIs
  (Codex/Gemini/Grok…), gated by explicit per-repo opt-in and a per-provider
  trust confirmation, with an overlay-profile model (immutable stock +
  presets, user-owned custom profiles storing only deltas so plugin updates
  never clobber a customization). The kernel/orchestrator itself stays
  Claude-native — explicitly a non-goal, not deferred by oversight.

It has no line in the config template above yet — this section will move it
out of Roadmap only once a human approves its spec. (Its former
`blocked-by`, `fg-a10901` — wave scheduling & verification economics, build-
ahead pipelining, the panel-ceiling rules, and judge-yield telemetry — has
since shipped; see [Verification economics](verification-economics.md).)
