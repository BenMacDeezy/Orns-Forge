---
name: ears-acceptance-verification
description: Verify a diff against its EARS acceptance criteria with evidence rather than impression — a criterion-by-criterion evidence table, adversarial re-derivation, gate-vs-criteria passes, constitution check, and a PASS/bounce verdict. Use when verifying a task's diff, checking whether work meets its acceptance criteria, or deciding PASS vs bounce. Backs the forge-verifier agent.
---

# EARS acceptance verification

Verification is an adversarial evidence exercise, not a read-through. The
verifier judges one task's diff against its EARS criteria and returns a verdict;
it **never edits code** — a failing criterion bounces back to the author.

## 1. Criterion-by-criterion evidence table

Build a table with one row per EARS acceptance criterion. Nothing is left
unchecked; "looks fine" is not evidence.

| Criterion (EARS clause) | Evidence | Verdict |
|---|---|---|
| WHEN … THE SYSTEM SHALL … | test name / command output / observed behavior | met / unmet |

Evidence is one of: a named test that exercises the clause and passes, captured
command output, or a concrete observation from running the code. A criterion
with no evidence column is treated as **unmet** — absence of proof is not proof.

## 2. Adversarial re-derivation — don't just re-run the author's tests

For each criterion, construct at least one scenario the clause *implies* that
the diff might NOT handle, then check it:

- boundary/empty/zero cases the happy-path test skipped,
- the unwanted-behavior branch (`IF <condition>, THEN …`) when the criterion
  has one — verify the error path fires, not just the success path,
- concurrent/repeated invocation, malformed input, the state the criterion
  names being false.

Re-running the author's own green tests confirms only what they already
thought to test. Derive the missing scenario yourself and exercise it.

## 3. Gate pass and criteria pass are two distinct passes

A green CI gate (build/test/lint) is **necessary but not sufficient**:

- **Gate pass:** the project's gates run clean on the diff.
- **Criteria pass:** every EARS clause has met evidence (steps 1–2).

Both must hold. Green gates with an unmet criterion is a **bounce** — the tests
simply don't cover the requirement. Passing criteria with a red gate is also a
bounce. Never collapse the two into one check.

## 4. Constitution / invariant check

When `.forge/constitution.md` exists, evaluate each numbered rule against the
diff and return a yes/no with concrete evidence per rule (e.g. "rule 1: bug fix
ships a test that fails without the fix — yes, `test_x` fails on revert"). Any
rule returning **no** fails the task regardless of criteria status. Cite rules
by their stable number.

## 5. Verdict discipline

- **`VERDICT: PASS`** — every criterion has met evidence, both passes are green,
  and every constitution rule returns yes. State it plainly.
- **`VERDICT: FAIL`** — name the *specific* unmet criterion (or failed gate /
  failed rule number) and the evidence gap, so the author knows exactly what to
  fix. Do not use "bounce" — that is what the kernel does AFTER a FAIL verdict,
  not the verdict value itself. The verdict names the specific criterion that
  failed.

The verifier **never patches** the code to make a criterion pass — that
collapses the check into the thing it checks. It judges and hands the FAIL
back; the author's agent fixes.

## Sources

- Forge conventions: `docs/conventions.md` (EARS acceptance criteria checkable
  by a verifier; `constitution.md` rules evaluated at VERIFY).
- Forge `ship` skill (`skills/ship/SKILL.md`) and `forge-verifier` agent —
  verifier judges, never edits; PASS/bounce verdict discipline; constitution
  yes/no with evidence.
- EARS: Mavin et al., "Easy Approach to Requirements Syntax", IEEE
  International Requirements Engineering Conference (RE), 2009.
