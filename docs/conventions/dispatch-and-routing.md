# Dispatch and routing

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## Loop patterns

Three loop shapes are first-class citizens of Forge orchestration — named
here so skills and contracts can reference them instead of re-describing
them:

- **Bounce-retry loop** — the existing INTEGRATE FAIL path (`forge:kernel`,
  INTEGRATE): re-dispatch the same worker contract plus the verifier's notes,
  max 2 retries, then `blocked` + mandatory double-bounce postmortem. Bounded
  by attempts.
- **Loop-until-dry sweep** — for audits and bug-hunts: keep dispatching
  finder rounds until **2 consecutive rounds surface nothing new**, then
  stop. The termination condition is emptiness of findings, not a fixed round
  count. Defined here; audit-shaped tasks and skills (e.g. security sweeps,
  coverage-gap hunts) adopt it by reference.
- **Watch loop** — during a fix: re-run the failing gate after each change
  until green, **bounded by attempts, never by time**. Cap attempts (same
  spirit as the bounce-retry cap) and report the attempt count; a watch loop
  that hits its cap escalates rather than spinning. Defined here; workers and
  the debugger adopt it by reference.

All three inherit the kernel's budget accounting: every dispatched round
increments the session dispatch count.

## Workflow executor

Response to the Batch D executor work; full mechanics in `forge:kernel`
("Executor").

- **Toggle:** forge.md Features `workflow-executor` (default `on`). Active
  only when the harness actually offers the Workflow tool; otherwise the
  sequential markdown loop runs regardless of the toggle.
- **Reference scripts:** `workflows/forge-wave.md` (parallel-eligible batch:
  per-task worker-in-worktree → verifier pipeline, with the verifier's
  constitution check threaded through via `constitutionRules` when
  `.forge/constitution.md` exists) and `workflows/forge-ship.md` (full-tier
  ship review: reviewer ∥ conditional security ∥ conditional legal, each with
  its own strict findings/verdict schema). Both are annotated canonical
  shapes the kernel instantiates, not files executed as-is.
- **Resume / runId convention:** the kernel records the workflow `runId` in
  each dispatched task's Attempt log at dispatch time. A run that dies is
  resumed via `resumeFromRunId` (completed `agent()` calls return cached),
  preferred over re-dispatching from scratch. Scripts stay deterministic —
  no `Date.now()`/`Math.random()`; timestamps travel in via args — so the
  cached replay is valid.
- **Invariant:** workflow mode must produce **byte-identical `.forge/` state
  transitions** to the sequential path. Scripts return results only; the
  kernel performs INTEGRATE and every `.forge/` write sequentially on main
  (Hard Rule 4). Workflow dispatches increment the session dispatch count
  exactly like sequential ones, so `max-tasks-per-session` binds identically.
- **Budget-guard blind spot:** in-script `agent()` calls are not Task/Agent
  tool dispatches, so the `budget-guard` PreToolUse hook (Budget keys
  amendment, above) never observes them; the kernel's own dispatch count —
  incremented once per task handed to the script at the Workflow call — is
  the ONLY enforcement mechanism in Executor mode.

## Run charter (2026-07-17)

Every kernel run — sequential, parallel, or workflow-executed — begins with a
stated charter: **goal** (one sentence), **scope** (tasks/areas in play),
**stop conditions**, and **budget** (caps in force). Interactive sessions
present it to the human before the first claim (structured confirm when a
judgment call is involved); standing-consent runs (continuous-loop, schedule,
headless) derive it from the queue + forge.md and record it verbatim at the
top of the session report. No dispatch precedes the charter. Defined in
`forge:kernel` SYNC ("Run charter"). This is the run-level counterpart of the
task-level charter every task already carries (EARS criteria, tier, priority,
scope, dependencies): loops and workflows never fire without a stated intent,
and never for work whose tier doesn't warrant them (trivial stays inline —
GATE proportionality rules are unchanged by any Feature toggle).

## Model vocabulary — fable amendment (2026-07-17)

The ROUTED model vocabulary is unchanged: `haiku | sonnet | opus`. Agent
frontmatter `model:` values and every router-assigned ROUTING line use only
those three; `opus` remains the strongest tier the router selects on its own.

`fable` is additionally recognized as a **human-authorized escalation, never
a route**: it is very expensive, so no routing-table row, no agent default,
and no automatic kernel decision may select it. It becomes available only
when a human asks — directly in conversation, or via an explicit
`fable/<effort>` line under forge.md `## Routing overrides` — and is meant
for work needing extremely deep reasoning (novel architecture with cascading
unknowns, forensic analysis where a wrong conclusion is unrecoverable, a
final adversarial gate the human wants at maximum capability). The kernel
may RECOMMEND it in a session report or blocker note; it never dispatches to
it unprompted. A ROUTING line using fable must name the human authorization.

## Report tasks (finder pattern) — 2026-07-17

> Amended by: "UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18", "Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)"

