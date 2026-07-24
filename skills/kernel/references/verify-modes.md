# Verify-mode detail (reference)

Loaded by `skills/kernel/SKILL.md` VERIFY, which is NORMATIVE
throughout: the first section below when the mode-2 verifier is being
considered for the reduced low-risk checklist, the second section when
mode 3 (finder / kernel-synthesis) is being chosen. Both sections are
moved verbatim from VERIFY, not summarized.

## Low-risk verify routing

**Low-risk verify routing.** Before spawning the mode-2 verifier, check
   the task against qualification rules in `docs/conventions.md`,
   "Low-risk verification (standard sub-class) — 2026-07" (docs/config-only
   diff, every EARS clause pin-covered, no touch on skills/, agents/,
   hooks/, workflows/, or `.forge/` protocol files, UI/animation tasks
   never qualify) — including that section's "NORMATIVE prose never
   qualifies" disqualifier: the kernel checks the CONTENT of the diff, not
   just its path, so a docs/-only edit to protocol, trust, consent, or
   verification-rule prose (including that section itself) never
   qualifies either. WHEN it qualifies, route the spawn to `forge-verifier` at
   haiku/low running that section's reduced checklist (gates green + every
   pin present-and-passing + one spot-checked EARS clause) instead of the
   full protocol, and record the classification in the Attempt log
   (`low-risk verify: qualified — <one-line reason>`). WHEN that verifier
   returns `VERDICT: ESCALATE`, re-dispatch full verification at the task's
   normal equal-or-higher tier — an ESCALATE is not a bounce and carries no
   penalty. After 4 consecutive low-risk verifications this session, route
   the 5th qualifying task to full verification (sampling audit),
   noting `sampling audit` in the Attempt log. This is still mode 2, not a
   new mode: it is still a separate verifier spawn judging a worker's own
   diff, so it does not contradict Hard Rule 3 ("the worker never verifies
   its own work") — only the routed tier and the checklist shrink, never
   the author/judge separation.

## Finder / kernel-synthesis (report tasks only)

**Finder / kernel-synthesis (report tasks only).** A standard-tier task
   whose sole deliverable is a findings report — read-only against the tree
   otherwise — may route to a "finder" instead of a worker+verifier pair;
   verification is the kernel's own synthesis of the finder's report, not a
   separate verifier spawn. Valid only under ALL of:
   (a) the Routing record declares it explicitly — `finder — verification:
   kernel synthesis` — never silently substituted for mode 2;
   (b) every finding is re-checked against the CURRENT tree state before any
   fix task is queued from it (a finder's findings can go stale by synthesis
   time, especially under a concurrent writer; see craft memory
   `mem-b82d19`);
   (c) never applicable to a task that modifies files beyond its own
   report — the moment a task's deliverable includes code, config, or
   `.forge/` changes, it takes mode 2 above instead.
   The finder route now mints via the fast path before dispatch, never
   raw generic (`docs/conventions.md`, "Report tasks (finder pattern),"
   NORMATIVE); `forge-worker`'s no-open-ended-exploration rule is not
   implicated.

## Blast-radius gate (mode-1 widening) — 2026-07-23 (owner-directed)

**Blast-radius gate.** Tier alone no longer decides whether a task earns a
   verifier spawn. Mode 1 (gates-inline, no separate verifier) applies to
   `tier: trivial` as before, AND to any `tier: standard` task whose diff
   passes ALL FIVE of the tests below. `tier: full` NEVER qualifies — spec-
   approved work always ships through `forge:ship`, unchanged.
   (a) **Gate-covered.** Every EARS acceptance clause is discharged by a
   gate command that actually runs and actually fails when the behavior is
   wrong — a passing test, type-check, lint, or pin that names the clause.
   A clause whose only evidence is "the code reads correctly" is NOT
   gate-covered and disqualifies the task on its own.
   (b) **No new behavior or contract.** The diff changes no public API
   signature, no data shape, no persisted schema, no config key's meaning,
   and no cross-module contract. Refactors, mechanical sweeps, additive
   internal helpers, and test-only changes pass; a new endpoint, a new
   field, or a changed return type does not.
   (c) **No sensitive surface.** Nothing security-, auth-, session-,
   secret-, money-, payment-, PII-, migration-, or deletion-adjacent, and
   nothing under `skills/`, `agents/`, `hooks/`, `workflows/`, or `.forge/`
   protocol files. Same disqualifier list the low-risk routing above uses,
   plus the money/data-loss surfaces, because those are the classes where a
   silent miss cannot be walked back by `git revert`.
   (d) **Not visual.** UI, animation, and mobile-render tasks never qualify
   — rendered output cannot be judged by a gate command, which is the whole
   reason `forge-ui-verifier` exists.
   (e) **First attempt.** A task that has already bounced once takes full
   verification on its retry, no exceptions. A bounce is direct evidence
   that this task's blast radius was misjudged.

   **The kernel runs the gates, never the worker.** Mode 1 is the kernel
   executing the gate commands itself against the returned diff and pasting
   the output into the Attempt log. It does not delegate that back to the
   agent that wrote the code, so Hard Rule 3 ("the worker never verifies its
   own work") holds exactly as it does for trivial tier today. What is
   removed is a second MODEL's opinion, not the objective check.

   **Record it.** Write `blast-radius: clear — <one-line reason>` in the
   Attempt log, naming which gate discharges which clause. WHEN any of the
   five tests is uncertain rather than clearly true, the task does NOT
   qualify — the gate is a whitelist, and "probably fine" is a mode-2
   answer. Record `blast-radius: verifier — <which test failed>` in that
   case, so the decision is auditable either way.

   **Sampling audit.** After 6 consecutive blast-radius-clear completions
   this session, route the 7th qualifying task to full verification anyway
   and note `sampling audit` in the Attempt log. This is the only defense
   against the gate slowly drifting into "everything qualifies," and it
   costs one verifier per seven tasks.
