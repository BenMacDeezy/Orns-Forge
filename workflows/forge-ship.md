# forge-ship — canonical Workflow script for a full-tier ship review

Reference doc for the kernel's Executor (`skills/kernel/SKILL.md`, "Executor").
Runs the `forge:ship` protocol's judge passes for ONE full-tier task —
reviewer always, security only on a trigger the kernel NAMES in the
dispatch note (docs/conventions.md, "Verification economics — 2026-07-18"),
legal only when the diff adds or bumps a dependency, vendors
third-party code, or integrates a new external service/API (the kernel
decides both flags before dispatching; the script never re-decides scope).
Judges are read-only: this script spawns them in parallel and returns their
verdicts; the pass/fail decision, the done-bar check, and every `.forge/`
write happen in the kernel at INTEGRATE.

Contract with the kernel:

- **Ship overlap (latency rule).** This script's input needs no verifier
  verdict — `diffSummary`/`criteria` come straight from the builder's
  return — so the kernel may launch it alongside the `forge-verifier`/
  `forge-ui-verifier` spawn, as one parallel batch, instead of waiting for
  the verifier verdict first. The done bar and every judge inside this
  script are unchanged; only the wall-clock ordering relative to the
  verifier moves. Full rule: `docs/conventions.md`, "Latency rules —
  ship-review overlap, mechanical bounces, batch gates, sliding-window
  dispatch," which is NORMATIVE.
- **Input** `args`: `{ taskId, diffSummary, criteria,
  needsSecurity, needsLegal, model, effort, startedAt }`. Routing is decided
  by the kernel's ROUTE table (full-tier judges run opus-tier; effort in the
  ROUTING line). `needsLegal` mirrors `needsSecurity`'s pattern — the kernel
  decides it from `forge:ship`'s item-6 trigger (dependency/vendor/new
  external service) before dispatch; the script never re-decides it.
- **Output**: `{ review, security | null, legal | null }` — three strict
  findings verdicts. Any Critical or Important finding from review/security
  fails verification and bounces at INTEGRATE; a `BLOCK-RECOMMENDED` legal
  verdict fails the same way, exactly as the sequential ship protocol
  specifies.
- The kernel records the workflow `runId` in the task's Attempt log at
  dispatch; resume via `resumeFromRunId` beats re-dispatching (completed
  judge calls return cached).

