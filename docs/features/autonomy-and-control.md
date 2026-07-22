# Autonomy and control

Forge has one kernel flow, but it is not one fixed operating mode. Choose the
amount of autonomy that suits this repository and this moment: the same
route, dispatch, verification, and integration rules apply at every level.

## The autonomy dial

The dial is a per-repository choice, not a maturity ladder.

1. **Hands-on.** Invoke individual commands and approve each next step.
2. **Prompt-driven (default).** A natural-language request routes to the
   right skill when `natural-language-invocation` is on. Within that run, the
   kernel can chain route → dispatch → verify → integrate.
3. **Session-autonomous.** One approval such as “build it” can work a whole
   spec wave, including parallel-eligible workers.
4. **Standing autonomy.** With `continuous-loop: on` and a human-set
   schedule, scheduled runs can pull ready work without a new chat prompt;
   standing consent lets a started run continue to newly-ready waves.

There are only four initiation doors: **a command, a natural-language
request, a schedule, or standing consent through `continuous-loop`**. Forge
never self-initiates outside those doors. `continuous-loop` is consent to
continue pulling waves, not permission to ignore a stop condition.

[Open the autonomy-dial diagram source](../diagrams/autonomy-dial.mmd).

## What does not move

The dial changes who starts or continues work; it does not remove the safety
floor. `tier: full` work still needs the spec approval gate. Provider use
still requires the repo Feature, its per-provider toggle, TOFU trust, and
the applicable budget/checkpoint and pilot gates. Budget caps and checkpoints
still bind, sensitive-domain work keeps its in-harness Claude builder
carve-out, and the grouped-verification floor and marginal-gain stop rules
still apply. See [configuration and Features](../conventions/config-and-features.md),
[dispatch and routing](../conventions/dispatch-and-routing.md), and
[verification](../conventions/verification.md).

| Dial level | What still asks a human |
|---|---|
| Hands-on | Each requested action, plus every protected gate below. |
| Prompt-driven | The request starts the run; full-spec approval, provider trust, blocked disputes, and budget interruptions remain human decisions. |
| Session-autonomous | The wave may proceed after its approval; the same full-spec, provider, budget, and blocker gates remain. |
| Standing autonomy | The schedule and standing consent start/continue work; the same gates can stop it and surface a human decision. |

In particular, no setting bypasses full-tier spec approval, creates provider
trust, raises a human-set cap as a side effect, or turns sensitive-domain
building into an external-provider default. Pilot gates and the stop rules
remain floors, not preferences.

## Change the setting, not the guarantees

Use `/forge:settings` to view or edit Features, provider toggles, Budgets,
Queue settings, profiles, and routing overrides. Plain language works too:
“turn off auto loops” maps to `continuous-loop: off` when
`natural-language-invocation` is on. The settings command validates the
change against the shared settings registry and keeps its protected floors.
`workflow-executor` changes whether eligible parallel work uses the
deterministic executor or the equivalent sequential loop; `providers` remains
off until a repository explicitly enables it and clears its separate gates.

For a narrower choice, write a per-task routing override rather than changing
the repository default. A standard-tier plan can also opt into the otherwise
escalate-only consensus path with `consensus-loop: on`; this adds review only
when the first critique rejects a P0/P1 decision. See the
[configuration reference](configuration.md) and
[cross-model orchestration](cross-model-orchestration.md).

## Loop catalog

Every loop is bounded. A loop either reaches its explicit exit condition or
escalates; it does not run on elapsed time or open-ended model judgment.

| Loop | When it fires | Bound / exit |
|---|---|---|
| **Bounce-retry** | A verifier finding survives the filter at INTEGRATE. | At most 2 retries; then `blocked` with a double-bounce postmortem. [Defined in dispatch and routing.](../conventions/dispatch-and-routing.md) |
| **Watch loop** | A fix must re-run a failing gate. | Repeats until green, capped by attempts rather than time; cap-out escalates. [Defined in dispatch and routing.](../conventions/dispatch-and-routing.md) |
| **Loop-until-dry** | A human-invoked audit or bug-hunt sweep needs finder rounds. | Stop after 2 consecutive rounds with nothing new. [Defined in dispatch and routing.](../conventions/dispatch-and-routing.md) |
| **Plan consensus escalation** | The normal refuter critique has a P0/P1 rejection; full-tier plans and explicit `consensus-loop: on` plans are eligible. | Escalate-only: C1 plus at most one C2 (2 critiques total); unresolved decisions go to a human. [Defined in provider judges §10.](../../skills/kernel/references/provider-judges.md) |
| **Sequential cross-model review** | Claude-built full-tier or sensitive work uses the cross-model verifier slot. | One codex judgment and one Claude findings review: 2 lifetime passes; a remaining dispute escalates. [Defined in provider judges §11.](../../skills/kernel/references/provider-judges.md) |
| **Dualverify** | A human explicitly requests a blind, audit-shaped double sweep. | Command-only; it is never started by a wave or standing consent. [Defined in `/forge:dualverify`.](../../commands/dualverify.md) |
| **Audit fix waves** | A human asks for an audit, court, or bug-hunt follow-up. | Human-invoked only; shipped work never auto-chains a new audit sweep. [Defined in verification.](../conventions/verification.md) |

[Open the iteration-loops catalog diagram source](../diagrams/iteration-loops-catalog.mmd).
