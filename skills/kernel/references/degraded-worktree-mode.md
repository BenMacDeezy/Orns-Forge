# No-worktree degraded mode (reference)

Loaded by `skills/kernel/SKILL.md` SYNC (the worktree-availability probe)
and GATE/DISPATCH when the probe reports worktrees are unavailable.
NORMATIVE. This file is the canonical statement of what "worktrees are
broken here" does to dispatch — it does NOT introduce a new sandbox or a
new merge path; it states that the EXISTING sequential, in-place worker
path (the one parallel-dispatch.md says "needs none of this" worktree
machinery) is what BOTH Claude and external (codex) mutating workers run
in when isolation is unavailable. Origin: 2026-07-24, owner-directed —
a live OneDrive/Windows repo where `git worktree add` produces empty or
un-synced trees, so parallel batching and any worktree-scoped dispatch
cannot be trusted.

## Worktree-availability probe (SYNC)

Once per session, at SYNC, before the first GATE, the kernel probes
whether worktrees actually work in THIS repo — a created worktree on a
OneDrive/Dropbox/network-synced or symlink-hostile tree can return
exit 0 yet materialize an empty or partially-synced directory, so an
exit-code check alone is not sufficient.

Probe: create a throwaway worktree at a temp path, assert it both
succeeded AND materialized a non-empty tree containing a known tracked
file, then remove it.

```
wt=$(mktemp -d)/probe
git worktree add -q --detach "$wt" HEAD 2>/dev/null \
  && [ -e "$wt/.git" ] && [ -n "$(ls -A "$wt" 2>/dev/null)" ]
# success = both the add succeeded and the tree is really there
git worktree remove --force "$wt" 2>/dev/null; git worktree prune 2>/dev/null
```

- **Probe passes** → normal mode. Parallel eligibility, batching, sharding,
  and worktree-scoped provider dispatch all work as documented elsewhere.
- **Probe fails** (non-zero, empty tree, or missing sentinel file) →
  DEGRADED MODE for the whole session. Record it verbatim in the run
  charter / session report: `worktree mode: DEGRADED — <one-line probe
  failure> — running sequential + in-place; parallel batching and
  worktree-scoped dispatch disabled this session`. This is a stated
  environment fact, not a silent fallback.

The probe is cheap and runs once; do not re-probe per task. A human may
also force degraded mode via forge.md (`worktrees: off`) to skip the
probe entirely on a repo known to be worktree-hostile.

## What degraded mode changes

**1. No parallel batches, no shards.** GATE's wave-level parallel-
eligibility test and the shard-eligibility predicate both FAIL CLOSED in
degraded mode: with no trustworthy worktree isolation, two mutating
workers must never share the one working tree. Every task runs
sequentially, one at a time, in the main tree. Parallel-first dispatch
(the default when worktrees work) is suspended for the session and the
charter says so. This is the ONE environment condition that overrides
parallel-first — and it overrides it because the safety precondition
(isolation) is absent, not as a preference.

**2. Mutating workers run in-place — Claude AND codex, identically.** A
sequential worker (either kind) is dispatched against the main working
tree directly, exactly as an in-harness Claude `forge-worker` already is
on the sequential path. For a codex worker this means:
- Launch `codex exec ... --sandbox workspace-write` with its working
  directory set to the repo root. codex's `workspace-write` sandbox is a
  codex feature that constrains writes to the launch directory — it is
  NOT a git worktree and does not require one. In the main tree it gives
  the same write-confinement it gives in a worktree.
- Skill materialization (provider-judges.md §8) writes to
  `.forge-dispatch/skills/<name>/` at the repo root instead of inside a
  worktree. The §8 INTEGRATE-time exclusion is UNCHANGED and now
  load-bearing: the kernel MUST exclude `.forge-dispatch/` from the diff
  it stages at INTEGRATE, so the scratch skills never get committed. In
  worktree mode the worktree threw this away for free; in-place, the
  kernel does it explicitly.
- One codex at a time is already mandatory (craft memory
  `codex-dispatch-mechanics`: concurrent `codex exec` processes contend
  on shared `~/.codex` state and can hang forever). Degraded mode's
  sequential-only rule and codex's own serialization requirement are the
  same constraint, so nothing is lost by dropping worktrees here.

**3. INTEGRATE is in-place, kernel-owned, per single task.** There is no
worktree branch to merge. The worker (Claude or codex) has written its
diff into the main working tree; the kernel VERIFIES that working-tree
diff (see verify routing below), and on PASS stages the task's files
(excluding `.forge-dispatch/` and `.forge/`) and commits — the ordinary
single-task INTEGRATE, not the batch/shard merge path. Hard Rule 4 holds
unchanged: the worker never touches `.forge/`; all `.forge/` writes are
kernel-only.

**4. Bounce reverts in-place.** With a worktree, a bounced task's bad diff
is discarded with the worktree for free. In-place, the bad diff sits in
the main tree, so the kernel MUST revert it before the next task claims
that tree: `git stash push --include-untracked -- <the task's scope
paths>` then drop the stash, or `git checkout -- <paths>` plus removing
any new untracked files the task created. Never leave a bounced task's
partial diff in the tree for the next sequential worker to build on top
of — that is the in-place equivalent of the orphaned-worktree hazard, and
it is the kernel's job to clean, not the worker's.

## Verify routing is builder-agnostic (the point of this whole mode)

The verifier is chosen by the TASK's acceptance criteria, never by who
built it. A task whose criteria are primarily rendered UI or motion
routes to `forge-ui-verifier` (Playwright visual gate) whether the diff
was written by a Claude worker, a codex worker, or the kernel inline —
exactly as SKILL.md VERIFY's "Visual gate routing" already specifies.
This is what makes **codex-build + Claude-visual-verify** a first-class
combination rather than a contradiction: the builder never needed to see
the rendered output; the verifier does, and the verifier is always the
harness-native one for the task's surface. The equal-or-higher-model-tier
rule on the verifier is unchanged and applies to the verifier's tier
relative to the BUILDER's tier, cross-provider included (provider-judges.md
§7, §11).