```js
// forge-ship: reviewer + conditional security + conditional legal, in parallel, one task.
// Script shape: `export const meta` then the BODY directly (no wrapper
// function, no default export) — args/budget/agent/parallel are globals.
export const meta = {
  name: 'forge-ship',
  description: 'Full-tier ship review: forge-reviewer + conditional forge-security + conditional forge-legal, in parallel, on one diff',
  phases: [{ title: 'Review' }],   // objects with title, not strings
};

// WHY a shared schema: forge:ship's strict findings contract — severity-
// tagged, file:line, failure scenario — is what makes the verdict DATA the
// kernel can act on (Critical/Important ⇒ FAIL) instead of prose.
const findingsSchema = {
  type: 'object',
  properties: {
    // Matches agents/forge-reviewer.md and agents/forge-security.md's own
    // documented output contract (`VERDICT: PASS | CHANGES REQUESTED`) —
    // unlike forge-wave.md's verifier schema, these two judges never say
    // FAIL themselves; the kernel derives the FAIL/bounce decision from
    // CHANGES REQUESTED (or any Critical/Important finding) at INTEGRATE.
    verdict: { enum: ['PASS', 'CHANGES REQUESTED'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { enum: ['Critical', 'Important', 'Minor'] },
      location: { type: 'string' },          // file:line
      failureScenario: { type: 'string' },   // concrete, not hypothetical
    }, required: ['severity', 'location', 'failureScenario'] } },
  },
  required: ['verdict', 'findings'],
};

// forge-legal's output contract (agents/forge-legal.md) is shaped
// differently from the review/security findings contract — VERDICT is a
// three-way recommendation, not PASS/FAIL, and it separately carries
// obligations (NOTICE/attribution text) and counsel-only questions.
const legalSchema = {
  type: 'object',
  properties: {
    verdict: { enum: ['CLEAR', 'OBLIGATIONS', 'BLOCK-RECOMMENDED'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      color: { enum: ['GREEN', 'YELLOW', 'RED'] },
      subject: { type: 'string' },
      finding: { type: 'string' },
      citation: { type: 'string' },
    }, required: ['color', 'subject', 'finding', 'citation'] } },
    obligations: { type: 'string' },   // attribution/NOTICE entries, or "none"
    forCounsel: { type: 'string' },    // questions only counsel can answer, or "none"
  },
  required: ['verdict', 'findings', 'obligations', 'forCounsel'],
};

const { taskId, diffSummary, criteria, needsSecurity, needsLegal, model, effort } = args;

// WHY parallel([...]): both judges read the same diff and neither writes,
// so genuine parallelism exists (delegation criterion b) with zero
// integration risk — verdicts are combined by the kernel afterwards.
// WHY thunks: parallel() takes functions so cached completions can be
// skipped deterministically on a resumeFromRunId replay.
const [review, security, legal] = await parallel([
  () => agent(
    // Scope instruction, not a sequencing claim: under ship overlap the
    // verifier verdict does not precede this call (they run in parallel),
    // so this is a surface boundary — EARS-clause verification is the
    // verifier's job, running concurrently, not the reviewer's — rather
    // than "the verifier already checked this."
    `ROUTING: ${model}/${effort} — full-tier ship review of ${taskId}\n` +
    `Review this diff. EARS-clause verification is the verifier's surface, ` +
    `running in parallel — not yours; focus on simplification and issues ` +
    `outside that surface.\n` +
    `CRITERIA:\n${criteria}\nDIFF SUMMARY:\n${diffSummary}`,
    { label: `review:${taskId}`, phase: 'Review',   // matches meta title
      agentType: 'forge:forge-reviewer',
      model,                        // explicit model — Hard Rule 1
      schema: findingsSchema },
  ),
  // Security judge only when the kernel flagged the diff's surface —
  // needsSecurity came in via args; the script never re-decides it.
  // Effort rides in via args (${effort}), same as the reviewer call above —
  // no hardcoded tier here; the sequential path's canonical opus/high (
  // agents/forge-security.md, skills/ship/SKILL.md) is what the kernel
  // passes as `effort` when it dispatches a full-tier ship review.
  needsSecurity
    ? () => agent(
        `ROUTING: ${model}/${effort} — security pass on ${taskId} (auth/input/secrets/money surface)\n` +
        `Security-review this diff.\nCRITERIA:\n${criteria}\nDIFF SUMMARY:\n${diffSummary}`,
        { label: `security:${taskId}`, phase: 'Review',
          agentType: 'forge:forge-security',
          model,                    // explicit again — nothing inherits
          schema: findingsSchema },
      )
    : () => null,
  // Legal judge only when the kernel flagged the diff as adding/bumping a
  // dependency, vendoring third-party code, or integrating a new external
  // service/API (forge:ship item 6) — needsLegal came in via args; the
  // script never re-decides it. forge-legal's own default route (
  // agents/forge-legal.md, skills/ship/SKILL.md item 6) is sonnet/medium,
  // independent of the task's own routed `model`/`effort` tier — it stays
  // an explicit literal here rather than riding on the judge tier used by
  // review/security, per Hard Rule 1 (nothing inherits).
  needsLegal
    ? () => agent(
        `ROUTING: sonnet/medium — legal pass on ${taskId} (dependency/vendor/third-party-integration surface)\n` +
        `Legal-review this diff.\nCRITERIA:\n${criteria}\nDIFF SUMMARY:\n${diffSummary}`,
        { label: `legal:${taskId}`, phase: 'Review',
          agentType: 'forge:forge-legal',
          model: 'sonnet',          // explicit literal — forge-legal's own default route
          schema: legalSchema },
      )
    : () => null,
]);

// Results only: no queue writes, no commit, no spec-delta filing here —
// the kernel owns the done bar and all .forge/ state (Hard Rule 4).
// No Date.now()/Math.random(): determinism keeps resume replay valid.
return { taskId, review, security, legal, spent: budget.spent(),
         startedAt: args.startedAt };
```

The kernel consumes all three verdicts at INTEGRATE: any Critical or
Important finding from review/security, OR a `CHANGES REQUESTED` verdict
from either judge, ⇒ FAIL ⇒ normal bounce path; otherwise the full-tier
done bar (verifier PASS + constitution + ship protocol) decides. For legal,
a `BLOCK-RECOMMENDED` verdict ⇒ FAIL ⇒ normal bounce path, same as a
Critical/Important finding (a human decides whether to accept the risk,
swap the dependency, or drop it); a `CLEAR` or `n/a`
(judge not spawned) verdict imposes no additional condition; an
`OBLIGATIONS` verdict does not fail the task, but its `obligations`
attribution/NOTICE entries must land in the same diff before INTEGRATE
commits — INTEGRATE holds the commit until they're present, exactly as
`skills/ship/SKILL.md` item 6 specifies for the sequential path. The ship
dispatch increments the session dispatch count like any other dispatch, and
`budget.spent()` feeds the session report's per-task cost line.
