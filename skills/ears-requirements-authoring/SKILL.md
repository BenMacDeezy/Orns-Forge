---
name: ears-requirements-authoring
description: Write acceptance criteria in EARS format correctly — the five templates, one assertion per criterion, non-goals, and clarification markers. Use when authoring acceptance criteria, drafting a spec's requirements, converting a feature idea into testable statements, or reviewing criteria for ambiguity. Backs the forge-spec-writer agent.
---

# EARS requirements authoring

EARS (Easy Approach to Requirements Syntax) constrains each requirement to one
of five sentence templates so criteria are unambiguous, atomic, and
test-mappable. Every Forge acceptance criterion is one EARS clause.

## The five templates — pick by trigger shape

Choose the template from what conditions the behavior, not by habit:

1. **Ubiquitous** — always true, no trigger.
   `THE SYSTEM SHALL <behavior>.`
   Use for invariants that hold at all times (e.g. "THE SYSTEM SHALL store
   passwords only as salted hashes.").

2. **Event-driven** — a discrete trigger occurs.
   `WHEN <trigger>, THE SYSTEM SHALL <behavior>.`
   Use for a response to an event/action (this is the Forge default form).

3. **State-driven** — true throughout a state.
   `WHILE <state>, THE SYSTEM SHALL <behavior>.`
   Use for behavior that persists as long as a condition holds (e.g. "WHILE
   offline, THE SYSTEM SHALL queue writes locally.").

4. **Unwanted-behavior** — an error/undesired condition.
   `IF <condition>, THEN THE SYSTEM SHALL <behavior>.`
   Use for handling failures, invalid input, abuse (e.g. "IF the token is
   expired, THEN THE SYSTEM SHALL reject the request with 401.").

5. **Optional-feature** — behavior gated on a feature's presence.
   `WHERE <feature>, THE SYSTEM SHALL <behavior>.`
   Use for behavior that exists only when a feature/config is included.

Templates compose: a clause may combine keywords (e.g. `WHILE <state>, WHEN
<trigger>, THE SYSTEM SHALL …`) when the behavior genuinely depends on both.

## One testable assertion per criterion

Each criterion asserts exactly ONE checkable behavior. A compound clause hiding
two requirements behind "and" must be split — otherwise a verifier can't say
which half failed.

- Bad: `WHEN a file uploads, THE SYSTEM SHALL scan it for viruses and email the
  owner.` (two behaviors)
- Good: two clauses — one for the scan, one for the notification.

Every clause must be objectively checkable (observable output, a value, an
exit code) so it maps to a test or a verifier observation.

## Non-goals as first-class

For every goal that could creep, write the paired non-goal in the spec's
`## Non-goals`. Non-goals are not an afterthought — they are the fence that
keeps a criterion from silently widening.

- Goal: "authenticate users via email + password."
- Paired non-goal: "SSO / OAuth providers are out of scope for this spec."

Pair ambiguous goals with their non-goals explicitly so a reader can't read
scope into the gap.

## [NEEDS CLARIFICATION] instead of silent assumptions

Where the idea is under-specified, DO NOT pick a default and move on. Insert a
marker exactly where the gap is:

```
[NEEDS CLARIFICATION] <the specific open question>
```

A spec body containing any such marker **cannot be approved and cannot be
decomposed into queue tasks** (Forge spec pipeline, validator-enforced). The
marker is the mechanism that forces the human answer before work starts — a
guessed assumption defeats it.

## Traceable decomposition

Each acceptance criterion must map to at least one item under the spec's
`## Task decomposition`. A criterion that no downstream task satisfies is dead
scope; a task that satisfies no criterion is unjustified work. When decomposed,
each `tier: full` queue task carries forward the specific EARS clause(s) it
implements, so the audit trail runs criterion → task → verifier evidence
unbroken.

## Sources

- Forge conventions: `docs/conventions.md` (spec body sections; Acceptance
  criteria as EARS clauses; clarification-marker gating; task decomposition).
- Forge `spec` skill (`skills/spec/SKILL.md`) — clarification markers block
  approval/queueing; decomposition into linked `tier: full` tasks.
- EARS: Mavin et al., "Easy Approach to Requirements Syntax", IEEE
  International Requirements Engineering Conference (RE), 2009 — the five
  templates (ubiquitous, event-driven, state-driven, unwanted-behavior,
  optional-feature).
