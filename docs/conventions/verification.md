# Verification

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## Low-risk verification (standard sub-class) — 2026-07

Response to fg-9e0201. VERIFY mode 2 (`forge:kernel`, "VERIFY") normally
spawns `forge-verifier` at equal-or-higher model tier than the work it
checks, running the full adversarial protocol. This section defines a
**reduced-protocol sub-class of mode 2** — not a fourth mode, not a
skipped verifier spawn — for the narrow slice of standard-tier work where
a full adversarial pass is disproportionate to the actual risk: a docs/
config-only change with every acceptance clause already pinned by a
passing test. The verifier spawn still happens; only its tier and
checklist shrink, and only when every qualification rule below holds.

**Qualification (ALL must hold — the kernel decides, never the worker).**
A standard-tier task qualifies for low-risk verification only if every one
of the following is true:

- The diff is **docs/config-only, zero runtime-behavior change** — no
  executable code path is added, removed, or altered.
- **Every EARS clause is covered by a passing pin or regression test** —
  no clause relies on prose-reading alone for its evidence.
- The task **touches NONE of `skills/`, `agents/`, `hooks/`, `workflows/`,
  or `.forge/` protocol files** — these are explicitly disqualified
  regardless of how small the diff looks.
- **NORMATIVE prose never qualifies, regardless of path.** A path outside
  the disqualified list above is necessary but not sufficient: any edit to
  text that *states a rule the system must follow* is full-verification
  work even when the diff sits entirely under `docs/`. This covers
  `docs/conventions.md` itself, the Trust boundary section, the
  verification-mode rules, this Low-risk verification section itself,
  protocol referenced from `forge.md`, and any design doc's binding
  sections. The self-referential case is explicit, not an edge case: a
  task editing this Low-risk verification section always gets full
  verification, precisely because loosening this rule is the
  highest-leverage way to defeat it. When in doubt whether prose is
  normative — does it state a rule an agent or the kernel must follow? —
  answer yes, and route to full verification. Only non-normative
  documentation (README files, code comments, non-normative reference
  data) qualifies under the affirmative side of this rule, subject to the
  other qualification rules above.
- **UI/animation tasks never qualify as low-risk verification** — rendered
  output is behavioral by definition, so it can never satisfy "zero
  runtime-behavior change," and any such task keeps its full-tier judge
  (`forge-ui-verifier`, never this reduced path), regardless of how small
  the visual diff looks.

Any task failing even one of these stays on full mode-2 verification —
qualification is conjunctive, not a scoring heuristic.

