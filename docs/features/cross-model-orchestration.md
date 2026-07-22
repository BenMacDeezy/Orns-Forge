# Cross-model orchestration

Forge remains Claude-native at the kernel: it decides the loop, keeps the
record, and never treats a provider result as an automatic approval. When
external providers are enabled, they fill explicitly routed worker or judge
slots with a visible provider/model label. The dispatch label identifies the
standing-in persona, profile role, provider, exact model slug, and task name;
it is not a new provider-specific persona. Full label grammar lives in
[`docs/conventions/telemetry-and-labels.md`](../conventions/telemetry-and-labels.md).

## External-provider dispatch: gates before routing

A provider must clear four independent layers: the repo-wide Feature, its
own toggle, TOFU confirmation, and the budget/checkpoint decision. Pilot
providers add an independent pilot gate; a toggle never clears it. A blocked
route states the one gate that blocked it and degrades gracefully rather than
waiting silently. The provider gate contract is normative in
[`provider-judges.md`](../../skills/kernel/references/provider-judges.md).

[Open the provider gate and pilot flow source](../diagrams/provider-gates-and-pilot.mmd).

```mermaid
flowchart TD
    FEATURE{"Feature on?"} -->|yes| TOGGLE{"toggle on?"}
    FEATURE -->|no| FALLBACK["Claude route + stated note"]
    TOGGLE -->|yes| TOFU{"TOFU confirmed?"}
    TOGGLE -->|no| FALLBACK
    TOFU -->|yes| BUDGET{"budget allows?"}
    TOFU -->|no| FALLBACK
    BUDGET -->|yes| PILOT{"pilot clear?"}
    BUDGET -->|no| FALLBACK
    PILOT -->|yes / not needed| DISPATCH["provider dispatch"]
    PILOT -->|no| FALLBACK
```

`/forge:settings` is the sole editor for the Feature, per-provider toggles,
and Budget keys. Its complete view and validation share one settings-schema
registry, so a key is defined once rather than independently in the UI and
validator. See
[`docs/conventions/config-and-features.md`](../conventions/config-and-features.md).

For every provider worker dispatch, attached skills are materialized into
the dispatch worktree before its prompt; this required attachment step does
not depend on native skill discovery. The materialized scratch area is
excluded at integration. Optional native discovery registration is a
human-run additive surface, never a substitute for materialization.

## Routing and the sensitive-domain carve-out

Routing honors a human-written override first. Without one, sensitive work
and provider-gate machinery default to an in-harness Claude builder. The
carve-out binds only the builder role: cross-model judging and second
opinions remain available. Otherwise, passing gates permit the active
profile role and work shape to resolve the builder.

[Open the builder-routing precedence source](../diagrams/builder-routing-precedence.mmd).

```mermaid
flowchart TD
    OVERRIDE{"human override?"} -->|yes| ROUTE["use override"]
    OVERRIDE -->|no| CARVE{"sensitive domain?"}
    CARVE -->|yes| CLAUDE["Claude builder"]
    CARVE -->|no| GATES{"provider gates pass?"}
    GATES -->|no| CLAUDE
    GATES -->|yes| ROLE["profile role"] --> SHAPE["shape tie-break"] --> ROUTE
```

## Checkpoints, not an invisible default ceiling

The shipped default is a running tally with a checkpoint every ten provider
dispatches. At each checkpoint Forge reports the tally, per-provider counts,
and exact model slugs, then continues unless the human objects. A numeric
provider-dispatch cap remains a real hard stop; provider rate-limit errors
are surfaced verbatim.

[Open the checkpoint-budget source](../diagrams/provider-checkpoint-budget.mmd).

```mermaid
flowchart TD
    TALLY["tally dispatch"] --> NUMERIC{"numeric cap?"}
    NUMERIC -->|yes| CAP{"cap reached?"}
    CAP -->|yes| STOP["hard stop"]
    CAP -->|no| CONTINUE["dispatch"]
    NUMERIC -->|no| TENTH{"checkpoint multiple?"}
    TENTH -->|no| CONTINUE
    TENTH -->|yes| CHECKPOINT["one-line checkpoint"] --> OBJECT{"human objects?"}
    OBJECT -->|no| CONTINUE
    OBJECT -->|yes| STOP
```

## Consensus and sequential review

Plan consensus is escalate-only: one refuter critique is the normal first
look. A clean `C1` ends review. A P0/P1 rejection triggers one Claude
revision and exactly one `C2`; any remaining dispute goes to per-decision
human resolution before the separate approval gate. Cosmetic findings are
fixed inline and do not create another round.

[Open the plan-consensus source](../diagrams/plan-consensus-escalation.mmd).

```mermaid
flowchart TD
    PLAN["clarified plan"] --> C1["single refuter: C1"]
    C1 --> REJECT{"P0/P1 REJECT?"}
    REJECT -->|no| CONSENSUS["consensus"]
    REJECT -->|yes| REVISE["Claude revises"] --> C2["final critique: C2"]
    C2 --> SETTLED{"REJECT remains?"}
    SETTLED -->|no| CONSENSUS
    SETTLED -->|yes| CAPOUT["cap-out"] --> HUMAN["human resolution"]
    CONSENSUS --> APPROVAL["approval gate"]
    HUMAN --> APPROVAL
```

For a routed provider build, Claude remains the equal-or-higher verifier.
For Claude-built sensitive or full-tier work, codex takes the single verifier
slot and Claude reviews only the findings it raises; a dispute reaches a
human rather than silently favoring either model. Simultaneous dual
verification is an explicit command, not the default.

[Open the sequential cross-model review source](../diagrams/sequential-cross-model-review.mmd).

```mermaid
flowchart TD
    SENSITIVE{"sensitive domain?"} -->|yes| CLAUDE["Claude builds"]
    SENSITIVE -->|no| BUILDER["routed builder"]
    CLAUDE --> CODEX["codex verifier slot"]
    BUILDER --> CODEX
    CODEX --> FINDINGS{"findings?"}
    FINDINGS -->|no| INTEGRATE["integration gate"]
    FINDINGS -->|yes| CLAUDE_REVIEW["Claude reviews findings"]
    CLAUDE_REVIEW --> DISPUTED{"disputed?"}
    DISPUTED -->|no| INTEGRATE
    DISPUTED -->|yes| HUMAN["human resolution"] --> INTEGRATE
```

Grouped verification remains the floor: related ready tasks can share one
verifier dispatch, but each receives its own verdict. The first adversarial
look is never skipped. After the initial pass and one delta re-verify,
further unresolved judgment becomes a human blocker; P3/cosmetic findings
are fixed inline rather than spending another verifier dispatch. See
[`docs/conventions/verification.md`](../conventions/verification.md).
