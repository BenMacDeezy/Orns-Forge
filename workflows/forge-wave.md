# forge-wave — canonical Workflow script for a parallel-eligible batch

Reference doc for the kernel's Executor (`skills/kernel/SKILL.md`, "Executor").
This is NOT executed from this file — the kernel writes the script into the
Workflow tool call, using this as the canonical shape. It runs only for a
batch that already passed the GATE parallel-eligibility test; everything the
sequential path checks is checked here too, just executed deterministically.

Contract with the kernel:

- **Input** `args`: `{ tasks: [{id, contractText, model, effort}...],
  verifierModel, verifierEffort, constitutionRules, startedAt }` — contracts
  are fully filled spawn contracts (`spawn-contract-template.md`), routing
  already decided by ROUTE. `constitutionRules` is the numbered rule text
  from `.forge/constitution.md` (string) when it exists, or `null` when it
  doesn't — the same input the sequential VERIFY step passes to the verifier
  (`forge:kernel`, VERIFY, "Constitution (Phase 3)"), threaded through
  unchanged so a parallel-dispatched task gets the identical check. `startedAt`
  is passed in because scripts must be deterministic.
- **Output**: per-task `{id, workerReport, verdict, runInfo}` — results only.
  The script never merges worktrees, never commits, never touches `.forge/`;
  the kernel INTEGRATEs sequentially on main (Hard Rule 4).
- The kernel records the workflow `runId` in each batch task's Attempt log at
  dispatch; a dead run is resumed via `resumeFromRunId` (completed `agent()`
  calls return cached) rather than re-dispatched.

