---
name: worktree-discipline
description: The worker-side contract for operating inside a kernel-owned git worktree — stay inside the assigned path, never touch git state yourself, leave the tree mergeable, and report the diff precisely. Use whenever a spawn contract dispatches you into an isolated worktree (Agent tool isolation:"worktree"), or before running any git command inside one.
---

# Worktree discipline

You were dispatched into a worktree the kernel or harness created for you.
This skill is the worker half of that contract only — the integrator half
(merge order, gate re-runs, bisection) is cited under "Integrator side"
below, never restated.

## Stay inside the assigned path

Work exclusively inside the worktree path named in your spawn contract. Never
touch the canonical checkout, and never touch a sibling worktree — not even
to read a file for context. If your contract doesn't name a path, stop and
report the gap rather than guessing which tree you're in.

## Detect existing isolation before assuming a fresh tree
<!-- adapted from superpowers 6.1.1 using-git-worktrees -->
Don't assume you need to create anything — you were placed here already.
Check the tree you're standing in before acting on it:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```

`GIT_DIR != GIT_COMMON` confirms you're in a linked worktree — the expected
state; don't create another one on top of it. That same inequality also
holds inside a git submodule, so guard it before trusting the conclusion:
if `git rev-parse --show-superproject-working-tree` returns a path, you're
in a submodule, not a worktree — treat it as a normal repo and stop, this
skill's isolation guarantees don't hold there.

## Never touch git state yourself

- Never commit, push, branch-switch, or run any `git worktree` command —
  those are integrator/kernel-owned moves (INTEGRATE, per the
  parallel-dispatch reference above).
- Run every gate command your contract lists, inside the worktree, and
  report their real output.
- Leave the tree mergeable when you stop: no untracked junk outside your
  declared file scope, no partial edits, nothing half-applied that isn't
  meant to ship.
- Report the diff surface precisely — every file you touched, and why — so
  the integrator can merge without re-deriving your change from the tree.
- On any git-state anomaly — a detached HEAD you didn't expect, a lock file
  you can't acquire — STOP and report it. Never repair git state yourself;
  that's a call for whoever owns the tree, not a worker-side fix.

## Cleanup is provenance-gated
<!-- adapted from superpowers 6.1.1 finishing-a-development-branch -->
Whoever CREATED the worktree owns its cleanup. The kernel or harness made
the workspace you're standing in, so you never remove it yourself — not on
success, not on failure, not "to be tidy." Leave it in place for its
creator to tear down.

## Report discipline
<!-- adapted from superpowers 6.1.1 subagent-driven-development -->
The integrator reads your final report as an unverified claim about the
code, not as settled fact — write it that way: a precise diff surface, real
gate output, no advocacy for your own work. If your work hands off to a
downstream reviewer, never write that reviewer's prompt so it pre-judges
severity or tells it what not to flag — a prompt containing "do not flag X"
or "at most Minor" has decided the answer before the review starts.

## Compaction warning
<!-- adapted from superpowers 6.1.1 subagent-driven-development -->
Conversation memory does not survive compaction. The task file's Attempt
log — not what you remember doing — is the resumable record. Log your
attempt before you stop, not after deciding whether you might continue: a
session that compacts mid-task and finds nothing logged has to reconstruct
where it left off from nothing.

## Integrator side — cited, not restated

Merge order, gate re-runs, and bisection on a broken merge belong to the
kernel: `skills/kernel/references/parallel-dispatch.md` owns that protocol
in full.

## Forbidden actions

- Never self-merge to any base branch, and never delete branches —
  INTEGRATE is kernel-owned (Hard Rule 4).
- Never dispatch a raw generic subagent — the universal-dispatch rule
  requires minting a proper agent first, always.
- Never keep progress or state in any store outside `.forge/` — no
  competing ledgers alongside the queue.
