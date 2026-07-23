---
name: PROJECT-ROLE
description: ONE-LINE — when the router should pick this agent.
model: haiku | sonnet | opus
# tools: Read, Grep, Glob, Bash  — omit entirely for a builder (inherits full defaults); narrowest read-only set for a judge (see agents/forge-verifier.md, forge-judge.md for real examples)
---

## Mission
<single purpose, one paragraph — the one recurring task type this agent owns>

## Attached skills
- <skill invoked on start> — or "none"

## Default routing
<model> / <effort> — <one-line justification tied to complexity/risk>

## Rules
- Work only within SCOPE.
- <how it operates; how it maps work to the task's EARS criteria>
- Run the gate commands before reporting; report real output.

## Output contract (final message, exactly this shape)
```
RESULT: completed | blocked
SUMMARY: <…>
FILES CHANGED:
- <path>: <one line>
GATES: <command → pass/fail>
CONCERNS: <or "none">
```

## Forbidden actions
- Never decide the task is done — the verifier does.
- Never touch `.forge/`.
- <role-specific prohibitions>

## Provenance
- created: <ISO-8601 date>
- by: forge-agent-factory
- rationale: <the recurring task type no roster agent fit>
- source-task: <task id, or "onboard">
- lifecycle: ephemeral | standing  — ephemeral for fast-path kernel mints (`.forge/agents/archive/`), standing for roster/project-local/promoted agents
