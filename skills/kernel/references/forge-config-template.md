# Forge config

## Operator profile
<!-- Active autonomy preset pointer. `stock:<name>` or `custom:<name>`
     (docs/conventions.md, "Operator-profile container format"). A
     forge.md with no Operator profile section behaves as if this pointer
     named the default stock profile for this install — `stock:guided` for
     a fresh install (no prior `.forge/` state before this section
     existed), `stock:full-auto` for an existing install (maps current
     behavior forward unchanged) — rendered `(default — not yet in
     forge.md)`, same missing-toggle-means-default convention as Features
     below. Precedence + pause-point/floor rules:
     skills/kernel/references/profile-wiring.md, NORMATIVE. -->
- active: (default — not yet in forge.md)

## Routing overrides
<!-- "<area or path pattern>: <model>/<effort> — <reason>" one per line.
     Models: haiku | sonnet | opus. A `fable/<effort>` line is also valid
     here — writing one IS the human authorization the kernel needs to use
     fable for that area (extremely deep reasoning only; very expensive;
     the router never picks fable on its own). -->
(none)

## Features
<!-- Behavior toggles. `on`/`off`. Defaults below; docs/conventions.md
     ("Features (forge.md)") is the reference. A forge.md with no Features
     section behaves as if every toggle were at its default here. -->
- natural-language-invocation: on   # Forge skills fire from plain conversation; off = command-only
- continuous-loop: on               # completing a task auto-pulls the next wave; off = one explicit run per invocation
- auto-queue-capture: on            # task-shaped ideas in conversation are offered for capture into the queue
- express-lane: on                  # standard-tier ideas skip the spec pipeline via one structured confirm
- workflow-executor: on             # waves + full-tier reviews run as deterministic Workflow scripts when the harness offers the Workflow tool
- providers: off                    # OFF by default; on unlocks per-provider enablement, each still gated by its own once-per-provider-per-repo-per-machine trust confirm

## Budgets
<!-- max-tasks-per-session is the PRIMARY enforced cap: the kernel counts
     dispatches per session and stops with a session report when reached.
     session-token-cap is advisory only — not the enforcement mechanism. With
     continuous-loop: on, a spend estimate (or elapsed time / session length) is
     never a reason to voluntarily pause the drain; only a hard cap stops it.
     max-provider-dispatches-per-session counts external-provider dispatches
     only (ALL providers combined), checked at ROUTE time; never folded into
     session-token-cap. Shipped default is the CHECKPOINT MODEL
     (owner-ratified 2026-07-22, docs/conventions/config-and-features.md,
     "Provider dispatch checkpoints"): no hard ceiling; every
     provider-dispatch-checkpoint-every dispatches the kernel posts a
     one-line tally checkpoint (per-provider counts, exact model slugs) and
     continues unless the human objects. Set a NUMBER instead of none to
     get the original hard-cap semantics — a session at a numeric cap
     dispatches no further external work and states so. -->
- max-tasks-per-session: none
- session-token-cap: none
- max-provider-dispatches-per-session: none
- provider-dispatch-checkpoint-every: 10

## Providers
<!-- Per-provider on/off toggle, layered UNDER the global `providers`
     Feature toggle above (docs/conventions/config-and-features.md,
     "Per-provider dispatch toggles"). A provider dispatches only when ALL
     FOUR hold: the `providers` Feature is on, this provider's own toggle
     below is on, its TOFU trust marker
     (.forge/.trust-providers/<provider-id>.local) is present, and the
     dispatch cap has headroom. MISSING TOGGLE = OFF — the one place in
     forge.md where a missing key does NOT mean its listed default here;
     it mirrors the `providers` Feature's own default-off posture instead.
     Toggling a provider off never clears its TOFU trust marker. Pilot-
     gated providers (grok, antigravity) stay undispatchable regardless of
     this toggle until a human clears their pilot gate. -->
- codex: off
- grok: off
- antigravity: off

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
