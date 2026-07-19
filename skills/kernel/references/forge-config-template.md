# Forge config

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

## Budgets
<!-- max-tasks-per-session is the PRIMARY enforced cap: the kernel counts
     dispatches per session and stops with a session report when reached.
     session-token-cap is advisory only — the model may stop early on its own
     spend estimate; it is not the enforcement mechanism. -->
- max-tasks-per-session: none
- session-token-cap: none

## Queue
- claim-staleness-hours: 0.5
- max-parallel-tasks: 3

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
