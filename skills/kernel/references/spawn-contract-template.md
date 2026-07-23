# Spawn contract template

Every Agent-tool dispatch MUST use this structure as the prompt. An unfilled
field is a protocol violation — stop and fill it.

`<model>` in the ROUTING line is always one of the plugin's routed model
vocabulary — `haiku | sonnet | opus` (`docs/conventions.md`, "Model
vocabulary — fable amendment (2026-07-17)") — never a vague
label like "best available". For the kernel ROUTE table's Critical/forensic
profile, `<model>` is exactly `opus`, the strongest tier the router assigns
on its own. `fable` may appear in a ROUTING line ONLY when a human
explicitly requested it (directly, or via a `fable/<effort>` forge.md
Routing override) — it is an expensive human-authorized escalation for
extremely deep reasoning, never a router decision; the ROUTING reasoning
line must name the human authorization when it is used.

**Context budget.** A contract is retrieval pre-done, not retrieval delegated:

- Map content included in CONTEXT is task-scoped EXCERPTS only — the
  paragraphs that bear on this task — never whole map files pasted in.
- MANDATORY include: every memory fact whose `agents:` list names the agent
  being spawned (excerpt or full body if short) — mechanical, not judgment;
  then judgment-selected facts as before, within the ~1k cap (tagged facts
  get priority when trimming).
- The whole contract targets ≤ ~1k tokens beyond the task file itself. If it
  wants to be bigger, the excerpting was not done — trim, don't paste.
- Verifier contracts carry the diff + acceptance criteria + gate commands
  only. No repo-exploration mandate: a verifier judges the diff against the
  criteria; it is not sent spelunking.

**CONTEXT PACK is REQUIRED** (`docs/conventions.md`, "Verification
infrastructure — 2026-07-18 (fg-a10908)"): every dispatch carries pre-rooted
retrieval, not a mandate to go re-derive it —

- Committed harness(es) to RUN, never hand-rolled if one already exists at
  `scripts/verify-*` or `tools/` — or state the check is throwaway/one-shot
  and why.
- Shared build/server for this wave (port/PID) if one is already running —
  reuse it, never rebuild; if none exists yet and this dispatch is first to
  need one, say so and it becomes the owner.
- Power tools note, one line, when the scout/onboard has vetted any for this
  repo (e.g. "Serena active: use find_referencing_symbols for impact
  checks") — omit only when none are vetted.
- Environment invariants: cite the target repo's committed reference file
  (e.g. `AGENTS.md`) instead of restating port etiquette /
  kill-own-PID-only / fixture-route hygiene prose here.
- Prior measurement tables that already settled facts (a re-derivation
  owner's published numbers) — consumers judge from the table, they do not
  re-derive it.

```
ROUTING: <model>/<effort> — <one-line reasoning>

OBJECTIVE
<the single thing this spawn must accomplish>

CONTEXT (complete — do not search beyond it unless SCOPE says you may)
- Task file content: <inline the task file>
- Relevant excerpts: <code/config excerpts the work needs, retrieval pre-done>
- Conventions: <build/test/run commands; relevant project conventions>

CONTEXT PACK (pre-rooted — required, see above)
- Committed harness(es) to RUN: <path(s), or "none — throwaway/one-shot: <why>">
- Shared build/server for this wave: <port/PID, or "none needed" | "this dispatch owns it">
- Power tools: <one line, e.g. "Serena active: use find_referencing_symbols for impact checks" | "none vetted">
- Environment invariants: <cite committed reference file, e.g. AGENTS.md — do not restate prose>
- Prior measurement tables: <inline the settled facts, or "none">
- Sibling task notes: <reusable context from same-spec DONE siblings, or "none">

SCOPE
- May modify: <files/dirs>
- Must not touch: .forge/ (the kernel owns queue state), <other exclusions>
- May search beyond provided context: <yes, within <dir> | no>

OUTPUT CONTRACT
<the exact structured form the final message must take — it is data for the
kernel, not prose for a human>

STOP CONDITIONS
- If acceptance criteria are ambiguous or contradictory: stop, report, do not improvise.
- If the change requires touching out-of-scope files: stop and report.
```

## Sibling task notes (cc-sdd pattern, fg-a10702 steal-list, promoted 2026-07-20)

WHEN PLAN runs for a task whose spec has sibling tasks already `state: done`,
THE SYSTEM SHALL read those siblings' task-file Attempt logs / Implementation
Notes for reusable context (helpers created, conventions settled, gotchas)
BEFORE dispatch, and SHALL fold relevant findings into this contract's
CONTEXT PACK "Sibling task notes" line rather than re-deriving them or
leaving the spawned agent to rediscover them.

WHEN LEARN considers filing a memory fact, THE SYSTEM SHALL NOT mint one for
knowledge that only serves same-spec siblings — intra-spec handoff rides the
task files themselves (this section), never a LEARN fact; LEARN facts are
reserved for knowledge that outlives the spec.
