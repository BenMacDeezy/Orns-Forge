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