```js
// forge-wave: implement-then-verify each batch task, in parallel across tasks.
// NOTE the script shape: `export const meta` followed directly by the script
// BODY (no wrapper function, no default export). The body runs in an async
// context where `args`, `budget`, `agent`, `pipeline`, `parallel`, `log`,
// and `phase` are globals; `await` and a bare `return` work directly.
export const meta = {
  name: 'forge-wave',
  description: 'One parallel-eligible Forge batch: worker (worktree) → verifier per task',
  phases: [{ title: 'Implement' }, { title: 'Verify' }],  // objects, not strings
};

// args.tasks arrive with routing DECIDED — model+effort chosen by the
// kernel's ROUTE table. The script never picks a model itself: Hard Rule 1
// (explicit routing always) means every agent() call below passes an
// explicit model, and effort rides in the contract's ROUTING line.
const { tasks, verifierModel, verifierEffort, constitutionRules } = args;

  // pipeline(items, ...stages): each task flows implement → verify, tasks
  // run in parallel with each other. This IS the GATE's parallel dispatch —
  // eligibility (parallel-safe, no dep edges, disjoint scopes, batch cap)
  // was already proven by the kernel before this script was dispatched.
const results = await pipeline(
  tasks,

  // Stage 1 — implement. isolation: 'worktree' gives each worker its own
  // git worktree, exactly like the sequential parallel-dispatch path.
  // WHY worktree: disjoint file scopes were verified at GATE, but
  // isolation makes a scope violation harmless instead of corrupting main.
  async (task) => {
    // WHY budget guard: session-token-cap is advisory, but when a target
    // is set, stop dispatching NEW work rather than blow through it.
    // Tasks already dispatched still finish (same as max-tasks-per-session
    // semantics: stop after in-flight work integrates). With no target set,
    // budget.remaining() is Infinity, so this guard is a no-op.
    if (budget.total && budget.remaining() <= 0) {
      return { id: task.id, skipped: 'budget exhausted before dispatch' };
    }
    const workerReport = await agent(task.contractText, {
      label: `worker:${task.id}`,
      phase: 'Implement',                // must match a meta.phases title
      agentType: 'forge:forge-worker',   // the real roster agent
      model: task.model,                  // explicit — never inherited
      isolation: 'worktree',
      // effort is in contractText's ROUTING line (no tool param exists).
    });
    return { id: task.id, workerReport };
  },

  // Stage 2 — verify. Hard Rule 3: the worker never verifies its own
  // work; a separate forge-verifier judges the diff, at equal-or-higher
  // tier (the kernel chose verifierModel under that rule).
  // Stage signature: (prevResult, originalItem, index) — the original task
  // arrives as the SECOND parameter, no destructuring wrapper.
  async (prev, task) => {
    if (prev.skipped) return prev;
    // WHY the conditional clause: constitutionRules is null when
    // .forge/constitution.md doesn't exist — omit the section entirely
    // rather than send an empty CONSTITUTION prompt (matches the
    // sequential VERIFY step, which only passes rules when the file exists).
    const verdict = await agent(
      `ROUTING: ${verifierModel}/${verifierEffort} — verify ${task.id} at equal-or-higher tier\n` +
      `Verify this diff against its EARS criteria and gates.\n` +
      `TASK + WORKER REPORT:\n${task.contractText}\n${prev.workerReport}` +
      (constitutionRules
        ? `\nCONSTITUTION RULES (report yes/no per rule, with concrete evidence):\n${constitutionRules}`
        : ''),
      {
        label: `verify:${task.id}`,
        phase: 'Verify',                   // must match a meta.phases title
        agentType: 'forge:forge-verifier',
        model: verifierModel,             // explicit — Hard Rule 1 again
        // WHY schema: the verdict is DATA the kernel consumes at
        // INTEGRATE, not prose — same strict contract as sequential.
        // WHY `constitution` as its own array (not folded into `clauses`):
        // mirrors the sequential verifier's separate CONSTITUTION block
        // (forge:kernel, VERIFY) so INTEGRATE applies the identical "any
        // no fails" rule without conflating EARS clauses with constitution
        // rules. Optional/empty when constitutionRules is null.
        schema: {
          type: 'object',
          properties: {
            verdict: { enum: ['PASS', 'FAIL'] },
            clauses: { type: 'array', items: { type: 'object', properties: {
              clause: { type: 'string' }, pass: { type: 'boolean' },
              evidence: { type: 'string' } } } },
            constitution: { type: 'array', items: { type: 'object', properties: {
              rule: { type: 'string' }, pass: { type: 'boolean' },
              evidence: { type: 'string' } } } },
          },
          required: ['verdict', 'clauses'],
        },
      },
    );
    // WHY results-only: INTEGRATE (merge, merged-gates run, commit,
    // queue-state writes) is kernel-owned OUTSIDE this workflow — the
    // kernel merges one worktree at a time on main. No fs/git calls here.
    return { id: task.id, workerReport: prev.workerReport, verdict,
             runInfo: { phase: 'Verify', startedAt: args.startedAt } };
    // NOTE: no Date.now()/Math.random() anywhere — nondeterminism breaks
    // resumeFromRunId's cached replay; timestamps come in via args.
  },
);

return { results, spent: budget.spent() }; // spent → per-task cost lines
```

The kernel then, for each result in completion order: consume the verdict →
merge the worktree, conflict-checked per merge — strictly sequential and
kernel-owned, exactly as `forge:kernel` INTEGRATE specifies. Once every
result in the batch has been merged, the kernel runs the gate suite ONCE
against the fully-merged result (not once per task) — single-gate batch
INTEGRATE (`docs/conventions.md`, "Latency rules — ship-review overlap,
mechanical bounces, batch gates, sliding-window dispatch — 2026-07",
rule 3). If the merged-result gate run is green, every task in the batch
commits together and the kernel writes queue state for the whole batch. If
the merged-result gate run fails, the kernel bisects by re-running gates
per-merge in the same completion order used to build the merge, to isolate
which task's merge broke the batch, then bounces only the offending task
(max 2 retries, then blocked) while the rest of the batch commits — the
merged-gates run remains authoritative over any per-worktree pass. A FAIL
verdict from the verifier stage bounces that task normally before it ever
reaches merge. Any `constitution` entry with `pass: false` fails
verification exactly like a failed EARS clause — the kernel treats it as a
FAIL verdict at INTEGRATE, same as the sequential VERIFY step's rule
(`forge:kernel`, VERIFY, "Constitution (Phase 3)": "Any `no` fails
verification"). When `constitutionRules` was `null` (no constitution file),
`constitution` is absent or empty and imposes no condition. Each task in
the batch increments the session dispatch count, same as sequential
dispatch.
