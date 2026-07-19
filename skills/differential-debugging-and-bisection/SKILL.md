---
name: differential-debugging-and-bisection
description: Techniques for regressions, flaky failures, and heisenbugs that superpowers:systematic-debugging doesn't cover — git bisect (including automated bisect run), delta debugging / input minimization, differential debugging across environments and data, and concurrency stress tactics. Triggers — "this used to work", "worked yesterday", "regression", "flaky test", "heisenbug", "only fails in CI", "only fails on prod", "can't reproduce locally", "shrink the repro", "minimal repro", "race condition".
---

# Differential debugging and bisection

`superpowers:systematic-debugging` covers the general hypothesis loop for a
bug you can already see and reproduce. This skill covers the gaps: bugs
defined by a *change over time* (regressions), a *change over space*
(works-here-fails-there), or a *change over runs* (nondeterminism). Load
this alongside systematic-debugging, not instead of it — use it to locate
the cause, then hand off to that skill's hypothesis loop to fix it.

## 1. Regression → git bisect first

If the bug is "this used to work," don't hypothesize from the current
diff — bisect finds the actual causal commit in O(log n).

1. Confirm you have a known-good ref and a known-bad ref (a tag, an old
   commit, `HEAD`).
2. `git bisect start`, `git bisect bad <bad-ref>`, `git bisect good <good-ref>`.
3. If the repro is scriptable (exit 0 = good, non-zero = bad, 125 = skip
   this commit — e.g. it doesn't build), automate it:
   `git bisect run <script>`. Writing that script IS the minimal-repro step
   (§3) — do it before bisecting, not after.
4. `git bisect view` / the final output names the first-bad commit.
   `git bisect log` captures the trail for the eventual root-cause writeup.
   Always `git bisect reset` when done, even on failure paths.
5. The first-bad commit is a strong causal hypothesis, not a proven root
   cause — read its diff, then verify with systematic-debugging's evidence
   loop rather than assuming the commit message explains the bug.

## 2. Differential debugging: diff the whole system, not just code

When a bug reproduces in one place and not another and the code is
identical, the cause is outside the diff you're staring at. Diff every
layer, in this order (cheapest first):

1. **Environment** — OS, runtime/interpreter version, installed package
   versions (`pip freeze` / `npm ls` / lockfile diff), env vars, locale,
   timezone, filesystem case-sensitivity.
2. **Config** — flags, feature toggles, config files, defaults that changed
   between versions.
3. **Data** — the actual input/state driving the two runs. Same code +
   different data is the single most underused explanation for
   "works on my machine." Dump both inputs and diff them byte-for-byte
   before trusting that they're "the same."

Treat each layer as a falsifiable hypothesis: state what you expect to
differ, diff it, record confirmed/killed. Don't stop at the first
difference found — confirm it's causal by reproducing with only that
difference flipped.

## 3. Minimal-repro construction (a checklist, not a side effect)

Before deep investigation, and always before `git bisect run`, shrink the
failing case:

- [ ] Can the failure be triggered from a single command / single test?
- [ ] Strip unrelated setup: delete config, fixtures, and code paths one at
      a time, re-running after each cut, keeping only what still fails.
- [ ] For a large failing *input* (file, payload, log, dataset), apply
      **delta debugging (ddmin)**: split it in half, test each half; if a
      half still fails, recurse into it; if neither half fails alone, test
      the complements (whole-minus-half) to catch failures caused by
      interaction between the two halves. Repeat until no further removal
      preserves the failure — this is the systematic, terminating version
      of manually commenting stuff out.
- [ ] Confirm the shrunk case fails with the exact same symptom (error
      text/stack) — ddmin over the wrong failure signature converges on
      the wrong minimal case.
- [ ] Save the minimal repro as the regression test's fixture.

## 4. Concurrency / heisenbugs

A bug that disappears when you add a log line, run under a debugger, or
run alone but not under load is not "flaky" — the timing sensitivity *is*
the diagnostic signal. Treat it as evidence of a race, not noise to average
away.

- **Stress-loop** the suspected path hundreds/thousands of times, under
  load, with injected delays (`sleep`/yield at suspicious points) to widen
  the race window instead of closing it.
- **Vary scheduling deliberately**: extra threads/workers, pool-size
  changes, CPU pinning, artificial contention — each is a hypothesis about
  *which* interleaving matters.
- Reach for **race/thread sanitizers** where the language has them (TSan,
  Go `-race`, ThreadSanitizer) before hand-rolling detection.
- Prefer **deterministic replay** over "reproduce and hope": record the
  failing run's schedule if tooling supports it, or log a causally-ordered
  per-thread trace so the interleaving can be reconstructed after the fact.
- A heisenbug fix isn't "confirmed" until it survives many more stress-loop
  iterations than the pre-fix version needed to fail — one clean run proves
  nothing for nondeterministic bugs.

## 5. Hypothesis + evidence template

Use this for every hypothesis regardless of which technique surfaced it —
this is what feeds forge-debugger's `HYPOTHESES` output field.

```
HYPOTHESIS [<category>]: <one sentence, falsifiable>
CATEGORY: Logic | Data | State | Integration | Resource | Environment
TEST: <what you ran/diffed/bisected to check it>
VERDICT: Confirmed | Falsified | Inconclusive (confidence: high/med/low)
EVIDENCE: <the actual output, diff, or bisect result — not a paraphrase>
CAUSAL CHAIN: <file:line -> file:line -> observed symptom, only if Confirmed>
```

Keep hypotheses one at a time even under bisect/ddmin — a ddmin run is the
TEST for a Data-category hypothesis; "bisect landed on commit X" is
TEST + EVIDENCE for a Logic/Integration hypothesis about that commit.

## Sources
- git-scm.com/docs/git-bisect
- Zeller, A. & Hildebrandt, R., "Simplifying and Isolating Failure-Inducing Input," IEEE Transactions on Software Engineering, 2002.
- Musuvathi, M. et al., "Finding and Reproducing Heisenbugs in Concurrent Programs," OSDI 2008.