Response to the sweep-2 regression and hygiene audits
(`docs/audits/2026-07-17-sweep2-regression.md` §1;
`docs/audits/2026-07-17-sweep2-hygiene.md`, Part A2).

**Confirm-only route (mirrors `forge:kernel`'s first-touch confirm gate).**
The untrusted-`.forge/` first-touch confirm gate (`forge:kernel`, "Untrusted
`.forge/` — first-touch confirm gate") is hostable by any command whose own
trust preamble hits an untrusted `.forge/`, not only `/forge:start` — on
CONFIRM, that command writes `.forge/.trust-local` and returns to its own
flow rather than auto-starting the kernel loop.

**Report tasks (finder pattern).** A standard-tier task whose only
deliverable is a findings report — read-only against the tree otherwise —
may route to a "finder" instead of a `forge-worker` + `forge-verifier` pair,
with verification collapsed to kernel synthesis (the kernel reads the
finder's report and judges it directly, no separate verifier spawn). This
pattern was used informally across the 2026-07-17 9a/9b audit waves without
being documented anywhere; it is retroactively formalized here rather than
disallowed, because the pattern itself is sound for genuinely read-only
report work — what was missing was the guardrails, not the idea. A finder
route is valid only under ALL of:

- **(a) Declared, not silent.** The task's Routing record states the route
  explicitly — `finder — verification: kernel synthesis` (plus the usual
  model/effort/reasoning) — never bare `finder` with no verification note,
  and never silently substituted for a verifier spawn on a task that isn't
  a report task.
- **(b) Stale-finding re-check.** Every finding in the report is re-checked
  against the CURRENT tree state before any fix task is queued from it — a
  finder's findings can go stale between when it ran and when a human or the
  kernel acts on them, especially when other work lands concurrently (see
  craft memory `mem-b82d19`: parallel finders racing a concurrent writer
  produced findings that were already stale by synthesis time). This
  re-check is not optional ceremony; skipping it is how stale findings turn
  into wasted or wrong fix tasks.
- **(c) Scope-limited.** Never applicable to a task that modifies files
  beyond its own report — the moment a task's deliverable is anything other
  than the report itself (code, config, `.forge/` state), it is not a
  finder task and takes the normal worker+verifier path.

This does not relax VERIFY for any task that writes code or touches
`.forge/` — the finder route exists only for the narrow read-only-report
case, and (a)-(c) above are conditions, not defaults. See `forge:kernel`,
VERIFY, mode 3.

## UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18

Response to the 2026-07-18 sweep-3 audits
(`docs/audits/2026-07-18-sweep3-frontend.md`, critical #2;
`docs/audits/2026-07-18-sweep3-coldstart.md`, C3;
`docs/audits/2026-07-18-sweep3-regression.md`, §2). Three additions.

**UI+motion task splitting (canonical rule).** When a task's acceptance
criteria span BOTH structural UI and non-trivial motion, it is split at
intake into two linked tasks rather than queued as one: a `ui`-shaped task
(routes to `forge-ui`) and a `blocked-by` animator task (routes to
`forge-animator`, `blocked-by` the ui task — motion is built against the
structure, not before it exists). Each split task carries its own EARS
criteria, scoped to its own surface. Trivial micro-transitions (hover/focus
states, a simple opacity fade, anything already covered by the project's
existing CSS transition tokens) are NOT "non-trivial motion" for this rule
and stay on the `ui` task — only motion substantial enough to warrant
`forge-animator`'s attached skills (entrances/exits, scroll-driven effects,
choreographed sequences, spring physics, gesture-driven interaction)
triggers the split. This is the same judgment `forge-worker`/`forge-ui`/
`forge-animator`'s Scope boundary sections already use to route a single
task to the right implementer; splitting at intake makes that routing
decision once, in the task shape, instead of re-deriving it mid-build with
no worker-to-worker sub-dispatch mechanism to act on it. Applied by
`forge:queue` Create and `forge:spec` Decompose alike.

**Empty-repo gates-pending mode (amends "forge.md (project config)",
"Malformed forge.md," above).** When forge.md's Gates carry onboard's
"no code yet" note, or the kernel's own auto-detect finds NO recognizable
build/test/lint tooling AND the repo has no source files, SYNC enters
GATES-PENDING mode instead of halting: the loop may dispatch tasks whose
acceptance criteria are self-contained and checkable without project gates
(file creation, scaffolding), using each task's own criteria-declared
checks in place of gate commands. SYNC re-attempts gate auto-detection
every session and exits gates-pending the moment real tooling lands,
writing the detected gates back per the existing `(auto-detect)` rule. The
"malformed forge.md" halt text above now applies only when tooling EXISTS
but its declaration is genuinely unparseable and unrecoverable — never to a
genuinely empty repo, which is gates-pending, not malformed. This mode
governs gate ABSENCE only; it does not relax the trust boundary above — an
untrusted `.forge/`'s stored Gates commands are still never executed,
empty repo or not.

**Finder dispatch has no dedicated agentType (amends "Report tasks (finder
pattern)," above).** VERIFY mode 3's finder route is dispatched as a
GENERIC read-only agent dispatch — the harness's general-purpose agent
under a kernel-declared read-only contract — not a roster `agentType`. No
roster agent is named "finder" and none is required: `forge-worker`'s
no-open-ended-exploration rule is not violated by this, because a finder
dispatch is never a `forge-worker` dispatch in the first place.

## Prefer the agent factory over ad hoc generic dispatch — 2026-07-19

> Amended by: "Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)"

Response to a human directive during a live inquest re-run: when a task
type recurs (the same shape of read-only role gets spawned pass after pass,
run after run) rather than being a true one-off, route it through
`forge:agent-factory` and mint a persisted, named roster agent — *before*
reaching for a generic `general-purpose`/`Explore`-style dispatch — so the
work stays discoverable, routable, and improvable inside Forge's own
ecosystem instead of living as an ad hoc prompt that gets rewritten from
scratch (and drifts) on every invocation.

**The test is recurrence, not existence of a task.** A single genuinely
one-off exploration (a question asked once, never to be asked the same
shape again) can stay generic — minting an agent for something that will
never recur is the "graveyard" failure mode the factory checklist's
no-roster-duplication gate already guards against from the other direction.
But the moment a role is dispatched the same way more than once as part of
a named protocol (a skill's own documented tribunal, sweep, or pipeline
stage), that is exactly the agent-factory's own "recurring task type no
roster agent fits" trigger — check the roster first, and if nothing fits,
propose minting one rather than repeating the same hand-written prompt.

**Concrete precedent.** `skills/inquest/SKILL.md`'s FINDER/REFUTER/JUDGE
roles ran generic for a full pass (this same convention file's "Finder
dispatch has no dedicated agentType" note, above, originally scoped that
choice to the *separate* report-task finder pattern, but the same reasoning
had been informally extended to inquest's three roles too) before being
roster-ified into `forge-finder`/Hound, `forge-refuter`/Foil, and
`forge-judge`/Gavel (spec §6.2) — see those three agent files' own
Provenance sections for the full trail. The report-task finder pattern
itself remains generic, since a report task's finder shape varies
per-dispatch rather than repeating one fixed protocol.

This preference amends nothing about the factory's own gates — every new
agent still goes through the full checklist (`references/factory-checklist.md`)
and the structured-question approval flow (`commands/agent.md`); this
section only changes which option a session reaches for *first* when a
recurring, protocol-shaped role needs a spawn.

## Latency rules — ship-review overlap, mechanical bounces, batch gates, sliding-window dispatch — 2026-07

Response to the sweep-4 efficiency wave (fg-9e0101, fg-9e0103). Four latency
rules, canonically stated here so `forge:kernel`, `skills/ship/SKILL.md`,
`workflows/forge-ship.md`, and both verifier agent contracts can point to
this section by name instead of restating it. None of the four relax any
done-bar/gate semantics — every FAIL/CHANGES REQUESTED/BLOCK-RECOMMENDED
still fails a task exactly as before; only *when* work is dispatched, and at
what tier a mechanical fix redispatches, change.

**1. Ship-review overlap.** WHEN a full-tier task's builder returns, the
kernel does NOT wait for the verifier verdict before starting the ship
judges. It dispatches the verifier spawn (`forge-verifier`/
`forge-ui-verifier`, `forge:kernel` VERIFY mode 2) AND the ship judges —
`forge-reviewer` plus conditional `forge-security`/`forge-legal`
(`forge:ship`), or the `forge-ship` Workflow script when Executor is
active — as ONE parallel batch. All of these judges are read-only against
the same diff, so genuine parallelism exists (delegation criterion b) with
zero integration risk: nothing one judge does can invalidate what another
reads. Because the reviewer no longer necessarily runs after the verifier,
`forge-reviewer`'s "don't re-verify EARS clauses already PASSed" instruction
is no longer a sequencing fact — it is restated as a scope instruction
("EARS-clause verification is the verifier's surface, running in
parallel — not yours") in the ship-judge dispatch prompt
(`workflows/forge-ship.md`). The done bar at INTEGRATE is completely
unchanged: it still consumes every verdict — verifier, constitution,
reviewer, conditional security, conditional legal — and any single FAIL,
CHANGES REQUESTED, or BLOCK-RECOMMENDED among them fails the task, exactly
as the sequential protocol always specified. Only the wall-clock ordering
moves; the pass/fail semantics do not.

**2. Mechanical-tagged bounces.** A verifier's (or `forge-ui-verifier`'s)
FAIL NOTES lead with exactly one tag: **MECHANICAL** (a single precise fix,
exact file/location plus the verbatim expected change, zero judgment
required to apply it) or **JUDGMENT** (everything else — when uncertain,
JUDGMENT). On a MECHANICAL-tagged FIRST bounce, the kernel's INTEGRATE step
MAY re-route the fix-only redispatch to haiku/low, quoting the FAIL NOTES
verbatim in the contract — the same quote-verbatim discipline craft memory
`mem-7c41ae` already established for dispatch briefs and acceptance
criteria. Re-verification is unaffected by this: it always runs at the
original equal-or-higher model tier regardless of the fix's redispatch
tier, because the judge's tier requirement is about the work it checks, not
who wrote the fix. A JUDGMENT tag, or the SECOND bounce of any task
regardless of tag, always redispatches the fix at the task's original
routed tier — the haiku/low path is a first-bounce-only, mechanical-only
optimization, never a standing downgrade.

**3. Single-gate batch INTEGRATE (parallel-batch tasks).** For an eligible
parallel batch (`forge:kernel` GATE, "Parallel eligibility"; mechanics in
`skills/kernel/references/parallel-dispatch.md`), INTEGRATE merges ALL
verified worktrees in completion order first — conflict-checking each merge
individually as it lands — and then runs the gate commands ONCE against the
fully-merged result, not once per task. If the merged-result gate run is
green, every task in the batch commits together; the merged-gates run
remains authoritative over any per-worktree gate pass, unchanged from the
existing rule. If the merged-result gate run fails, the kernel bisects by
re-running gates per-merge in the same completion order used to build the
merge, to isolate which task's merge broke the batch — bisection is a
failure-path-only cost, never the common case. This does not relax
INTEGRATE's existing "strictly sequential and kernel-owned" merge discipline
(`skills/kernel/references/parallel-dispatch.md`, "INTEGRATE — Parallel
batch") — it only collapses N redundant gate runs into one for the common
case where every merge in the batch is clean.

**4. Sliding-window dispatch.** `max-parallel-tasks` (forge.md Queue
section, default 3) is a concurrency window on simultaneous spawns, not a
hard cap on how many wave tasks a session may eventually run. When a batch
has more parallel-eligible tasks than `max-parallel-tasks` allows in flight
at once, the surplus tasks wait, and each is dispatched the moment an
in-flight worker's slot frees (worker completes or bounces out of the
in-flight set) — the window slides, rather than the kernel dispatching one
fixed batch and stopping. `.forge/` writes and merges remain strictly
serialized and kernel-owned regardless of how many workers are in flight —
the sliding window only concerns worker dispatch concurrency, never queue-
state mutation, which stays exactly as single-threaded as the existing
Hard Rule 4 / INTEGRATE sequencing already requires.

## Sharded fan-out — 2026-07-18

Response to fg-a10801 (T3 of the decomposition; design:
`docs/plans/2026-07-18-sharded-fanout-design.md`; schema: fg-a10811,
`tools/validate_task.py`; splitter: fg-a10812, `tools/shard_task.py`). A
single queue task can declare that it splits into N disjoint slices,
dispatched to N identical-slug workers, each in its own git worktree, then
merged and verified — **intra-task fan-out**, distinct from the inter-task
**parallel waves** ("Parallel dispatch (Waves amendment, 2026-07-17)",
above): waves run N *different* tasks concurrently; sharding turns *one*
task into a swarm of copies of itself over disjoint scope. This is the
canonical section fg-a10801 EARS clause 4 requires: the mechanism is found
here, in ONE dated section.

### Frontmatter fields

Three new, optional, additive frontmatter fields (`tools/validate_task.py`,
fg-a10811) — a task with none of them validates exactly as before:

| Field | Type / values | Notes |
|---|---|---|
| `shard-by` | `files` \| `items` \| `ranges` | the split dimension; absent = not shardable |
| `max-shards` | integer ≥ 2 | upper bound on slice count; required when `shard-by` is set, but `max-shards` alone (without `shard-by`) is currently accepted, not rejected — validation is directional, matching fg-a10811's shipped shape check |
| `shard-key` | scalar string, not a list | required when `shard-by` is `items` or `ranges`; optional for `files` |

`shard-by`/`max-shards`/`shard-key` are orthogonal to `parallel-safe`: a
shardable task does not need `parallel-safe: true`, and a `parallel-safe:
true` task is not automatically shardable — the former governs intra-task
fan-out, the latter inter-task wave eligibility.

### Source resolution and split (`tools/shard_task.py`, fg-a10812)

The splitter resolves `shard-key` into a deterministic, deduped, sorted
list of atoms, then partitions it. `files`/`items` sources accept an
inline literal string, a list of strings, or one or more glob patterns
(expanded via `glob.glob`, recursive); every resolved atom is deduped
through a `set()` before sorting, so two glob patterns that resolve the
same path collapse to one occurrence rather than landing in two slices.
`ranges` sources are a plain `(start, end)` inclusive integer pair or a
`"start-end"` string — no filesystem or process interaction. **No `cmd:`
source in v1** — see "`cmd:` shard sources", below.

Chunking is a stable-sort-then-contiguous-divmod rule: the degenerate case
(0 or 1 atom) always yields exactly ONE slice, never an error, never a
fan-out, regardless of `max-shards`. Otherwise `N = min(max-shards, atom
count)` contiguous, disjoint, exhaustive chunks, sized as evenly as
possible. Each slice manifest is `{"index": i, "shard_by": ..., "items":
[...]}` with a 1-based `index`, so the kernel labels swarm members
`#1..#N` directly off the slice index — no separate labeling pass. Same
inputs always produce identical slices (no wall-clock, no randomness), so
a resumed run replays the frozen manifest rather than re-enumerating.

### Shard → dispatch → merge → verify protocol

- **Shard**: the kernel resolves the source set and computes the slice
  manifests (above) once, at GATE, and freezes them into the Attempt log
  before dispatch.
- **Dispatch**: each shard-job is its own worker spawn with Agent-tool
  `isolation: "worktree"` — the identical mechanism the parallel-wave path
  already uses. Shard spawns share the SAME sliding-window concurrency cap
  (`max-parallel-tasks`) as inter-task wave members — one global
  concurrency budget, not a second nested window.
- **Merge**: kernel-owned and strictly sequential, one worktree at a time,
  completion order — merge into main, then run gates on the merged result
  (Hard Rule 4: shard workers never touch `.forge/`; all `.forge/` writes,
  including the Attempt log, are kernel-only, on main). Disjoint outputs
  make a merge conflict structurally impossible in the common case; a
  *surprise* conflict (scope overlap the splitter missed) bounces that
  shard to `blocked` with the conflict noted — never resolved
  speculatively, identical to the wave rule.
- **Verify**: the merged-result gate run is authoritative over any
  per-worktree pass. Per-shard verifier spawns are optional — see "Skip
  per-shard EARS verify", below, for what that optionality actually means.
- Each shard's outcome is recorded as its own line in the ONE task's
  Attempt log — N shard-jobs map to one task file, not N task files —
  written sequentially and kernel-owned, same discipline as any other
  serialized `.forge/` write.

### Worktree-per-shard isolation — MANDATORY

Every shard worker MUST dispatch under Agent-tool `isolation: "worktree"`.
Parallel identical-slug workers must never share a mutating tree — this is
the structural fix for the shared-tree-corruption hazard recorded as a
craft gotcha (mem-c72f04): workers clobbering siblings' uncommitted files,
`git stash`/`checkout` destroying sibling work, phantom test failures from
sibling churn. Sharding exists, in part, to make that failure mode
structurally impossible rather than relying on worker discipline. Orphaned
shard worktrees from a dead session are flagged by the existing SYNC
stale-worktree sweep for human cleanup, exactly like orphaned wave
worktrees — no new recovery machinery.

### Display convention

A sharded swarm displays with the dispatched slug unchanged
(`forge-worker`, `forge-grunt`, whichever slug the task routes to) and an
instance suffix `#1..#N` taken directly from the slice manifest's 1-based
`index` — workers are disambiguated by instance number, never by task id,
since all N shard-jobs share the one task id.

### Shard-eligibility predicate — separate from wave eligibility

Wave eligibility ("Parallel dispatch (Waves amendment, 2026-07-17)",
above) is a **mechanical scope-overlap check**: ≥2 tasks, each
`parallel-safe: true`, no `blocked-by` edges among them, non-overlapping
declared file scope, batch size ≤ `max-parallel-tasks`. Shard eligibility
is NOT the same predicate applied at a smaller grain — it ADDS a
conservative judgment call on top: `shard-by` present with `max-shards` ≥
2; the resolved source has ≥2 atoms; the splitter produces provably
disjoint slices; AND **no cross-slice dependency** — the task's criteria
must not require slice *i* to read slice *j*'s output. That last test is
not mechanical — it is a judgment call, and **when uncertain, do NOT
shard.** Any failure means the task runs as one worker, unchanged; the
decision (sharded into N, or why single) is recorded in the Routing
record, exactly as the wave-eligibility decision is.

**`shard-by: files` is RESTRICTED in v1 to provably per-file-local
operations** — formatting, header insertion, per-file codemods with no
cross-file signature change. A file set coupled through the build graph (a
signature change that ripples to callers, a shared type touched from
multiple files) is **textually-clean-but-semantically-broken** when split
by file: each shard's diff looks correct in isolation, the per-shard scope
is genuinely disjoint, and the merge is conflict-free — but the merged
*behavior* is wrong in a way none of the structural checks above catch,
because those checks test disjointness of text, not coupling of meaning.
Build-graph-coupled file sets must NOT be sharded by `files`.

### Nesting (a shardable task that is also a wave member) — OQ1 resolution

Human-decided 2026-07-18 (fg-a10801, "Human decisions"), reconciled
against the refuter's execution-safety argument (fg-a10801, "Refuter
verdict + kernel reconciliation"): nesting is **SUPPORTED by schema and
loop from day one** — never a retrofit. A shardable task that is also an
inter-task wave member is held under the **SAME single sliding-window
cap** as every other spawn (no second, shard-private window), with **≥1
slot reserved per distinct wave task** so a task's shards can never starve
its wave siblings of a dispatch slot.

**"Allowed ≠ always-chosen."** Schema and loop supporting nesting does not
mean the kernel picks it: the shard-eligibility predicate above still
applies in full, and it does not auto-select a double fan-out where the
no-cross-slice-dependency judgment is unproven. A task may be structurally
eligible to nest and still run un-sharded, or as the sole member of its
wave, if that judgment can't be made with confidence.

### `cmd:` shard sources — DEFERRED (OQ2 security decision)

**v1 ships `inline-list` and glob shard sources only.** `shard-key: cmd:
<command>` — enumerating a shard source by running a command — is
explicitly deferred to a future task, reversing the human's initial lean
toward gating it like `forge.md` Gates commands, per the refuter's dissent
(fg-a10801, "Refuter verdict + kernel reconciliation," OQ2). The reason is
the existing trust-boundary rule this file already states: "Trust cannot
travel with content arriving after the first confirm — merges widen blast
radius" ("Trust boundary — specs + NL scoping amendment (2026-07-17)",
above). A `cmd:`-bearing task merged into an already-trusted `.forge/` by
a compromised collaborator — the exact scenario that rule describes —
would dispatch on the next `continuous-loop` wave with **no re-gate**,
because the trust confirmation happened before that content ever arrived.
Gating `cmd:` like Gates commands does not cover this merged-content path,
only the untrusted-repo-at-first-confirm path. Inline-list and glob
sources carry no execution surface — they are always safe — so v1 loses
no coverage of the shipped schema by excluding `cmd:`.

### Skip per-shard EARS verify — tied to Low-risk verification, not a blanket exemption

"Per-shard verifier spawns are optional for mechanical work" (above) is
**not** a blanket "mechanical work → optional verify" rule. It is the
EXISTING **Low-risk verification (standard sub-class) — 2026-07**
predicate (above), applied at shard granularity: a shard's per-slice
verify may be skipped only when that shard's diff would itself qualify
under that section's conjunctive qualification — every EARS clause
pin-covered, no `skills/`/`agents/`/`hooks/`/`workflows/`/`.forge/`
protocol-file touch, gates cover it. "Gates-green ≠ acceptance-met" holds
at shard granularity exactly as it holds at task granularity; a shard that
doesn't qualify gets a real verifier spawn, same as any other
standard-tier work.

### Shard INTEGRATE is ATOMIC for the task — inverts parallel-batch INTEGRATE

Parallel-batch INTEGRATE is explicitly **not** all-or-nothing: one wave
task failing does not stop the rest of the batch ("Parallel dispatch
(Waves amendment, 2026-07-17)", above). Shard INTEGRATE **inverts** that
rule: because N shard-jobs are slices of **one** task, not N independent
tasks, a broken shard re-dispatches only that shard's slice (max 2
retries); a **second** failure of the same shard blocks the **whole
task**, with a mandatory double-bounce postmortem — there is no "drop the
broken member, integrate the rest" option, because the slices are not
independent deliverables, they are one deliverable in pieces. This
atomicity is why shard dispatch needs its own INTEGRATE kernel stub,
separate from the batch-INTEGRATE stub GATE and DISPATCH reuse — the two
rules (batch: not all-or-nothing; shard: atomic) cannot share one stub
without one of them being silently wrong. That stub is out of scope here
(T5, fg-a10816).

## Sharded fan-out — per-shard write surfaces amendment (2026-07-19, fg-b0401)

> Amends: "Sharded fan-out — 2026-07-18" (above).

Response to fg-b0401 (parallelization enabler: docs/conventions.md sharded
into docs/conventions/*.md per-domain files, docs/conventions.md itself
reduced to a pure index). Every "the conventions append slot" / "conventions
writer" reference elsewhere in this file and in `skills/kernel/references/
parallel-dispatch.md` predates this amendment and described ONE monolithic
serialization point; this section is the canonical update to that guidance.

**Per-shard write surfaces replace the single conventions surface.** A task
that amends conventions content now declares its scope as the SPECIFIC
shard file(s) it touches — `docs/conventions/<shard>.md` — never the bare
`docs/conventions.md` path, which after this task carries no section bodies
to collide over (it is index-only: preamble, TOC, and the Shards manifest).
Two tasks amending DIFFERENT shard files have non-overlapping declared file
scope under the existing wave-eligibility rule ("Parallel dispatch (Waves
amendment, 2026-07-17)", above) and MAY be dispatched in the same
parallel-eligible batch. Two tasks amending the SAME shard file still
overlap in declared scope and still serialize — identical in spirit to the
pre-sharding single-file rule, just scoped down to the shard that actually
collides instead of the whole corpus.

**Index-file writes are their own tiny serialization unit.** A task whose
edit ONLY adds a TOC entry / Shards-manifest row for a new section (no shard
body change) declares `docs/conventions.md` itself as its scope; this is a
narrow, low-collision-probability surface (one line each), unchanged in
spirit from today's TOC-only edits, and does not block or get blocked by a
shard-body-only task naming a different file.

**No change to intra-task fan-out.** This amendment is about INTER-task wave
scope-overlap only; it does not alter the shard/dispatch/merge/verify
protocol above in any way — a single task sharded into N worker-slices via
that protocol is unaffected by which conventions shard file(s) it happens to
touch.

## Grud routing (goblin grunt) — 2026-07-18

Response to fg-a10802 (blocked-by fg-a10801, the sharded fan-out epic —
Grud is sharding's primary consumer). Defines the routing rule for a new
roster agent, `forge-grunt` (persona **Grud**), the boundary against
`forge-migrator` (Tern) so the two never overlap, and the roster/persona
registration this agent joins.

### Routing rule

WHEN the kernel faces fully-specified, zero-judgment bulk work — an exact
patch applied across many files, a literal string replace, a delete/move, a
reformat, a mechanical bulk edit — THE SYSTEM SHALL route it to
`forge-grunt`, always dispatched at **haiku/low**, with a minimal system
prompt and NO craft skills attached. Grud is non-skillful by design: cheap,
and structurally unable to over-think a mechanical job, because it has no
craft skill to over-think it WITH. When the work is large, the kernel shards
it ("Sharded fan-out — 2026-07-18", above) into a Grud swarm displayed as
"Grud #1..#N", each worker in worktree isolation — Grud is sharding's
primary consumer (fg-a10801).

### Grud vs Tern (`forge-migrator`) — the boundary, stated so they never overlap

The dividing line is judgment, not surface area:

- **Judgment about WHAT to change** — a semantic-preserving codemod, an
  AST-aware rename, a sweep where each site needs its own plausibility check
  — is `forge-migrator` (Tern), `agents/forge-migrator.md`.
- **Fully specified and only executed** — the contract already names every
  site and every replacement, with zero judgment left to apply — is
  `forge-grunt` (Grud).

Grud enforces this from its own side: if a contract handed to Grud requires
ANY judgment call, Grud REFUSES and bounces the whole task back to the
kernel unexecuted rather than guessing or silently narrowing scope
(`agents/forge-grunt.md`, Rules) — the safety valve that keeps the boundary
from blurring in practice, not just in this prose.

### Verification inheritance — tied to the Low-risk predicate, not a blanket exemption

Grud's output inherits the cheapest sufficient verification path
(gates-inline / the Low-risk verify sub-tier / one spot-check over the
merged result) — the efficiency lever the overhead audit (fg-a10209)
identified, verify being ~60% of spend. But this is the EXISTING **Low-risk
verification (standard sub-class) — 2026-07** predicate (above), applied to
Grud's output, never a blanket "mechanical → optional verify" exemption
invented for this persona — exactly the discipline already stated for shard
verification (above, "Skip per-shard EARS verify — tied to Low-risk
verification, not a blanket exemption"): **a mechanical-tier slug does not
get a looser bar.** A Grud diff that doesn't satisfy the Low-risk predicate
— touches `skills/`/`agents/`/`hooks/`/`workflows/`/`.forge/` protocol
files, or has an EARS clause without a passing pin, or is NORMATIVE prose —
gets a real verifier spawn at its task's normal tier, same as any other
worker's output. Gates-green ≠ acceptance-met holds for Grud exactly as it
holds for everything else.

### Roster / persona registration

`forge-grunt` joins the standing roster as its 20th agent, persona **Grud**.
Display label, per fg-a10213's `<Persona> (<role>)` format ("Dispatch
display labels" persona amendment, above, names the format; fg-a10213
supplies Grud's own mapping): **"Grud (grunt)"**; swarm-disambiguated as
**"Grud #1..#N (grunt)"** per that same task's #N rule. The canonical
slug→persona table lives in "Dispatch display labels — persona amendment
— 2026-07" (above); this section extends it — without altering any of that
table's existing rows — with:

| Slug | Persona |
|---|---|
| forge-grunt | Grud |

## Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)

> Amended by: "Dispatch-provenance flag — 2026-07-19 (fg-b0310, spec-b71f3a)"

NORMATIVE. Response to `.forge/specs/2026-07-19-universal-agent-dispatch-
lifecycle.md` (spec-b71f3a, "Universal dispatch (no exceptions)" AC1-AC3).
Ephemeral minting (`skills/agent-factory/SKILL.md`, "Fast path
(kernel-initiated ephemeral minting)"; "Ephemeral agent tier — 2026-07-19
(fg-b0301, spec-b71f3a)," above) is now cheap and non-blocking — no spawn,
no `AskUserQuestion` — so the anti-graveyard control this file used to
place on CREATION moves to PROMOTION and RETENTION instead (fg-b0305,
fg-b0306); creation itself is no longer gated by recurrence. This amends
two sections, explicitly, never silently:

- **"Prefer the agent factory over ad hoc generic dispatch — 2026-07-19"**
  (above): the "single genuinely one-off exploration... can stay generic"
  carve-out is withdrawn. A one-off exploration now mints an archive-tier
  ephemeral agent via the fast path INSTEAD of staying generic — never a
  raw `general-purpose`/`Explore`-style dispatch with no backing file.
  "Prefer the factory" becomes "never dispatch raw generic; mint instead."
- **"Report tasks (finder pattern) — 2026-07-17"** (above, itself amended
  by "UI+motion task splitting, empty-repo gates-pending, and finder
  dispatch — 2026-07-18"'s "Finder dispatch has no dedicated agentType"
  note): the finder route's generic dispatch is likewise replaced — a
  report task's finder now mints an archive-tier agent via the fast path
  before dispatch, never a raw generic dispatch with no backing file.
  `forge-worker`'s no-open-ended-exploration rule remains not implicated,
  since a finder dispatch is still never a `forge-worker` dispatch.

**Dispatch mechanics (AC1, AC5, AC9, Risk 6 ordering).** WHEN the kernel
dispatches an archive-tier agent — from either route above, or any other
fast-path mint — it uses the harness's generic/catch-all `subagent_type`
as transport, injecting the full `.forge/agents/archive/<name>.md` file's
content as the spawn contract: the persisted file authors the dispatch,
never an improvised prompt with no name and no file. File existence is a
precondition of dispatch, not a follow-up (`skills/kernel/SKILL.md`,
ROUTE + DISPATCH, "Mint-before-dispatch" / "Archive-tier" transport rule)
— cited here rather than restated.

**Why now, not before.** The prior prefer/recurrence-gated wording assumed
minting was expensive (a spawn, an `AskUserQuestion`, human review) — worth
reserving for genuinely recurring shapes. The fast path (fg-b0302) made
minting mechanical and inline, so the cost calculus flipped: the
anti-graveyard control that used to gate CREATION now gates PROMOTION
(usage-based, human-approved, fg-b0305) and RETENTION (90-day/below-
threshold pruning, fg-b0306) instead — never creation (spec-b71f3a AC3).

## Dispatch-provenance flag — 2026-07-19 (fg-b0310, spec-b71f3a)

> Amends: "Universal Forge-agent dispatch — 2026-07-19 (fg-b0303, spec-b71f3a)" (above).

Response to `.forge/specs/2026-07-19-universal-agent-dispatch-lifecycle.md`
(spec-b71f3a), "Install-time ecosystem enforcement," second bullet. Adds
`hooks/scripts/agent-provenance-flag.sh`, a fail-silent, non-blocking
`PreToolUse` hook on the same `Task|Agent` matcher `budget-guard.sh` uses
(`hooks/hooks.json`).

**What it checks.** On every Task/Agent dispatch in a repo with `.forge/`
present, the hook resolves the dispatch's `subagent_type` against the
forge-backed categories "Universal Forge-agent dispatch — 2026-07-19"
(above) already establishes: a roster agent (`agents/<name>.md` under
`CLAUDE_PLUGIN_ROOT`, referenced with the `forge:` prefix convention — e.g.
`forge:forge-worker` resolves to `agents/forge-worker.md`), a project-local
agent (`.forge/agents/<name>.md`, or its `.claude/agents/<name>.md`
mirror), or the harness's generic/catch-all `subagent_type`
(`general-purpose` / `Explore`) — the documented archive-tier transport
(above, "Dispatch mechanics").

**What's logged, and where.** A dispatch whose `subagent_type` is NAMED
(i.e. not the generic/catch-all transport) and resolves to none of the
above is flagged: the hook appends one line — UTC timestamp plus the
`subagent_type` — to `.forge/telemetry/dispatch-provenance.log` (the
directory is created on the first flag) for the session report to
surface. Nothing else is written, and the dispatch itself is never
touched.

**Never denies.** Unlike `budget-guard.sh` — the ONE documented exception
to the fail-silent-hooks doctrine (`hooks/hooks.json` description) — this
hook never returns a deny decision; it always exits 0. `budget-guard.sh`
remains the only hook allowed to block a dispatch.

**Fail-silent.** No `.forge/` present -> silent. Unparseable stdin, a
missing `subagent_type`, or any other error along the way -> silent, exit
0, and the dispatch proceeds unaffected (spec-b71f3a, "Install-time
ecosystem enforcement," second bullet; fail-silent doctrine).

**Generic-transport limitation, stated rather than hidden.** A generic
`subagent_type` is legitimate archive-tier transport (above), but the
invariant that actually matters — that the injected prompt really is an
archive-tier FILE's content, not an improvised one — lives in the prompt
body, which this hook cannot see or verify from `tool_input`'s
`subagent_type` field alone. Generic types are therefore never flagged;
this is a documented limit of the hook's vantage point, not an oversight.

