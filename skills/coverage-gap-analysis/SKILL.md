---
name: coverage-gap-analysis
description: Systematically find untested branches, edge cases, and unasserted behavior in EXISTING code — complements test-driven-development, which governs new code written test-first. Use when asked to "improve coverage" or "find untested edge cases", or when a coverage report shows lines executed but the assertions look weak. Triggers — "increase test coverage", "what's not tested", "coverage gaps", "untested branches", "legacy code has no tests", "characterization tests", "is this well tested".
---

# Coverage gap analysis

`superpowers:test-driven-development` governs writing new code test-first.
This skill is for the opposite direction: code already exists, has weak or
no tests, and you need to find what's actually untested before touching it.
Order matters — inventory (§1) before characterize (§4) before any new
assertions, and never let "coverage went up" substitute for "the risk went
down" (§3).

## 1. Branch/path inventory — before writing a single test

Read the target code and enumerate, in a list, every point where behavior
forks:

- **Conditionals**: every `if`/`else`/`switch`/ternary branch, including the
  implicit "else does nothing" branch nobody wrote.
- **Loops**: zero iterations, one iteration, many, early-exit (`break`/
  `return` inside the loop).
- **Error paths**: every `throw`/`catch`/`Result::Err`/error return, every
  place a caught exception is swallowed, logged-and-continued, or
  fell back silently.
- **Boundary values**: empty string/collection, null/undefined/None, zero,
  negative, max-length, off-by-one at any range check (`<` vs `<=`).
- **External-input validation**: what happens on malformed input at each
  parse/deserialize/validate call.

Turn this into a checklist of `<location> -> <branch>` pairs before writing
any test. A gap you didn't enumerate is a gap you won't test.

## 2. Mutation-testing mindset on EXISTING tests

For every test that already exists and claims to cover a piece of code, ask:
"what one-line bug could I introduce here that this test would still pass?"
Concretely:

- Flip a comparison operator (`<` to `<=`, `==` to `!=`) — does any test fail?
- Change a boundary constant by one — does any test fail?
- Delete a line that mutates state, or skip a branch entirely — does any
  test fail?
- Swap a returned value for a plausible-but-wrong one (empty list vs null,
  0 vs -1) — does any test fail?

If you can name a mutation that survives, that's a real gap even though the
line is "covered" — write the test that kills that mutant. Don't
exhaustively run a mutation-testing tool unless one is already in the
project's toolchain; the mindset is the deliverable, applied by inspection
to the highest-risk branches from §1.

## 3. Coverage-metric skepticism

Line/branch coverage percentages measure *execution*, not *verification*.
Treat a high coverage number as a lead to investigate, not a result to
trust. Specifically flag:

- **Executed-but-not-asserted**: a test calls the code path but the
  assertion only checks "no exception was thrown" or checks an unrelated
  return value — the actual behavior of that branch is unverified.
- **Assertion-free integration smoke tests** masquerading as coverage of
  the units they pass through.
- **Coverage of the happy path only**, with the error/edge branches from
  §1 pulled in by the same test run incidentally (e.g. a catch block that
  executes during teardown) without ever being the thing under test.

When you find these, they count as gaps in §1's inventory even though the
coverage tool marks the line green.

## 4. Characterization tests first, when repairing legacy gaps

If the plan is to change behavior (refactor, bug fix, dependency bump) in
code that has these gaps, pin CURRENT behavior before changing anything —
even behavior you suspect is wrong:

1. Write tests that assert what the code *actually does today*, including
   any suspected bugs — these are characterization tests (Feathers), not
   correctness tests.
2. Get them green against the untouched code.
3. Only then make the intended change, using the characterization tests as
   a change-detector.
4. If a characterization test encodes a real bug, don't silently fix it
   inside this pass — flag it (or fix it as its own explicit, separately
   reviewed change) so "pin current behavior" and "fix the bug" aren't
   conflated into one unreviewable diff.

## 5. Test-pyramid discipline when placing new tests

Default every gap from §1–§3 to the **lowest** level that can exercise it:

- Pure logic, single-function branches, boundary values → unit test.
- Only push to integration level if the risk is genuinely at a boundary
  (two modules' contracts, a DB query's actual behavior, a serialization
  round-trip) that a unit test with mocks would fake past.
- Reserve e2e/system tests for the critical path only — never as the
  vehicle for closing a branch-coverage gap that a unit test could close
  faster and more precisely.

If you're tempted to write an integration or e2e test to cover a branch,
ask whether a unit test at the function boundary would catch the same
mutation from §2. If yes, write the unit test instead.

## Sources
- Mutation testing — general test-engineering practice for scoring test-suite strength by surviving/killed mutants.
- Feathers, M., *Working Effectively with Legacy Code* — characterization tests for pinning behavior before modifying untested code.
