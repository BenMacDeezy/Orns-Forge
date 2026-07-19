---
name: ship
description: The Forge full-tier "done" protocol — gates green, verifier verdict, constitution check, reviewer pass, security when the diff warrants, and the regression-test rule. Use at kernel VERIFY for tier:full tasks before INTEGRATE commits. Bounce/blocked semantics match the kernel.
---

# Forge ship protocol (full tier)

A `tier: full` task is "done" only when EVERY gate below is green. The kernel
invokes this skill at VERIFY for full-tier work; it never commits (INTEGRATE
does) and never edits source (agents do). Its output is a single SHIP verdict
the kernel acts on.

## Preconditions (else the task is already blocked at GATE)
- `tier: full` with a non-null `spec:` pointing to an `approved` spec.
- The worker has reported completed, with its gate output.

**Ship overlap.** On the builder's return, this protocol's judges dispatch
in parallel with the `forge-verifier`/`forge-ui-verifier` spawn, not after
it — see `forge:kernel` VERIFY, "Ship overlap — parallel fan-out," and
`docs/conventions.md`, "Latency rules — ship-review overlap, mechanical
bounces, batch gates, sliding-window dispatch," for the full rule. The done
bar below is unaffected: every check still gates INTEGRATE identically.

## The checklist — all must pass

1. **Gates green.** build + test + lint/typecheck run by the verifier, output
   captured in the Attempt log. Any red gate → FAIL.
2. **Verifier verdict PASS.** `forge-verifier` (≥ tier of the work) confirms
   each EARS clause with evidence, attacks the change, sweeps silent failures.
   **Full-tier UI/motion tasks:** the verifier slot here is the visual gate —
   `forge-ui-verifier` runs instead of (or, for mixed code+visual criteria,
   alongside) `forge-verifier`, per `forge:kernel` VERIFY's visual gate
   routing rule; a mixed task needs both verdicts PASS.
3. **Constitution check.** When `.forge/constitution.md` exists, the verifier's
   CONSTITUTION block reports every numbered rule yes/no with evidence. Any
   `no` → FAIL.
4. **Reviewer pass.** Spawn `forge-reviewer` (opus/high) on the diff. Read its
   `COUNTS: <N critical, M important>` output-contract field; any Critical or
   Important finding → FAIL (bounce with the findings).
5. **Security pass (named trigger).** If the kernel NAMES a trigger in the
   dispatch note — new cookie/storage write, raw-HTML/dangerouslySetInnerHTML,
   auth/token/secret touch, form/redirect handling, parsing untrusted input,
   new dependency, money/payment (`docs/conventions.md`, "Verification
   economics — 2026-07-18") — spawn `forge-security` (opus/high). Read its
   `COUNTS: <N critical, M important>` output-contract field; any Critical or
   Important finding → FAIL. No named trigger → SECURITY is
   `n/a — no named trigger`.
6. **Legal pass (conditional).** If the diff adds or bumps a dependency,
   vendors third-party code, or integrates a new external service/API, spawn
   `forge-legal` (sonnet/medium). Read its `VERDICT:` output-contract field;
   `BLOCK-RECOMMENDED` → FAIL (bounce with the RED findings — a human decides
   whether to accept the risk, swap the dependency, or drop it);
   `OBLIGATIONS` → PASS, but the attribution/NOTICE entries it lists must land
   in the same diff before INTEGRATE commits. Otherwise LEGAL is `n/a` with
   the reason.
7. **Regression protection.** Read the verifier's `REGRESSION: <test present |
   n/a (not a bug fix)>` output-contract field. If the task is a bug fix and
   REGRESSION is not `test present` → FAIL.

## Bounce / blocked (same as kernel)
Any FAIL returns to the kernel's INTEGRATE, which re-dispatches the SAME worker
contract plus the findings (max 2 retries), then sets `state: blocked` with a
plain-English report. `/forge:status` surfaces blocked tasks first.

REVIEW/SECURITY/LEGAL findings pass through the finding filter before a FAIL becomes a bounce — `docs/conventions.md`, "Ship-judge widening + Critical-security exploit bar — 2026-07-18".

## Output contract (return to the kernel)

```
SHIP: PASS | FAIL
GATES: <command → pass/fail>
VERIFIER: PASS | FAIL
CONSTITUTION: <rule N → yes/no — evidence, one per line, or "no constitution">
REVIEW: PASS | CHANGES REQUESTED — <reviewer's COUNTS field: N critical, M important>
SECURITY: PASS | CHANGES REQUESTED | n/a — <surface touched, or why n/a; if run, security's COUNTS field: N critical, M important>
LEGAL: CLEAR | OBLIGATIONS | BLOCK-RECOMMENDED | n/a — <what triggered it, or why n/a; if OBLIGATIONS, confirm the NOTICE/attribution entries are in the diff>
REGRESSION: <verifier's REGRESSION field: test present | n/a (not a bug fix)>
FAIL NOTES: <what must change, or omit>
```

Any single FAIL line = `SHIP: FAIL`.
