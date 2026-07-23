# Parallel-batch dispatch and integrate (reference)

Loaded by `skills/kernel/SKILL.md` ROUTE+DISPATCH and INTEGRATE when GATE's
inline "Parallel eligibility (wave-level)" test found an eligible batch
(≥2 `parallel-safe: true` tasks, no `blocked-by` edges among them,
non-overlapping declared file scopes); `max-parallel-tasks` caps simultaneous
spawns only (sliding window), never batch eligibility.
NORMATIVE — moved verbatim from those two steps, not summarized. A wave
with no eligible batch never reads this file; the sequential path (one
task at a time) is unaffected and needs none of this.

## ROUTE + DISPATCH — Parallel dispatch

When a batch is eligible:
- **Claim the whole batch first.** Before dispatching any worker, claim every
  batch task not already claimed by this session — one atomic file-write
  each, re-read-before-write race guard as in `forge:queue` Claim / release.
  A claim that fails the race guard drops that task from the batch.
- **Sliding-window dispatch.** `max-parallel-tasks` (forge.md Queue section,
  default 3) is a concurrency window on simultaneous spawns, not a hard cap
  on how many eligible tasks a session may eventually run. When the batch has
  more eligible tasks than fit in the window at once, dispatch up to
  `max-parallel-tasks` workers immediately, then dispatch each surplus task's
  worker the moment an in-flight worker's slot frees (worker completes or
  bounces out of the in-flight set) — the window slides rather than the
  kernel dispatching one fixed batch and stopping (`docs/conventions.md`,
  "Latency rules — ship-review overlap, mechanical bounces, batch gates,
  sliding-window dispatch — 2026-07", rule 4).
- **Dispatch each task as its own worker spawn** with git worktree isolation
  (Agent tool `isolation: "worktree"`), each with a normal, complete spawn
  contract. Each dispatch increments the session dispatch count.
- **Hard Rule 4 holds inside worktrees:** workers still never touch `.forge/`.
  All `.forge/` writes are kernel-only, on the main branch, never inside a
  worktree.
- **One worker fails or blocks:** the others proceed; the failed task bounces
  normally (VERIFY/INTEGRATE bounce rules) — a batch is not an all-or-nothing
  unit.
- **Session dies mid-batch:** the worktrees are orphaned; the next session's
  SYNC stale-worktree sweep flags them for human cleanup (never auto-deleted)
  and claim recovery handles the stale claims.

## INTEGRATE — Parallel batch

**Parallel batch — INTEGRATE is strictly sequential and kernel-owned.**
Merge every finished worktree back into main one at a time, in completion
order: verify (verdict in hand) → merge the worktree branch to main,
conflict-checked per merge. Never merge two worktrees concurrently. Once
all worktrees in the batch are merged, run the gate suite ONCE against the
fully-merged result — not once per task — then commit (single-gate batch
INTEGRATE; `docs/conventions.md`, "Latency rules — ship-review overlap,
mechanical bounces, batch gates, sliding-window dispatch — 2026-07",
rule 3).
- **Merge conflict:** bounce that task to `blocked` with the conflict noted
  in its Attempt log — do not resolve speculatively. Remaining batch members
  continue integrating.
- **Merged-result gates pass:** every task in the batch commits together.
- **Merged-result gates fail:** the merged-gates run remains authoritative
  over any per-worktree gate pass, unchanged from the existing rule — the
  kernel bisects by re-running gates per-merge in the same completion order
  used to build the merge, to isolate which task's merge broke the batch.
  Bisection is a failure-path-only cost, never the common case.
- All queue-state writes for the batch happen here, on main, by the kernel
  (Hard Rule 4).

## Shard expansion (fg-a10814)

Response to fg-a10801 (T4a of the decomposition — the MECHANICAL dispatch-
expansion half; scope is dispatch/expansion only — merge, per-shard verify,
bisect, and shard-INTEGRATE atomicity are fg-a10815/T4b, not this section).
Extends the ROUTE + DISPATCH and INTEGRATE machinery above for **intra-task**
shard fan-out, per "Sharded fan-out — 2026-07-18" (`docs/conventions.md`,
the canonical protocol this section implements the dispatch half of) — a
shardable task is a SYNTHETIC parallel batch, expanded through the SAME
mechanism above, not a second one.

**Expansion.** When GATE finds a task shard-eligible ("Shard-eligibility
predicate — separate from wave eligibility," `docs/conventions.md`), the
kernel expands that ONE task into N ephemeral shard-jobs through the
EXISTING parallel-wave machinery above:
- Each shard-job is an **identical-slug worker** — the same agent slug the
  task would route to un-sharded, spawned N times.
- Every shard-job dispatches with Agent-tool `isolation: "worktree"` —
  **MANDATORY**, no exception ("Worktree-per-shard isolation — MANDATORY,"
  `docs/conventions.md`): parallel identical-slug workers must never share a
  mutating tree.
- All N shard-jobs share the ONE sliding-window concurrency cap
  (`max-parallel-tasks`) that governs every other dispatch above — no
  second, shard-private window. See "Nesting guardrail," below, for how
  that one window is shared when the task is also a wave member.

The splitter is `tools/shard_task.py` (fg-a10812),
`split_shards(shard_by, max_shards, shard_key)`. Its manifest — confirmed
against the shipped module — is a list of dicts:

```
{"index": <1-based int>, "shard_by": "files"|"items"|"ranges", "items": [...]}
```

These three keys — `index`, `shard_by`, `items` — are PINNED here as the
dispatch contract: DISPATCH reads `index` to number the shard-job (the
`#1..#N` display, below, is taken directly from it — no separate labeling
pass), `shard_by` to record provenance, `items` as that shard-job's disjoint
slice of work. `tools/test_doc_pins.py::TestFgA10814ShardDispatchPins`
behaviorally asserts these are the real keys the shipped module returns —
this task is the first consumer of the splitter, so this is where the keys
become contract rather than a docstring claim.

**Nesting guardrail — wave siblings + shards share ONE window (OQ1).** When
a shardable task is also an inter-task wave member ("Nesting (a shardable
task that is also a wave member) — OQ1 resolution," `docs/conventions.md`),
DISPATCH counts wave siblings AND all shards of every nested task against
the single sliding-window cap above — there is no second, shard-private
window. To keep one task's shard fan-out from starving its wave siblings of
a dispatch slot, DISPATCH reserves **at least 1 slot per distinct wave
task** in the batch before filling remaining slots with additional
shard-jobs: every distinct wave task gets at least one in-flight worker
(itself, or its first shard) before a second shard-job of any nested task
claims a slot. This is the OQ1 guardrail from fg-a10801's human decision,
reconciled against the refuter's execution-safety argument (fg-a10801,
"Human decisions" and "Refuter verdict + kernel reconciliation") — schema
and loop support nesting from day one, but the shard-eligibility predicate
stays conservative about actually choosing it ("allowed ≠ always-chosen").

**Attempt-log recording — kernel-owned sequential writes, one task file.**
Every shard-job's outcome is recorded in the ONE originating task's Attempt
log — N shard-jobs map to one task file, never N task files. Writes are
kernel-owned and strictly **SEQUENTIAL** on main, exactly like every other
`.forge/` write (Hard Rule 4): the kernel serializes the N shard-job results
into that one Attempt log one at a time, in completion order — **never
concurrent writers**, and never a shard worker writing its own line (shard
workers never touch `.forge/`, same as any worktree worker above).

**Display — `"<Persona> #1..#N (<role>)"`.** A sharded swarm's dispatch
label leads with the persona (`docs/conventions.md`, "Dispatch display
labels — persona amendment — 2026-07"), then the instance suffix `#1..#N`
taken directly from the slice manifest's 1-based `index`, then the task's
role in parens. The slug itself stays unchanged across all N shard-jobs;
workers are disambiguated by **instance number, never by task id** — all N
shard-jobs share the one task's `fg-xxxx`, so the id can't do the
disambiguating work the instance number does (per fg-a10213, "Dispatch
display labels — 2026-07").

**Dead-session shard worktrees.** Orphaned shard worktrees left behind by a
dead session need **no new recovery path**: the EXISTING SYNC
stale-worktree sweep — the same one that already flags orphaned wave
worktrees ("Session dies mid-batch," above; `skills/kernel/SKILL.md`
SYNC) — flags them for human cleanup, never auto-deleted. A shard worktree
is, structurally, the same git-worktree artifact a wave-batch worker
leaves behind; the sweep does not need to distinguish the two.

**Shards complete → see merge/verify contract in fg-a10815 (T4b).** Merge
order, single-gate batch verify vs. per-shard verify, bisect-on-failure, and
shard-INTEGRATE's ATOMIC-for-the-task semantics (inverting parallel-batch
INTEGRATE's not-all-or-nothing rule above) are fg-a10815's scope, not this
section's.

## Shard merge, verify, bisect, atomicity (fg-a10815)

Response to fg-a10801 (T4b of the decomposition — the JUDGMENT-heavy
merge/verify/bisect/atomicity half; complements the fg-a10814 section
above, which covers dispatch/expansion only). Canonical protocol:
`docs/conventions.md`, "Sharded fan-out — 2026-07-18" (subsections "Skip
per-shard EARS verify — tied to Low-risk verification, not a blanket
exemption" and "Shard INTEGRATE is ATOMIC for the task — inverts
parallel-batch INTEGRATE"); this section is the kernel-reference statement
of that canon, not a second source of truth for it. Refuter revisions
R-D4a, R-D4b, and R-D7 (fg-a10801, "Refuter verdict + kernel
reconciliation") are all covered below.

### Merge — conflict CHECK, never speculative resolve

Disjoint shard outputs merge exactly like a parallel-batch merge above
("INTEGRATE — Parallel batch," this file): kernel-owned, strictly
sequential, one worktree at a time, merge-then-gate. A *surprise* textual
conflict — scope overlap the splitter missed — bounces that shard to
`blocked` with the conflict noted in its Attempt log; the kernel NEVER
resolves it speculatively. This is a **verbatim reuse** of the existing
wave conflict-bounce rule above — "**Merge conflict:** bounce that task to
`blocked` with the conflict noted in its Attempt log — do not resolve
speculatively" — cited, not restated as a shard-specific variant: the same
sentence, applied at shard grain.

### Verify model — tied to the Low-risk predicate, never a blanket exemption (R-D4a)

"Skip per-shard EARS verify" is permitted **ONLY** when a shard's diff
would itself fully satisfy the EXISTING **Low-risk verification (standard
sub-class) — 2026-07** predicate (`docs/conventions.md`, above) in full —
paraphrased in this task's own acceptance criteria as "every EARS clause
pin-covered, no protocol-file touch, gates cover the change," and stated
in the predicate's own words as "Every EARS clause is covered by a passing
pin or regression test," the task "touches NONE of `skills/`, `agents/`,
`hooks/`, `workflows/`, or `.forge/` protocol files," and the diff is
"docs/config-only, zero runtime-behavior change." This is **NEVER** a
blanket "mechanical work → optional verify" rule — mechanical-looking
work is not automatically low-risk; it must clear the SAME conjunctive
qualification bar any other standard-tier task clears, at shard grain.

**Gates-green ≠ acceptance-met — the canonical counterexample.** A shard
tasked with a mechanical rename `X` → `Y` that instead *deletes* `X` (and
touches nothing that references it) passes every gate green — nothing in
the merged tree references the deleted symbol, so nothing fails — while
the EARS criterion ("rename X to Y") is unmet. Gates alone cannot catch
this; only an EARS-clause verifier reading the criterion against the diff
can.

**When the predicate is not fully satisfied**, an EARS-clause verifier
runs: **per-shard** for disjoint outputs whose risk can be judged slice by
slice, or **once over the merged result** when the shard-set's acceptance
criteria only make sense read together, spanning slices. Grud/grunt
shards **inherit this rule explicitly** — a mechanical-tier slug does not
get a looser verification bar than a standard-tier one; "mechanical slug"
and "Low-risk verification" are independent axes, and only the latter ever
licenses a skip.

**Reconciling fg-a10801 EARS clause 2.** The parent clause reads
"per-shard for disjoint outputs, or once over the merged result" — read
alone that looks like a free choice. It is not: those two options are
**modes selected by the Low-risk predicate above, not a free choice**.
Concretely: disjoint-output shard-sets **MAY** verify once-over-merged
**ONLY** under the Low-risk predicate — fully satisfied, the reduced
protocol (including the once-over-merged shape) may apply; when the
predicate is not fully satisfied, per-shard/EARS verification applies
instead. The predicate picks the mode; the worker and the kernel do not.

### Bisect + coupling misattribution (R-D4b)

WHEN a merged shard-set fails gates due to **cross-slice coupling** — two
disjoint-file slices coupled through a shared signature the splitter
could not see (a build-graph dependency, not a text overlap) — the
kernel's ordinary bisect (re-running gates per-merge in completion order,
"INTEGRATE — Parallel batch," above) blames the **last-merged slice**,
because that is the merge step at which the gate suite first goes red.
Re-dispatching that slice alone, with the same scope, **reproduces the
failure** — the slice itself was never wrong; the fault is the
*relationship* between slices, not any one slice's content. Therefore:
after that slice's **2nd failure**, the kernel does NOT retry a 3rd time —
the **WHOLE task blocks**, with a note that the failure is
**coupling-shaped, not slice-local**, pointing the human at the **slice
SET**, not the one slice bisect happened to blame.

**Why this composes with the eligibility restriction.** This is exactly
the failure mode "Shard-eligibility predicate" (`docs/conventions.md`,
above) restricts `shard-by: files` against: a build-graph-coupled file set
is **textually-clean-but-semantically-broken** when split by file — each
slice's diff looks correct in isolation, the per-shard scope is genuinely
disjoint, and the merge itself is conflict-free, so nothing before gates
run would have flagged it. The eligibility restriction (per-file-local
ops only) and this bisect rule are the same hazard handled twice:
eligibility tries to keep the hazard from ever being dispatched; this rule
is what fires on the occasions it slips through anyway — one retry is the
resource bound, then it becomes the human's problem, framed correctly
(the slice SET, not a scapegoat slice).

### Atomicity — shard INTEGRATE inverts parallel-batch INTEGRATE (R-D7)

Parallel-batch INTEGRATE (above) is explicit: "a batch is not an
all-or-nothing unit" — one wave task failing does not stop the rest.
**Shard INTEGRATE inverts that rule.** Because N shard-jobs are slices of
**one** task, not N independent tasks, INTEGRATE is **ATOMIC for the
task**: the whole task is done, or the whole task is blocked — there is
no "drop the broken slice, integrate the rest" option, because the slices
are not independent deliverables; they are one deliverable in pieces. This
inversion is stated **explicitly** because reusing the batch-INTEGRATE
mental model here would be silently wrong in the opposite direction it
was right for batches.

This is also why the atomicity difference needs its **own** kernel
INTEGRATE stub, not a reuse of the batch-INTEGRATE stub GATE and DISPATCH
already share: the kernel's INTEGRATE stub for shards (fg-a10816) **MUST
cite THIS section**, not the batch-INTEGRATE stub above, wherever it
handles a shard-bearing task — citing the batch stub for a shard-set would
silently reintroduce "not all-or-nothing" where "ATOMIC" is required.

## Build-ahead pipelining (fg-a10901) — NORMATIVE

WHEN a builder returns and GATE permits another task (DAG + window + budget),
dispatch that build IMMEDIATELY — do not hold the slot for the returning
task's verifier verdict. Verification gates INTEGRATE, never the next
dispatch (`docs/conventions.md`, "Verification economics — 2026-07-18").

Mechanics:
- Verifier spawns are read-only and do NOT consume a build window slot;
  the ≥1 reserved-slot rule of "Shard expansion" is unchanged.
- INTEGRATE still consumes verdicts sequentially; commits remain ordered.
- A verify FAIL that lands after a dependent build started: bounce the
  failed task normally AND pass the bounce context to the dependent build's
  verifier (rework exposure is judged, not assumed clean).
- Sharded batches keep the ATOMIC batch INTEGRATE (fg-a10815) — pipelining
  never ships a partial shard set.

## Per-shard write surfaces (fg-b0401)

`docs/conventions.md` was split into per-domain shards under
`docs/conventions/*.md` (`docs/conventions.md`, "Sharded fan-out — per-shard
write surfaces amendment (2026-07-19, fg-b0401)"); the root file is now
index-only (preamble, TOC, Shards manifest) and carries no section bodies to
collide over. Wave-eligibility scope-overlap checks above ("declared file
scope with no overlap between members") now resolve against the SPECIFIC
`docs/conventions/<shard>.md` file(s) a task's Execution plan names, never
the bare `docs/conventions.md` path. Two tasks naming DIFFERENT shard files
have non-overlapping scope and MAY batch together; two tasks naming the SAME
shard file still overlap and still serialize — this replaces every prior
"the conventions append slot" reference with a per-shard equivalent, scoped
down from the whole corpus to the one file that actually collides. A task
touching only the index (a TOC/manifest-only edit, no shard body) declares
`docs/conventions.md` itself as its scope, a narrow one-line-per-entry
surface unaffected by shard-body edits elsewhere.
