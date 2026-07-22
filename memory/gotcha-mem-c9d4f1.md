---
name: mem-c9d4f1
description: Worktree-isolated parallel dispatch pollutes test runners whose default excludes stop at node_modules — worktree checkouts under .claude/worktrees/ get collected as phantom suites; exclude the worktree dir in runner config before the first parallel batch, and sanity-check batch-merge gate counts against expected totals
type: gotcha
created: 2026-07-18T12:50:00Z
updated: 2026-07-18T12:50:00Z
superseded-by: null
schema-version: 1
agents: forge-verifier, forge-worker
---

Promoted from a project fact, vitest-based repo. Live symptom: merged-batch
gate run reported 1003 tests where 354 were expected, with 4 failures —
all phantom collections of stale test copies inside
`.claude/worktrees/<agent>/` checkouts (vitest's default excludes stop
at node_modules/.git; most runners behave the same).

How to apply, any repo, any runner:
- Before the FIRST worktree-parallel batch, add the worktree root to
  the test runner's exclude config (vitest: `test.exclude:
  ["**/node_modules/**", "**/.claude/**"]`; jest: `testPathIgnorePatterns`).
- At batch INTEGRATE, sanity-check the merged gate's test count against
  baseline + sum of branch additions — a count far above expectation
  means collection pollution, not new coverage.
- Windows/OneDrive: worktree dirs can stay Permission-denied-locked
  after `git worktree remove --force`; prune git metadata, retry the
  directory delete later, and rely on the runner exclusion meanwhile.
