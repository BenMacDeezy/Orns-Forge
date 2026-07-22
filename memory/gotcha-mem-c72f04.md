---
name: mem-c72f04
type: gotcha
description: Parallel same-tree agents + revert-red verification collide — verifiers must NEVER git stash/checkout/restore a shared working tree (it clobbers sibling workers' in-progress files); prove revert-red non-destructively via `git show HEAD:<file>` in a scratch harness. The real fix is worktree isolation per parallel mutating agent (2026-07-18)
created: 2026-07-18T15:45:00Z
updated: 2026-07-18T15:45:00Z
agents: [forge-verifier, forge-worker]
superseded-by: null
schema-version: 1
---

In the 2026-07-18 inquest-fix wave, 5–6 workers built fixes concurrently on
one shared working tree and their verifiers then ran revert-red proofs. Two
failure modes appeared repeatedly: (1) a verifier's `git stash`/`checkout`
to test the pre-fix version would have clobbered a sibling worker's
uncommitted file (caught and redirected mid-flight); (2) full `pytest tools/`
runs transiently caught sibling tasks' in-progress test files as failures,
forcing every worker/verifier to reason about attribution via
`git diff --stat -- <own files>`. Net: real correctness risk plus wasted
reasoning on phantom failures.

Rules: (1) a verifier proving Constitution rule 1 (revert-red) on a shared
tree MUST use a non-destructive method — `git show HEAD:<path>` into a scratchpad copy,
load it alongside the current module via importlib, run the defect scenario
against both — and NEVER `git stash`/`git checkout`/
`git restore`/`sed -i` a tracked file; state the method used. (2) A verifier
of one task on a shared multi-worker tree scopes its gate to its OWN test
file + validate_all, not the full `pytest tools/` suite, and confirms scope
via `git diff --stat -- <own files>`; treat any unrelated red as sibling
churn, attribute it away by diff, do not fail the task for it. (3) The
STRUCTURAL fix is worktree isolation per parallel mutating agent (Agent tool
`isolation: worktree`, or the queued sharded-fan-out capability fg-a10801) —
prefer it whenever >1 agent mutates files at once; the non-destructive
verify discipline above is the mitigation while a shared tree is still in
use. See also the char-ceiling compression trap [[mem-e4a917]] and the
Stop-hook debounce fact [[mem-9b31c5]].
