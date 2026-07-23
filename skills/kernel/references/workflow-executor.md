# Executor mode (reference)

Loaded by `skills/kernel/SKILL.md` between GATE and DISPATCH when forge.md's
Features set `workflow-executor: on` AND the harness offers the Workflow
tool. NORMATIVE — moved verbatim from the kernel's "Executor" section, not
summarized. If the toggle is off, or the tool is absent, none of this
applies: the sequential markdown loop (ROUTE+DISPATCH below) runs unchanged
and behavior is identical either way.

When forge.md's Features set `workflow-executor: on` AND the harness offers
the Workflow tool, the kernel dispatches **parallel-eligible batches** and
**full-tier ship reviews** as deterministic Workflow scripts —
`workflows/forge-wave.md` and `workflows/forge-ship.md` (plugin root)
describe the canonical scripts. **Detecting tool presence:** check your own
available tool list for a tool literally named `Workflow`; if it is absent,
or `ToolSearch` cannot load it, fall back to the sequential loop below —
never assume the tool exists. The sequential markdown loop below remains
the portable fallback whenever the tool is absent or the toggle is off:
**behavior must be identical either way — only the executor changes.** The
same GATE eligibility test, the same routing table, the same
claim-the-whole-batch-first mechanics (claims are kernel-owned `.forge/`
writes, made BEFORE the Workflow call), the same verify/integrate rules; a
workflow run must produce byte-identical `.forge/` state transitions to the
sequential path.

Two hard rules carry over verbatim into any script:

1. Every `agent()` call passes an explicit `model` (and effort in the
   prompt's ROUTING line) — Hard Rule 1 applies inside workflows; nothing
   inherits the session model.
2. INTEGRATE and all `.forge/` writes stay kernel-owned OUTSIDE the workflow
   — scripts spawn workers/judges and return results; the kernel consumes
   those results and integrates sequentially on main (Hard Rule 4).

/forge:start and Forge commands are user-invoked; their instructions
authorizing the Workflow call constitute the user's opt-in to multi-agent
orchestration.

**Budget accounting:** workflow dispatches ALSO increment the session
dispatch count (step 5) — one increment per task the script processes, same
as sequential dispatch. The Workflow tool's `budget.spent()` additionally
gives real token figures for the session report's per-task cost line.
In-script `agent()` calls are not Task/Agent tool dispatches, so the
`budget-guard` PreToolUse hook never observes them; the kernel's own
dispatch count — incremented once per task handed to the script at the
Workflow call — is therefore the ONLY enforcement mechanism in Executor mode.

**Crash recovery:** record the workflow `runId` in each batch task's Attempt
log at dispatch. A workflow run that dies can be resumed via
`resumeFromRunId` — completed `agent()` calls return cached results — which
is preferred over re-dispatching from scratch. If resume is impossible, the
normal stale-claim recovery path applies.