**Reduced protocol.** WHEN a task qualifies, the kernel MAY route its
verification spawn to `forge-verifier` at **haiku/low**, running a
reduced checklist in place of the full adversarial protocol: gates green
+ every pin present and passing + ONE EARS clause spot-checked
adversarially (chosen by the verifier, not pre-selected by the kernel).
This is still a real verifier spawn — Hard Rule 3 ("the worker never
verifies its own work") is unchanged; only the tier and the checklist
shrink, never the separation between author and judge.

**ESCALATE semantics.** WHEN a low-risk verifier finds anything
behavioral, unpinned, protocol-adjacent, or otherwise doubtful, it returns
`VERDICT: ESCALATE` — not PASS, not FAIL — and the kernel re-dispatches
full verification at the task's normal equal-or-higher tier. Escalation is
**mandatory on doubt**: when uncertain, ESCALATE. An ESCALATE is not a
bounce and is never counted against the bounce-retry cap (`forge:kernel`
INTEGRATE, "FAIL") — it carries no penalty for the task or the worker; it
simply means the reduced protocol wasn't the right instrument and the full
one runs instead.

**Sampling audit.** After a session has run **4 consecutive low-risk
verifications**, the **5th qualifying task runs full verification
anyway**, regardless of how clean the reduced-protocol case looks — the
Attempt log records `sampling audit` as the reason. This resets the
consecutive count; the 6th through 9th qualifying tasks may again route
low-risk, with the 10th sampled, and so on.

**Classification is kernel-owned, not the worker's claim.** The
qualification decision above is made by the kernel at VERIFY, from the
diff and the task file — never asserted by the worker's own report. The
kernel records the classification in the task's Attempt log as `low-risk
verify: qualified — <one-line reason>` (or, when the sampling audit fires
instead, `sampling audit`) so the routing decision is auditable after the
fact, same discipline as every other Routing-record/Attempt-log
requirement in this file.

## Verifier-finding filter (bounce pre-check) — 2026-07

> Amended by: "Ship-judge widening + Critical-security exploit bar — 2026-07-18"

Response to fg-a10201 (Dex steal-list item —
`docs/audits/2026-07-18-scout-orchestration-landscape.md`: "false-positive-
filtering pass on verifier findings before bouncing"). This extends craft
memory `mem-b82d19` — the same re-check discipline `forge:kernel`'s finder
pattern already applies to a finder's findings before a fix task is queued
(`docs/conventions.md`, "Report tasks (finder pattern)," (b) Stale-finding
re-check, above) — to a verifier's FAIL verdict before a bounce is
dispatched.

**The filter.** WHEN a verifier (`forge-verifier` or `forge-ui-verifier`)
returns FAIL, before choosing a bounce route the kernel spot-checks EACH
finding in FAIL NOTES against the current tree: the cited file/location
must exist, and the claimed defect must reproduce on direct inspection —
read the file, and run the failing command if one is cited. This filter
runs strictly BEFORE the MECHANICAL/JUDGMENT bounce-routing decision
("Latency rules — ship-review overlap, mechanical bounces, batch gates,
sliding-window dispatch," "2. Mechanical-tagged bounces," above) — routing
only ever applies to findings that already survived the filter; filter
first, then route what survives.

**Per-finding outcomes.**
- **SURVIVES** — the cited location exists and the defect reproduces; the
  finding goes into the bounce contract.
- **CHALLENGED** — the finding is ambiguous rather than clearly wrong: the
  kernel sends ONE clarification exchange back to the verifier (a focused
  re-ask scoped to that specific finding), never a new full verification
  pass.
- **FILTERED** — the defect does not reproduce; recorded in the Attempt log
  with the reason. A filtered finding is never silently dropped.

**Bounce scope.** A bounce dispatches only for surviving findings, quoted
verbatim in the redispatch contract — the same quote-verbatim discipline
craft memory `mem-7c41ae` already established for dispatch briefs and
acceptance criteria.

**PASS-after-filter.** WHEN every finding in a FAIL verdict filters, the
verdict becomes PASS-after-filter: no bounce dispatches, and the full
filter rationale (each finding, its outcome, and why) is recorded in the
Attempt log — never silently. The kernel notes the PASS-after-filter
outcome in the session report. **Telemetry honesty:** a verifier whose
findings all filtered is still counted by `tools/telemetry.py` as a FAIL
verdict either way — the filter changes what the kernel does next, never
what the verifier said, so stats stay honest about verifier behavior
instead of laundering a FAIL into an invisible PASS.

This is the same re-check discipline `mem-b82d19` already established
(parallel finders racing a concurrent writer produce findings that can be
stale by the time anyone acts on them — re-check against current state
before acting), named here as the same discipline applied to verifier
verdicts instead of finder reports.

## Inquest tribunal — 2026-07

Response to fg-a10204. `/forge:inquest` (`skills/inquest/SKILL.md`) is the
adversarial deep-debug tribunal that hunts bugs already in the tree and
unknown — FINDER (maximalist) → REFUTER (motivated skeptic, per-finding) →
JUDGE (weighs and routes), never loop-initiated. The full protocol —
gating, charter, role contracts, routing tiers, proportionality — lives
canonically in the skill file; this section is the cross-cutting boundary
statement and the NORMATIVE verdict vocabulary other parts of the system
(telemetry, kernel dispatch, future tooling) cite rather than re-derive.

**Boundary.** Inquest occupies a distinct slot from three adjacent
patterns, and none of the three substitutes for it:

- **vs. `forge-debugger`** — `forge-debugger` fixes ONE already-known bug
  (a filed task, a failing test, a reproduced report) via hypothesis →
  evidence → fix. Inquest hunts for bugs nobody has found yet and never
  fixes anything itself; a CONFIRMED finding reaches `forge-debugger` (or
  `forge-worker`) only after it exits through `forge:triage`.
- **vs. the finder pattern in report tasks** (above, "Report tasks (finder
  pattern)") — a report-task finder is a single read-only pass with no
  adversarial defense step, handed straight to kernel synthesis. Inquest's
  FINDER is deliberately maximalist precisely because a REFUTER and a JUDGE
  stand between its claims and any queue task — the two patterns are not
  interchangeable, and neither may be substituted for the other and still
  called by the other's name.
- **vs. the verifier-finding filter** (above, "Verifier-finding filter
  (bounce pre-check) — 2026-07") — that filter gates CHANGES already headed
  into the tree, spot-checking a verifier's FAIL findings before a bounce.
  Inquest hunts bugs already IN the tree, with no pending diff and no
  verifier verdict to filter. Family resemblance (both attack a claimed
  defect before acting on it), different lifecycle point (pre-bounce vs.
  pre-triage-draft).

**Verdict vocabulary — NORMATIVE.** The exact words below are load-bearing:
a future rewrite of `skills/inquest/SKILL.md` or `workflows/forge-inquest.md`
that rewords one of them must keep the literal string (or update every
consumer — kernel routing, telemetry, any future inquest tooling — in the
same change), same discipline as "Telemetry vocabulary," above.

- **REFUTER verdicts** — `REFUTED` (with evidence: the failure scenario was
  run, or otherwise disproved, and the defect does not hold), `CONFIRMED`
  (the refutation attempt itself reproduced the bug), `UNRESOLVED` (neither
  disproof nor reproduction was achievable with available evidence).
- **JUDGE verdicts** — `CONFIRMED` (routes through the `forge:triage` door
  as a ready queue-task draft; constitution rule 1's regression-test
  requirement applies to the resulting task), `DISMISSED` (recorded with
  the refuter's reason, never silently dropped), `UNRESOLVED` (surfaced
  directly to the human). Every finding that enters a tribunal pass exits
  through exactly one of these three — a fourth outcome is a protocol bug
  in the run, not a valid state.

## Ship-judge widening + Critical-security exploit bar — 2026-07-18

Response to fg-a10206 (tribunal-pattern survey, 2026-07-18, adoptions 1-2).
Amends "Verifier-finding filter (bounce pre-check) — 2026-07," above: that
filter scoped its trigger to `forge-verifier`/`forge-ui-verifier` FAIL,
leaving an asymmetry the survey named — the ship judges (`forge-reviewer`/
Rook, `forge-security`/Aegis, `forge-legal`/Lex; `skills/ship/SKILL.md`
checklist items 4-6) return findings that bypassed the filter entirely.
This closes the gap.

**Widened trigger.** WHEN `forge-reviewer` returns CHANGES REQUESTED,
`forge-security` returns CHANGES REQUESTED, or `forge-legal` returns
BLOCK-RECOMMENDED — any of which drives the ship protocol's overall `SHIP:
FAIL` (`skills/ship/SKILL.md`, "Bounce / blocked") — the kernel applies the
SAME filter defined above before that FAIL becomes a bounce: spot-check
each finding against the current tree, sort into SURVIVES / CHALLENGED /
FILTERED, bounce only on SURVIVES, and record every outcome (FILTERED and
CHALLENGED included) in the Attempt log. **Honesty carries over
unchanged:** a ship-judge FAIL whose findings all filter is still counted
by `tools/telemetry.py` as the `SHIP: FAIL` verdict of record —
PASS-after-filter changes what the kernel does next (no bounce dispatches),
never what the ship judge said, the same rule as the verifier case above,
applied here without modification.

**Critical-security exploit bar.** A `forge-security` finding tagged
Critical is held to a stricter bar than the general filter: the cited
location existing is insufficient for SURVIVES on its own — the kernel
must make an actual reproduction/exploit attempt (run the attack path,
trigger the vulnerable code with a crafted input, or equivalent concrete
evidence) before a Critical counts as SURVIVES. When that attempt is
inconclusive — the location exists, the finding is not refuted, but the
exploit does not reproduce either — the outcome is CHALLENGED, never
FILTERED — fail-safe: doubt keeps a Critical alive, it never silently
dies. Important-severity `forge-security` findings follow the general
filter unchanged.

**Legal scope limit.** Filtering a `forge-legal` finding is narrower than
the general filter's "defect reproduces on direct inspection" check: the
kernel verifies ONLY that the cited source (license text, dependency
manifest, third-party notice) exists and says what the finding claims it
says. The kernel never re-judges the underlying legal risk assessment
itself — that judgment belongs to `forge-legal`, and, per the ship
checklist's Legal pass, ultimately to the human deciding whether to
accept, swap, or drop a flagged dependency. A Lex finding whose cite does
not exist, or misstates what the cited source says, is FILTERED; a Lex
finding whose cite checks out is SURVIVES regardless of whether the
kernel agrees with the underlying risk call.

## Idle-wait discipline — 2026-07

Response to the 2026-07-18 live session where an undebounced Stop hook woke
the kernel five consecutive turns during one background build, each woken
turn re-reading an advancing worker's transcript before recognizing nothing
had changed. Craft memory `mem-9b31c5` records the hook-side fix (any Stop
hook that nudges must debounce itself, keyed by session id, since Stop fires
every turn-end, not once per session); this section is the kernel-side
counterpart — how the kernel itself is meant to behave while work it
dispatched is still in flight, independent of what the hook layer does or
fails to do.

**The discipline (NORMATIVE).**

- WHILE background dispatches are in flight and nothing is actionable, the
  kernel waits for completion notifications rather than checking in on its
  own initiative.
- At most ONE long fallback wakeup (>= 20 minutes, harness-permitting) may
  be scheduled per wait as a hang safety net — never a wakeup per dispatch,
  never a recurring short-interval poll.
- The kernel never polls worker transcripts turn-by-turn: reading an
  in-flight worker's output is triggered by that worker's own completion
  notification, never by an unrelated wakeup checking in on progress.
- An unrelated hook fire or stray wakeup that lands with no new notification
  attached ends the turn as a no-op — at most one short status line, no
  worker-output reads, no re-derivation of state already known from the
  last real notification.

## Idle-wait discipline — watchdog amendment — 2026-07-20

> Amends: "Idle-wait discipline — 2026-07" (above).

On the one long fallback wakeup the discipline above allows, the kernel
runs `tools/watchdog.py` for that turn and acts only on the flags it
prints (see "Watchdog thresholds — 2026-07-20", below) — a healthy run
prints nothing, so this costs nothing beyond the one script invocation on
the already-scheduled fallback.

## Idle-wait discipline — cold-cache dispatch note — 2026-07-20

> Amends: "Idle-wait discipline — 2026-07" (above).

Promoted from the jcode pattern (fg-a10702 steal-list, 2026-07-20): a kernel
dispatch that follows more than 5 minutes of session idle (no tool activity)
pays a cold prompt-cache cost a back-to-back dispatch does not, and today
nothing surfaces that cost.

WHEN a kernel dispatch follows more than 5 minutes of session idle (no tool
activity), THE SYSTEM SHALL add one line to the session report naming the
idle-gap length and the dispatch it preceded. This is visibility only: the
note never blocks the dispatch, and it never triggers auto-rescheduling. No
threshold configuration ships in v1 — the 5-minute figure is fixed, not a
`.forge/forge.md` override key (unlike the per-project `watchdog-<name>:`
overrides in "Watchdog thresholds — 2026-07-20," below).

**Composition with the watchdog fallback wakeup.** This note does not
restate "Idle-wait discipline — watchdog amendment — 2026-07-20"'s
fallback-wakeup sentence (above) — cited, not repeated: that amendment
governs what the kernel does DURING a long idle wait (run `tools/watchdog.py`
on the one allowed fallback wakeup); this section governs what the kernel
WRITES to the session report once a dispatch actually follows an idle gap
past the 5-minute mark. The two compose without overlap — a watchdog-flagged
wait and a cold-cache note can both fire off the same idle stretch, one
acting during the wait, the other reporting after it ends.

## Watchdog thresholds — 2026-07-20

Response to fg-a10211 (script-only, zero-token-when-healthy detection of
hung workers, runaway agents, stale claims, duplicate tasks, and
mechanically-mismatched worker reports — the automation counterpart to the
"Idle-wait discipline — 2026-07" fallback wakeup, above, which now runs it).
`tools/watchdog.py` is stdlib-only and read-only against `.forge/` and the
harness task-output dir passed via `--task-dir`; a healthy run prints
nothing and exits 0.

**Canonical default thresholds.**

| Flag | Threshold | Default |
|---|---|---|
| HUNG | worker transcript file has not grown for | 10 minutes |
| RUNAWAY | transcript byte budget | 2 MB |
| RUNAWAY | identical command repeated in the tail | 5 times |
| STALE-CLAIM | claimed-by age with no new Attempt-log line | 4 hours |
| DUPLICATE-TASK | normalized-title similarity (`difflib.SequenceMatcher`) | 0.85 |
| ATTEMPT-CAP | attempts past the bounce cap | 3 |

**Overrides.** Every threshold above is overridable per-project via
`.forge/forge.md`'s `## Features` section, as `watchdog-<name>: <value>`
bullet lines (e.g. `- watchdog-hung-minutes: 15`) — a missing or malformed
override line silently keeps the canonical default rather than erroring,
matching the "every missing toggle behaves as its default" rule already
established for Features ("Features (forge.md)", above).

**Report checking.** `tools/watchdog.py --check-report` reads a worker
RETURN report on stdin and mechanically verifies checkable claims only —
named changed files exist, cited paths resolve, and (when a gate-output
file is supplied) a claimed test count matches the most recently supplied
gate output — reporting each mismatch as a `REPORT-MISMATCH` line with the
claimed value next to the actual one. Prose-quality judgment (is the
summary accurate, is the fix actually right) stays with verifiers; this
mode never attempts it.

## Architect-plan refuter — 2026-07

Response to fg-a10207 (tribunal-pattern survey, 2026-07-18, adoption 3).
Applies the tribunal REFUTER role (`forge:inquest`, "Inquest tribunal —
2026-07", above) to `forge-architect` plans that touch the checklist spec
already escalates on — one adversarial pass on a plan's own judgment calls
before it turns into worker tasks, at zero cost to the common case.

**Trigger — cited, not restated.** The checklist is `skills/spec/SKILL.md`'s
Express lane **tier-escalation checklist** (the list following "Escalate to
full tier ... when the idea touches ANY of:"). This section never repeats
those items: a future edit to the checklist is read live from
`skills/spec/SKILL.md`, never from a stale copy here.

WHEN a `forge-architect` plan's BOUNDARIES or BLAST RADIUS touches the
tier-escalation checklist, THE SYSTEM SHALL run ONE refuter pass — a second
architect-capable spawn at equal-or-higher model tier than the architect
that produced the plan — attacking the plan's DECISIONS, TRADE-OFFS, and
BLAST RADIUS before decomposition. The refuter's verdict is handed to the
kernel alongside the architect's own OPEN QUESTIONS, both surfaced together
— never one without the other.

WHEN the plan does not touch the checklist, THE SYSTEM SHALL proceed
exactly as today — no refuter pass, no added cost, no change to existing
architect routing.

WHEN the refuter and the architect disagree irreconcilably, THE SYSTEM
SHALL surface BOTH positions to the human — the kernel never silently
picks a side, the same disagreement-goes-to-human discipline as the
Inquest JUDGE's UNRESOLVED path, above, scoped to planning instead of
debugging.

One pass, not a tribunal: no FINDER (the plan itself is the claim under
test) and no JUDGE (the kernel relays both positions; it never adjudicates
a verdict the human hasn't seen).

## Verification economics — 2026-07-18 (fg-a10901)

NORMATIVE. Ratified by the human 2026-07-18 ("too much verification for no real extra
gain... a lot of this can be done safely in parallel with other tasks"),
after two forensic passes over a live 16.5h frontend session: 18 builders vs
55 judges, four independent derivations of the same WCAG ratios on one task,
20–36min kernel digest stretches between waves, and a one-line bounce fix
re-running a 3-judge panel. Verification pays only where it buys verdict
independence or catches real risk; everything else below converts that into
rules. The existing verification-mode triage (gates-inline / Low-risk
sub-class / full spawn) and the floor — **no task integrates UNVERIFIED** —
are unchanged; quick fixes and trivial edits remain gates-inline with zero
spawned verifiers.

### Panel policy (per-task ceiling)

- At MOST one adversarial verifier per task: `forge-verifier` (Vera), or
  `forge-ui-verifier` (Iris) for visual criteria; a genuinely mixed
  code+visual task gets both — that pair is the ceiling, never a panel.
- **Rook (review): wave-end, not per-task.** One `forge-reviewer` pass over
  the wave's integrated diff after the last task of the wave integrates.
  Exception: `tier: full` tasks keep the per-task reviewer (ship checklist
  step 4) — the full tier IS the opt-in to per-task review.
  **Docs-wave skip (human tightening, 2026-07-18):** a wave whose diff is
  entirely docs/config/prose with every task pin-covered and
  verifier-passed SKIPS the wave-end reviewer outright (recorded in one
  line: `wave-end review: skipped — docs wave, pin-covered`); every 4th
  such skipped wave gets the reviewer anyway (sampling audit), so drift
  can't hide. Waves containing code keep the wave-end pass.
- **Aegis (security): named trigger only.** The kernel spawns
  `forge-security` ONLY when it names a specific trigger in the dispatch
  note: new cookie/storage write · raw-HTML or dangerouslySetInnerHTML ·
  auth/token/secret touch · form/redirect handling · parsing untrusted
  input · new dependency · money/payment flow. No named trigger → no Aegis,
  recorded in one line (`security: no named trigger`). This tightens ship
  step 5: same surfaces, but the trigger must be NAMED by the kernel, never
  inferred by habit.

### Single re-derivation owner

Each empirical fact (a measured ratio, a rendered state, a perf number) gets
ONE re-derivation owner on the panel — the designated skeptic re-measures
from rendered reality and publishes the table. Every other judge consumes
that table and judges its OWN dimension (method audit and spot-checks are
fine; a full recompute is not). Adversarial redundancy buys independence on
the VERDICT, not copies of the lab work.

### Build-ahead pipelining

WHEN a task's BUILD completes, the kernel immediately dispatches the next
DAG-permitted build; the verifier runs in parallel. **Verification gates
INTEGRATE, never the next dispatch.** A later verify FAIL bounces per the
normal path, and the kernel notes rework exposure for any dependent build
already started (its verifier gets the bounce context). Wave window
accounting is unchanged — verify spawns are read-only and share the
reserved slot discipline of "Sharded fan-out — 2026-07-18".

### Delta-only bounce re-verify

A bounce fix is re-verified by ONE verifier scoped to the fix plus the
specific finding that bounced it, at the cheapest adequate mode — never a
fresh full panel, never re-deriving facts the first pass already settled
(their owner's table stands unless the fix touched them).

### Wave-end review failure = merge-gate failure

WHEN the wave-end reviewer (or any wave-end check) fails the integrated
result, treat it as a merge-gate failure: bounce the offending task(s);
dependent work already built on top is re-verified, not silently shipped.
For sharded batches this composes with the ATOMIC shard INTEGRATE
(fg-a10815): the batch-invert rule applies before any partial state ships.

### Judge-yield telemetry

Every judge verdict the kernel consumes is recorded in the task's Attempt
log as `judge-yield: <agent-slug> raised=<N> survived=<M> changed=<K>`
(findings raised → survived the finding filter → changed the outcome:
bounce/blocked/design-delta). `tools/telemetry.py` aggregates per-judge
yield; `/forge:evolve` reviews it. Panel policy is data-ruled in BOTH
directions: a demoted judge whose wave-end yield shows real per-task
catches being missed gets re-tightened by evidence, not vibes.

## Verification infrastructure — 2026-07-18 (fg-a10908)

NORMATIVE. Origin: 2026-07-18 live forensics of a ui-verifier run — 16m37s
spent mostly on scaffolding (an npm build, a hand-rolled Playwright harness,
self-debugging, and FOUR server rebuild/restart cycles) before any judging
began, one of nine ui-verifier runs that same day repeating the pattern.
Separately, a 16.5h orchestrator session made 520 tool calls with ONE
ToolSearch and ZERO MCP calls, while three agent briefs advertise Serena "if
connected" and the scout's vetted shortlist never reached a single dispatch
contract. This section makes persistent, cited, pre-computed dispatch
infrastructure the rule instead of the exception, composing with
"Verification economics — 2026-07-18 (fg-a10901)" (above) without drift —
that section sets panel policy; this one sets what each panel member is
handed before it starts working.

### Harnesses committed on first use

WHEN a worker or verifier authors measurement tooling that could gate future
work (contrast scanners, tab-walk scripts, CLS probes, smoke harnesses), it
is committed as repo tooling (`scripts/verify-*` or `tools/`) with a
one-line README entry, so the NEXT agent RUNS it instead of hand-rolling a
fresh one. Throwaway scaffolding is allowed only when the check is
genuinely one-shot, and the dispatch contract must say which — either
"harness: committed at `<path>` — RUN it" or "harness: throwaway, one-shot
(<why>)".

### One build/server per wave

WHEN a verification panel needs a running app, the kernel (or the first
agent to need it) builds and starts ONE instance per wave and passes the
port/PID through the dispatch notes. Later panel members reuse it and never
rebuild; teardown is the kernel's, at wave end — this is the direct fix for
the FOUR rebuild/restart cycles the forensics found inside one 16m37s
verify.

### Cite-don't-restate environment invariants

WHEN a dispatch contract would restate environment invariants that every
agent in the repo needs (port etiquette, kill-own-PID-only, fixture-route
hygiene), it instead cites a committed reference file in the TARGET repo —
`AGENTS.md` (generated by `/forge:onboard`) is the committed home when the
target repo has one — rather than restating the prose per contract.

### Power tools note

WHEN the kernel dispatches into a repo where the scout (or onboard) has
vetted power tools, the dispatch contract carries a one-line "power tools"
note, e.g. "Serena active: use find_referencing_symbols for impact checks;
committed harness at scripts/verify-*" — so the scout's vetted shortlist
reaches dispatch instead of dead-ending after the scout pass.

### Context pack required

WHEN the kernel dispatches a task, the dispatch contract includes a
pre-computed CONTEXT PACK: the pointed files/symbols the work touches
(rooted via Serena/impact tools when active), the committed harness paths
to RUN, the shared server port (per "One build/server per wave", above),
and any prior measurement tables that already settled facts — so the agent
starts acting in its first minutes instead of re-deriving the map (user
direction 2026-07-18: "amazing plans... pre documented so that we can run a
lot more work in parallel and then require less checking").

## Clean-context debug escalation — 2026-07-18 (fg-a10701)

NORMATIVE. Adopted from the scout's three-harness audit
(`docs/audits/2026-07-18-scout-three-harnesses.md`, STEAL-LIST item 1 —
cc-sdd's auto-debug-on-2nd-reject), targeting the overhead audit's
bounce-cost finding (fg-a10209): a stuck worker re-poked with the same FAIL
notes twice rarely finds what it already missed twice.

### The escalation

WHEN a task has FAILed verification twice — the moment kernel INTEGRATE
would otherwise move straight to `state: blocked` with the double-bounce
postmortem — the kernel inserts ONE extra step first: dispatch
`forge-debugger` (Hex) in a FRESH context, never the same worker re-poked
with notes appended. Hex's spawn contract carries the failing diff plus
BOTH verifier FAIL notes as inputs; Hex root-causes from scratch via its own
hypothesis→evidence→fix protocol (`agents/forge-debugger.md`), with no
memory of the stuck worker's prior attempts.

### Outcome routing

WHEN Hex's fresh pass produces a fix, it routes through NORMAL verification
at the task's original equal-or-higher tier — a delta-only bounce re-verify
("Delta-only bounce re-verify," above), never a fresh full panel. A
re-verify PASS integrates normally; a re-verify FAIL falls through to the
block below exactly as if Hex had never run. WHEN Hex cannot produce a fix
(`RESULT: not-reproduced` or `blocked`), the kernel blocks the task with the
postmortem exactly as today — Hex's own ROOT CAUSE / HYPOTHESES writeup
folds into that postmortem's "what was tried."

### The cap

This escalation adds exactly one attempt, never a loop: at most ONE Hex
dispatch per task, ever — a re-verify FAIL after Hex's fix goes straight to
`state: blocked`, never a second Hex dispatch and never back to the
original worker.

## Spec-time boundary maps — 2026-07-18 (fg-a10910)

NORMATIVE. Adopted from the scout's three-harness audit
(`docs/audits/2026-07-18-scout-three-harnesses.md`, STEAL-LIST item 2 —
cc-sdd's design.md "File Structure Plan" with `_Boundary:_`/`_Depends:_` per
task), targeting the same audit's finding: file/scope boundaries surface
per-task at dispatch today, sometimes when the Execution plan is still
`(pending)` — this makes them surface at the human approval gate instead.

### Annotation requirement

WHEN `/forge:spec` pre-computes the task decomposition
(`skills/spec/SKILL.md` step 4), every decomposition item carries
`Boundary:` (the files/dirs it owns exclusively) and `Depends:` (the
contract tasks it consumes), derived from the design's file structure plan.
This composes with contract-first decomposition ("Verification economics —
2026-07-18 (fg-a10901)", above) rather than duplicating it: the contract
item that decomposition already splits out is exactly what a consumer's
`Depends:` line points at.

### Conflict resolution before the approval ask

WHEN two decomposition items claim overlapping `Boundary:` paths, that
conflict is resolved BEFORE the approval ask in step 5 — either serialize
the two items with a `blocked-by` edge, or re-split the boundary so the
overlap disappears. A decomposition with an unresolved `Boundary:` conflict
is never presented for human approval.

### Boundary carried into the task file

WHEN queue tasks are created from an approved spec (step 6), each item's
`Boundary:` carries verbatim into the created task file's Execution plan
body, pre-seeded there instead of left `(pending)`. This is the SOURCE the
kernel's dispatch-contract file-ownership line quotes: the spawn contract's
SCOPE "May modify" line (`skills/kernel/references/spawn-contract-template.md`;
cited by "Verification infrastructure — 2026-07-18 (fg-a10908)", above)
quotes the task's `Boundary:` instead of re-deriving file ownership from
scratch at dispatch.

## Finding severity + confidence — 2026-07-18 (fg-a10911)

NORMATIVE. Response to fg-a10911 (scout three-harness audit steal-list item
3, `docs/audits/2026-07-18-scout-three-harnesses.md`: oh-my-pi `/review`'s
P0-P3 severity + confidence per finding). Every finding a judge
(`forge-verifier`, `forge-reviewer`, `forge-security`) reports carries
`P0|P1|P2|P3` (P0 = ship-blocking correctness/security, P3 = polish) and
`confidence: high|medium|low` — REQUIRED output-contract fields, alongside
(never replacing) the existing MECHANICAL/JUDGMENT tag ("Latency rules —
ship-review overlap, mechanical bounces, batch gates, sliding-window
dispatch — 2026-07", above) and each judge's own Critical/Important/Minor
severity vocabulary. Canonically stated once here; each agent brief's own
"## Output contract" section (`agents/forge-verifier.md`,
`agents/forge-reviewer.md`, `agents/forge-security.md`) carries the fields
in its finding-line shape and quotes this section rather than restating it.

### Coherence with the finding filter

This section does not restate the Verifier-finding filter's ("Verifier-
finding filter (bounce pre-check) — 2026-07", above) SURVIVES/CHALLENGED/
FILTERED semantics, or the Ship-judge widening amendment's ("Ship-judge
widening + Critical-security exploit bar — 2026-07-18", above) widened
trigger and Critical-security exploit bar — it adds a numeric signal both
now use coherently:

- **(a) P0/high is never FILTERED on a spot-check alone.** This
  generalizes the Critical-security exploit bar above — until now scoped
  to Critical-tagged `forge-security` findings only — to any judge's
  finding tagged `P0` with `confidence: high`. The cited location existing
  is insufficient for FILTERED on its own: the kernel must complete a REAL
  re-check first — a delta-scoped verifier re-dispatch (the same
  "Delta-only bounce re-verify" instrument, "Verification economics —
  2026-07-18 (fg-a10901)", above) or an actual reproduction/exploit
  attempt equivalent to the exploit bar's (run the failing path, trigger
  the defect with a concrete input) — with its own evidence recorded in
  the Attempt log. Same fail-safe as that bar: when the re-check is
  inconclusive, the outcome is CHALLENGED, never FILTERED — doubt keeps a
  P0/high finding alive, it never silently dies.
- **(b) P3/low never alone bounces.** A finding tagged `P3` with
  `confidence: low` never by itself triggers a bounce — it rides along in
  the bounce contract as a note, not a trigger. The crisp rule: a bounce
  requires at least one SURVIVING finding that is EITHER severity `P0`,
  `P1`, or `P2` (any confidence), OR JUDGMENT-tagged with `confidence:
  medium` or `high` at ANY P-level. A finding meeting neither disjunct —
  P3 at any confidence paired with MECHANICAL, or P3 with `confidence:
  low` regardless of tag — never drives a bounce by itself; it still
  survives into the bounce contract as a note whenever at least one other
  finding qualifies.
- **(c) Severity is the judge's call; the filter never downgrades it.**
  The P-level and confidence a judge assigns are that judge's own
  evidence-backed assessment (each brief's Severity + confidence
  subsection, cited above) — the kernel's spot-check filter may change a
  finding's OUTCOME (SURVIVES/CHALLENGED/FILTERED, per the existing
  per-finding-outcome rules) but never its stated severity or confidence.
  Re-labeling a P0 down to make it easier to filter is out of bounds; the
  filter FILTERS with evidence that the defect does not reproduce, exactly
  as the existing rules require — it never re-judges impact.

### Telemetry: judge-yield severity distribution

`tools/telemetry.py`'s `judge-yield: <slug> raised=N survived=M changed=K`
line ("Verification economics — 2026-07-18 (fg-a10901)", above) extends
BACKWARD-COMPATIBLY with an optional trailing suffix `p0=A p1=B p2=C
p3=D` — counts of RAISED findings per severity level for that verdict. The
base shape with no suffix still parses exactly as it always has; a suffix
that is present but malformed (a missing p-level, a non-numeric count)
fails the WHOLE line, which falls into the unparsed tally rather than a
silent partial parse — the same coverage-honesty discipline "Telemetry
vocabulary — 2026-07" (above) already establishes for every other line
shape. `parse_attempt_log` stores the per-line severity counts only when
present, `aggregate` sums them per-slug, and `render_table` shows the
distribution only when a slug's summed counts are nonzero — a slug whose
judge-yield lines never carry the suffix renders exactly as it did before
this change. Per the Telemetry vocabulary discipline (above), this
extension updates `tools/telemetry.py` in this same change rather than
drifting the parser out of sync with the grammar.

## External-provider dispatch rules — 2026-07-19 (fg-c0112, spec-e8a3)

Response to `.forge/specs/2026-07-19-provider-profiles.md` (spec-e8a3),
"Dispatch mechanics — shared machinery, verification floor unmoved" and
"Provider-specific enablement gates". Three normative rules govern every
external-provider dispatch (OpenAI Codex CLI primary at ship; xAI Grok and
Google Antigravity gated behind their own pilot-test tasks per that spec's
Non-goals) that reaches this repo's verification path — cited here, not
restated from the spec's full acceptance criteria.

**JSON/JSONL-only output capture.** WHEN an external provider CLI is
dispatched, THE SYSTEM SHALL capture only clean JSON/JSONL structured
output — never a scraped TTY transcript. A CLI offering no structured
output mode is not dispatched at all: the dispatch helper refuses to invoke a CLI in a mode that doesn't offer clean structured output.
Ownership stated honestly: `tools/providers.py` (fg-c0102 /
bm-provider-cli-detection) ships non-mutating availability + authed-state
DETECTION only today; the dispatch helper itself — the component that
actually performs this refusal at invocation time — is Phase 2
worker-dispatch scope (bm-provider-worker-dispatch), not yet built. The
rule is normative now so that future dispatch helper has no discretion to
relax it later.

**Pin model IDs at implementation time.** WHEN a role-assigned provider is
dispatched, THE SYSTEM SHALL resolve its model via a per-provider tier map
built from that CLI's own live model-listing command — exact model IDs are pinned at implementation time from each CLI's own live model-listing command, never hardcoded from this spec's or any cutoff-bound knowledge.
This applies identically to every current and future provider profile: a
tier map that hardcodes a model ID from spec text or training data rather
than a live listing call is a defect against this rule regardless of which
provider it targets.

**Verification floor unmoved for external output.** WHEN external-provider
output (a judge verdict in Phase 1, or a worker diff in Phase 2) reaches
Forge's verification path, THE SYSTEM SHALL apply the verification floor
exactly as documented elsewhere in this shard — external output is never exempt from adversarial verify against EARS, and never eligible for a
provider-specific reduced protocol beyond the existing Low-risk
verification sub-class's own qualification rules (above) qualifying on
their own merits, never a provider-specific carve-out. A Phase 2 external
worker's diff is verified by a Claude-side `forge-verifier`/
`forge-ui-verifier` at the task's normal equal-or-higher tier, same as any
in-harness worker's diff — the verification floor stays unmoved regardless
of which CLI produced the diff.

## Benchmark-ratified routing — 2026-07-20 (fg-a10408)

Ratified from the T8 A/B benchmark's pre-registered rules (run
`t8-20260719`, `docs/audits/2026-07-19-ab-benchmark-t8-report.md`; delta
ratified 2026-07-20 in `docs/specs/2026-07-16-forge-design.md` §17):

- WHEN a task is feature-class, THE SYSTEM SHALL keep the full adversarial
  verification protocol — measured evidence: the single-agent arm shipped
  an important escaped defect past green gates that the protocol's
  verifier caught (R2 fired).
- No task class earned a gates-inline widening at N=2/class; the
  mechanical class (zero escapes, but cost ratio 1.39×/1.46× below the
  frozen ≥1.5× threshold) is the designated first candidate for a 3/class
  extension re-run before any lighter routing is proposed again.

## Grouped verification — 2026-07-20 (human-ratified)

Ratified by the operator after the 2026-07-20 session audit found 11
zero-verifier closes under an unratified "right-sized review" practice —
and the first retroactive sample over that set found a real P1 the inline
review had missed. The ruling replaces both the unratified practice and
pure per-task verification:

- WHEN tasks close, THE SYSTEM SHALL give every task real adversarial
  verification by a spawned verifier agent — kernel-inline "review" is
  never a substitute. Zero-verifier closes are disallowed for every class;
  the ratified low-risk sub-class means a real haiku verifier spawn, not
  no spawn.
- WHEN multiple related tasks are ready to verify, THE SYSTEM SHALL group
  them into one verifier dispatch — a coherent group is 2–4 tasks sharing
  a spec, surface class, or wave, with one contract listing each task's
  acceptance criteria and requiring a per-task verdict (one FAIL never
  hides behind a group PASS).
- WHEN more than one group is ready, verifier groups run in parallel with
  each other and overlap in-flight builds — verification cost scales with
  groups, not tasks, without reopening the zero-verifier gap.
- Delta re-verifies after a bounce may batch the same way (one verifier
  re-checks every fix in the group).

## Marginal-gain stop rules — 2026-07-22 (human-ratified)

Ratified by the operator after the 2026-07-22 consensus-loop ruling
("lean: escalate-only"), extending the same economics to ALL verification:
review earns its cost on the first adversarial look at risky work and
stops earning past one round of fixes. These rules cap repetition; they
never touch the first look, the grouped-verification floor, the named
security triggers, or the human spec gate.

- **Lifetime judgment cap.** WHEN an artifact (a task diff or a plan) has
  received its initial adversarial pass plus ONE delta re-verify after
  fixes, THE SYSTEM SHALL NOT dispatch a third judgment pass over it —
  anything still disputed escalates to the human as a plain-English
  blocker, never another model round. The bounce-retry attempt cap is
  unchanged; this caps VERIFIER passes, not build attempts.
- **Never re-verify a judge's own fix.** WHEN a verifier's finding
  prescribed an exact fix and that fix is applied as written with gates
  green, THE SYSTEM SHALL close the finding without re-spawning the judge
  to confirm its own prescription. A finding fixed some OTHER way still
  counts against the delta re-verify (P0/P1 only, per Verification
  economics).
- **Cosmetic findings never cost a dispatch.** WHEN a finding is P3 or
  cosmetic — on the build side or the plan side — THE SYSTEM SHALL fix it
  inline, gate, and record it as fixed-inline; it never re-queues a
  judgment pass and never keeps a loop alive on its own.
- **No auto-chained sweeps.** Audits, courts, and bug-hunt rounds run
  ONLY on human invocation or a human-set schedule. A shipped wave never
  automatically triggers a follow-up audit of itself; the kernel may
  RECOMMEND one in the session report, but the human pulls the trigger.

## Blast-radius gate — 2026-07-23 (owner-directed)

Amends "Verification economics — 2026-07-18 (fg-a10901)" and widens
mode 1 in `skills/kernel/SKILL.md` VERIFY. Owner-directed after a live
session ran a full verifier spawn on every task in a queue where most
tasks were mechanical: "this didn't really need the full verifier system
for every task."

**Rule.** Tier alone no longer decides whether a task earns a verifier
spawn. `tier: trivial` takes mode 1 (gates-inline) as before. A
`tier: standard` task ALSO takes mode 1 when its diff passes all five
tests enumerated in `skills/kernel/references/verify-modes.md`,
"Blast-radius gate (mode-1 widening) — 2026-07-23", which is NORMATIVE
and is the canonical enumeration: gate-covered acceptance clauses, no
new behavior or contract, no sensitive surface (security/auth/secret/
money/PII/migration/deletion, or `skills/`, `agents/`, `hooks/`,
`workflows/`, `.forge/` protocol files), not visual, and first attempt.
`tier: full` NEVER qualifies — spec-approved work always ships through
`forge:ship` unchanged.

**Whitelist, not a judgment call.** Every one of the five tests must be
clearly true. "Probably fine" is a mode-2 answer. The kernel records
`blast-radius: clear — <reason>` or `blast-radius: verifier — <which
test failed>` in the Attempt log, so the decision is auditable in both
directions.

**Hard Rule 3 is untouched.** Mode 1 is the KERNEL running the gate
commands itself against the returned diff — never the worker re-checking
its own output. What the gate removes is a second model's opinion, not
the objective check. A task with no real gates therefore fails test (a)
and cannot reach mode 1 at all.

**Sampling audit.** After 6 consecutive blast-radius-clear completions in
a session, the 7th qualifying task takes full verification anyway
(`sampling audit` in the Attempt log). This is the only defense against
the gate drifting into "everything qualifies," at a cost of one verifier
per seven tasks. It is deliberately separate from the low-risk routing's
own 5th-task audit above; a session can trip both.

## Parallel-first dispatch — 2026-07-23 (owner-directed)

Amends the delegation GATE in `skills/kernel/SKILL.md` step 4. Owner-
directed after the same session: the kernel's "first instinct wasn't to
spawn agents for parallel execution."

**Rule.** Parallel dispatch is the DEFAULT whenever the wave-level
parallel-eligibility test passes. Sequential or inline execution now
needs a stated reason recorded in the Routing record — the burden of
justification is inverted from what it was. The eligibility test itself
is unchanged (≥2 `parallel-safe` tasks, no `blocked-by` edges among
them, declared non-overlapping file scopes).

**Consequence for the delegate criteria.** "Genuine parallelism exists"
is no longer one of the three inline-vs-delegate criteria, because
parallelism is now decided BEFORE that question rather than as one input
to it. The two remaining criteria are context pollution and specialist
need.

**Supersedes every "default 3".** `max-parallel-tasks` has defaulted to
`auto` (`min(cores - 2, 16)`, floored at 1) since v0.24.0. Any prose
still describing the default as `3` — including "Sharded fan-out —
2026-07-18"'s batch-size line and the kernel's own former GATE text — is
stale and superseded by this section. A batch of 2-3 is a floor, not a
target: on a typical 8-32 core machine the window is 6-16.
