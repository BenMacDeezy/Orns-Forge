# Inquest tribunal

Canonical protocol: [`skills/inquest/SKILL.md`](../../skills/inquest/SKILL.md)
(gating, charter, role contracts, routing tiers). Cross-cutting boundary and
verdict vocabulary: [`docs/conventions.md`](../conventions.md), "Inquest
tribunal — 2026-07".

`/forge:inquest` is the adversarial deep-debug tribunal that hunts bugs
**already in the tree and unknown** — nobody has filed them, nobody has
reproduced them, the code has simply never been adversarially attacked. It
is a three-role protocol, deliberately split across three spawns so
maximalism and skepticism both run at full strength instead of collapsing
into whichever instinct one agent happens to lean toward.

## Gating — human ask or accepted card only

Inquest **never loop-initiated**. No kernel loop, wave, or standing-consent
toggle (including `continuous-loop: on`) ever starts a tribunal on its own
— a human typing `/forge:inquest` (or an equivalent NL ask) this turn, or a
structured recommendation card the human explicitly accepted, is the only
valid trigger. A charter (scope, budget, stop conditions) is stated before
the first FINDER spawns, same discipline as every kernel run charter.

## The three roles

None of the three ever edits source, `.forge/`, or any file — inquest is
read-only end to end.

- **FINDER (maximalist).** Proposes every plausible defect it can support
  with a concrete scenario, inside its declared scope — coverage, not
  caution. Each finding: Location, Claim (falsifiable), a concrete failure
  scenario (not "this looks fragile" — "call X with an empty list while Y
  is mid-flight"), and Severity (Critical/Important/Minor, the same
  vocabulary `forge-reviewer`/`forge-security` use).
- **REFUTER (motivated skeptic).** Receives ONE finding at a time and tries
  to kill it. Running code beats argument: a reproduction or a failed
  reproduction always outranks prose reasoning either way. Verdict, exactly
  one of `REFUTED` (disproved, with evidence), `CONFIRMED` (the refutation
  attempt itself reproduced the bug), or `UNRESOLVED` (neither disproof nor
  reproduction was achievable).
- **JUDGE (decides, never re-investigates).** Weighs every finding against
  its REFUTER verdict and evidence — never re-runs a scenario, never asks
  for more, never forms its own independent read. In the common case this
  ratifies the REFUTER's verdict; a REFUTED verdict backed only by
  unexecuted prose is weak evidence, and the JUDGE may downgrade it to
  UNRESOLVED rather than treat thin reasoning as settled.

A large scope MAY split the FINDER into parallel lenses (correctness,
security, performance, lifecycle, …), each its own sonnet/high spawn — but
the REFUTER and JUDGE structure stays fixed: every finding from every lens
still gets its own independent REFUTER pass, and there is still exactly one
JUDGE synthesizing across the whole combined set, never one JUDGE per lens.

## Routing tiers

| Role | Tier | Why |
|---|---|---|
| FINDER | sonnet/high | coverage over depth per lens |
| REFUTER | equal-or-higher than the FINDER it's attacking | a weaker refutation can't be trusted to kill a claim |
| JUDGE | opus/high | the highest-leverage read in the protocol — a wrong routing decision either buries a real bug or wastes a full triage+fix cycle on a phantom |

## Judge routing table

| Verdict | Action |
|---|---|
| `CONFIRMED` | Routes through `forge:triage` as a normal ready queue-task draft — repro steps + expected/actual. Constitution rule 1 (every bug fix ships a regression test) applies to the resulting task; the FINDER's severity carries forward. |
| `DISMISSED` | Recorded with the REFUTER's reason — never silently dropped, never re-attempted within the same pass. |
| `UNRESOLVED` | Surfaced directly to the human — not queued, not dismissed, a human call. |

Every finding that enters a tribunal pass exits through exactly one of
these three rows; a fourth outcome would be a protocol bug in the run, not
a valid state.

## Boundary — three adjacent patterns, none of which substitute for it

- **vs. `forge-debugger` (Hex).** Hex fixes ONE already-known bug (a filed
  task, a failing test, a reproduced report) via hypothesis → evidence →
  fix. Inquest hunts for bugs nobody has found yet and never fixes anything
  itself; a CONFIRMED finding reaches Hex (or `forge-worker`) only after it
  exits through `forge:triage`.
- **vs. the finder pattern in report tasks.** A report-task finder is a
  single read-only pass handed straight to kernel synthesis — no
  adversarial defense step. Inquest's FINDER is deliberately maximalist
  precisely *because* a REFUTER and a JUDGE stand between its claims and
  any queue task.
- **vs. the verifier-finding filter.** That filter gates changes already
  headed into the tree, spot-checking a verifier's FAIL findings before a
  bounce. Inquest hunts bugs already IN the tree, with no pending diff and
  no verifier verdict to filter — family resemblance, different lifecycle
  point.
