---
name: bug-triage-classification
description: Reproduce and classify a bug report into a ready queue-task draft without drifting into fixing it. Use when triaging a bug, deciding a bug's severity/priority, reproducing a defect, or turning a raw bug report into an actionable task. Backs the forge-triage agent (Forge intake door 3).
---

# Bug triage & classification

Triage answers three questions and stops: **does it reproduce, how bad is it,
what is the ready task?** It never fixes and never writes queue state — the
`forge:queue` skill (invoked by the triage command) owns all writes. Triage
hands back a draft; the command persists it.

**Boundary vs `forge:queue` capture:** a report with repro intent — "this is
broken," "X is failing," a stack trace, unexpected behavior — routes through
triage first, here. A task-shaped TODO with no defect behind it — "we should
add X," "let's track doing Y later" — has nothing to reproduce or classify;
it goes straight to `forge:queue` as a plain task, not through this skill.

## 1. Reproduce first — minimal repro or bust

Before classifying anything, reduce the report to the **smallest sequence of
steps that reliably triggers the defect** on a stated environment. Strip
unrelated setup; confirm the failing behavior appears and disappears when the
trigger is present/absent.

- A bug that reproduces gets steps + a severity classification (below).
- A bug that does NOT reproduce stays **`state: backlog`** with a note
  recording what was tried, the environment used, and the missing information
  needed to reproduce. The triage output records **`REPRODUCED: no`**. Route it
  back for more detail; do not invent a severity to make the report look
  actionable.

## 2. Classify — severity × likelihood decision table

Severity is the blast radius of one occurrence; likelihood is how often real
users hit the trigger. Read priority off the table, not off a vibe:

| Severity ↓ / Likelihood → | Rare | Occasional | Frequent |
|---|---|---|---|
| **Critical** (data loss, security, corruption, hard crash, money) | P2 | P1 | P1 |
| **Major** (core feature broken, no workaround) | P2 | P2 | P1 |
| **Moderate** (feature degraded, workaround exists) | P3 | P3 | P2 |
| **Minor** (cosmetic, edge case, low-impact) | P4 | P3 | P3 |

Priority maps to the queue's `priority` field (1 = highest). State the chosen
cell and the one-line reason (which severity band, which likelihood band, why).

## 3. Duplicate check — before minting anything

Search the existing queue (`.forge/queue/tasks/`) and, if present, the repo map
(`.forge/map/hotspots.md`) for an existing task covering the same defect or
component. If a live task already covers it, do NOT mint a new one — attach the
new repro/environment as corroborating evidence to that task and say so. Only a
genuinely new defect becomes a new task draft.

## 4. Expected-vs-actual on every ready task

Every ready draft carries the same template, filled concretely (no
placeholders):

```
Expected: <what the system should do at the trigger>
Actual:   <what it does instead, verbatim — error text, wrong value, crash>
```

This is the payload a verifier and a fixer both key off; a report without a
crisp expected/actual is not ready.

## 5. Ready-task definition of done

A draft is **ready** only when it carries ALL of:

1. **Repro steps** — the minimal sequence from step 1.
2. **Environment / version** — OS, build/commit, config, and any data
   preconditions the repro needs.
3. **Expected vs actual** — the step-4 block.
4. **Suspected component** — the file/subsystem/module the evidence points at
   (best current hypothesis, not a fix).

The acceptance criteria are written in EARS so the eventual fix is checkable —
e.g. `WHEN <the reproduced trigger>, THE SYSTEM SHALL <the expected behavior>`.
Missing any of the four → the draft stays `backlog`, not `ready`.

## Scope discipline — triage does not fix

- Triage **reproduces and classifies**; it does not patch, refactor, or write
  a failing test into the codebase.
- Triage **does not write queue state** — it returns a draft (proposed
  frontmatter + body); the `forge:queue` skill invoked by the command performs
  the write. This keeps the audit trail single-owner.
- If the bug can't be fixed without a design change (new behavior, API change,
  a deliberate trade-off), triage does not decide it — it **recommends
  `/forge:spec`** and hands over the repro + expected/actual as spec input.
  Straightforward defects skip spec approval; design-changing ones do not.

## Sources

- Forge conventions: `docs/conventions.md` (task frontmatter, EARS clause form
  `WHEN [trigger], THE SYSTEM SHALL [behavior]`, state machine incl.
  `ready`/`backlog`).
- `forge-triage` agent contract (intake door 3: drafts only, never writes queue
  state).
- EARS: Mavin et al., "Easy Approach to Requirements Syntax", IEEE
  International Requirements Engineering Conference (RE), 2009.
