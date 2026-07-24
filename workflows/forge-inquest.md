# forge-inquest — canonical Workflow script for the adversarial deep-debug tribunal

Reference doc for the kernel's Executor (`skills/kernel/SKILL.md`, "Executor").
This is NOT executed from this file — the kernel (or `/forge:inquest`) writes
the script into the Workflow tool call, using this as the canonical shape.
Implements `skills/inquest/SKILL.md`'s three-role protocol: parallel FINDER
lenses → per-finding REFUTER pass (no barrier between refutes — every finding
gets attacked concurrently, not queued behind its neighbors) → JUDGE
synthesis over the full combined set (the one deliberate barrier in this
script: the JUDGE needs every refutation before it can weigh anything).

Contract with the kernel/command:

- **Gating is the caller's job, not this script's.** This script never
  decides whether an inquest should run — `skills/inquest/SKILL.md`'s
  "NEVER loop-initiated" gate and its charter (scope/budget/stop conditions)
  are satisfied by the caller (`/forge:inquest` or an accepted recommendation
  card) BEFORE this Workflow is ever invoked. The script receives an
  already-authorized charter in `args`, not a decision to make.
- **Input** `args`: `{ charter: { scope, stopConditions }, lenses:
  [{ name, prompt }...], finderModel, finderEffort, refuterModel,
  refuterEffort, judgeModel, judgeEffort, startedAt }`. `lenses` is one entry
  for a single-FINDER pass, or several under the proportionality rule (large
  scopes MAY split the FINDER into parallel correctness/security/perf/
  lifecycle lenses — `skills/inquest/SKILL.md`, "Proportionality"). Routing
  is decided by the caller exactly like `forge-wave`/`forge-ship`: every
  `agent()` call below still passes an explicit `model` — nothing inherits
  (Hard Rule 1).
- **Output**: `{ findings, routed, spent }` — results only. This script never
  creates a queue task, never touches `.forge/`, and never merges/commits
  anything — every finding it returns is a JUDGE-routed verdict the caller
  (kernel or `/forge:inquest`) acts on: CONFIRMED becomes a `forge:queue`
  draft, DISMISSED/UNRESOLVED are recorded/surfaced by the caller.
- The kernel/command records the workflow `runId` at dispatch; a dead run is
  resumed via `resumeFromRunId` (completed `agent()` calls return cached)
  rather than re-dispatched, same convention as `forge-wave`/`forge-ship`.

```js
// forge-inquest: FINDER lenses (parallel) -> REFUTER per finding (parallel,
// no barrier) -> JUDGE synthesis (one call, the deliberate barrier).
// Script shape matches forge-wave.md / forge-ship.md exactly: `export const
// meta` then the BODY directly (no wrapper function, no default export) —
// args/budget/agent/parallel/pipeline are globals.
export const meta = {
  name: 'forge-inquest',
  description: 'Adversarial deep-debug tribunal: parallel finder lenses -> per-finding refute -> judge synthesis',
  phases: [{ title: 'Find' }, { title: 'Refute' }, { title: 'Judge' }],
};

const {
  charter, lenses, finderModel, finderEffort,
  refuterModel, refuterEffort, judgeModel, judgeEffort,
} = args;

// WHY a shared findings schema: the FINDER's structured-finding contract
// (location + claim + concrete failure scenario + severity) is what makes
// its output DATA the REFUTER can attack and the JUDGE can weigh, instead
// of prose (skills/inquest/SKILL.md, "FINDER — maximalist").
const findingsSchema = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      location: { type: 'string' },
      claim: { type: 'string' },
      failureScenario: { type: 'string' },   // concrete, not hypothetical
      severity: { enum: ['Critical', 'Important', 'Minor'] },
    }, required: ['location', 'claim', 'failureScenario', 'severity'] } },
  },
  required: ['findings'],
};

// Stage 1 — Find. One FINDER spawn per lens, genuinely parallel (each lens
// reads the same tree and writes nothing, so no integration risk exists).
// No roster `agentType` here — a generic read-only agent dispatch, same
// convention as the report-task finder pattern (docs/conventions.md,
// "Finder dispatch has no dedicated agentType").
const lensResults = await parallel(
  lenses.map((lens) => () => agent(
    `ROUTING: ${finderModel}/${finderEffort} — FINDER lens "${lens.name}" for an inquest tribunal\n` +
    `Mindset: everything and anything might be a bug. Report-only, no ` +
    `self-censoring beyond structure — propose every plausible defect in ` +
    `scope you can support with a concrete failure scenario.\n` +
    `CHARTER SCOPE: ${charter.scope}\nLENS BRIEF: ${lens.prompt}`,
    { label: `finder:${lens.name}`, phase: 'Find', model: finderModel, schema: findingsSchema },
  )),
);

// Flatten every lens's findings into one list, tagging each with a stable
// id (lens + index) the REFUTER and JUDGE stages both key off.
const findings = lensResults.flatMap((result, lensIdx) =>
  (result.findings || []).map((f, i) => (
    { id: `${lenses[lensIdx].name}-${i}`, lens: lenses[lensIdx].name, ...f }
  )),
);

// WHY a shared refute schema: REFUTER verdicts are the tribunal's central
// vocabulary (skills/inquest/SKILL.md, "REFUTER — motivated skeptic") —
// REFUTED (with evidence) / CONFIRMED (refutation attempt reproduced the
// bug) / UNRESOLVED — and must stay DATA for the JUDGE, never prose.
const refuteSchema = {
  type: 'object',
  properties: {
    verdict: { enum: ['REFUTED', 'CONFIRMED', 'UNRESOLVED'] },
    evidence: { type: 'string' },   // reproduction result or disproof, not argument alone
  },
  required: ['verdict', 'evidence'],
};

// Stage 2 — Refute. Each finding is attacked independently and
// concurrently — "no barrier between refutes" (skills/inquest/SKILL.md,
// "Boundary" intro): a REFUTER never sees another finding's outcome, and no
// finding waits on its neighbors to finish. `pipeline` here has exactly one
// stage per item; the primitive still applies because findings run in
// parallel WITH EACH OTHER, the same guarantee forge-wave.md's two-stage
// pipeline gives per-task.
const refuted = await pipeline(
  findings,
  async (finding) => {
    const verdict = await agent(
      `ROUTING: ${refuterModel}/${refuterEffort} — REFUTER pass on finding ${finding.id} ` +
      `(equal-or-higher tier than the FINDER that raised it)\n` +
      `Mindset: attack, don't accept. Running code beats argument — run the ` +
      `failure scenario if the codebase makes that possible; a reproduction ` +
      `or a failed reproduction outranks prose reasoning either way.\n` +
      `FINDING:\nlocation: ${finding.location}\nclaim: ${finding.claim}\n` +
      `failure scenario: ${finding.failureScenario}\nseverity: ${finding.severity}`,
      { label: `refute:${finding.id}`, phase: 'Refute', model: refuterModel, schema: refuteSchema },
    );
    return { ...finding, refuterVerdict: verdict.verdict, refuterEvidence: verdict.evidence };
  },
);

// WHY a single JUDGE call over the full set, not one per finding: the
// JUDGE's value is weighing the complete picture at once, never one judge
// per lens or per finding (skills/inquest/SKILL.md, "Proportionality" — the
// refute/judge structure stays fixed regardless of lens count). This is the
// script's one deliberate barrier: every refutation must land first.
const judgeSchema = {
  type: 'object',
  properties: {
    routed: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      verdict: { enum: ['CONFIRMED', 'DISMISSED', 'UNRESOLVED'] },
      reason: { type: 'string' },
      // Only populated when verdict is CONFIRMED — the forge:triage-ready
      // draft (repro + expected/actual), per the Judge routing table.
      taskDraft: { type: 'string' },
    }, required: ['id', 'verdict', 'reason'] } },
  },
  required: ['routed'],
};

const judged = await agent(
  `ROUTING: ${judgeModel}/${judgeEffort} — JUDGE synthesis over ${refuted.length} refuted findings\n` +
  `Weigh claim vs. refutation evidence for EACH finding below. Do NOT ` +
  `re-litigate or re-investigate — you never re-run a scenario or add new ` +
  `evidence; you weigh only the written record. Route each finding to ` +
  `exactly one of CONFIRMED (forge:triage-ready draft) / DISMISSED (record ` +
  `the refuter's reason) / UNRESOLVED (surfaced to the human) — nothing is ` +
  `silently dropped.\n` +
  `FINDINGS + REFUTER VERDICTS:\n${JSON.stringify(refuted)}`,
  { label: 'judge:synthesis', phase: 'Judge', model: judgeModel, schema: judgeSchema },
);

// Results only: the caller (kernel or /forge:inquest) creates the
// forge:queue draft for each CONFIRMED id, records DISMISSED reasons, and
// surfaces UNRESOLVED findings to the human — this script writes nothing.
return { findings: refuted, routed: judged.routed, spent: budget.spent() };
```

The caller then, for each entry in `routed`: **CONFIRMED** — create a ready
queue-task draft via `forge:queue` from the matching finding's
location/claim/failure-scenario/severity plus the JUDGE's `taskDraft`
(repro + expected/actual; constitution rule 1 applies, same as any bug-fix
task). **DISMISSED** — record the entry (finding + `reason`) in the session
report; never re-attempted within the same pass. **UNRESOLVED** — surface
the finding, its REFUTER evidence, and the JUDGE's `reason` directly to the
human. No `.forge/` write happens inside this script — task creation is the
caller's job, exactly like `forge-wave`'s INTEGRATE staying kernel-owned
outside the script (Hard Rule 4).
