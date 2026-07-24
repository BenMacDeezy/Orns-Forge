---
name: mem-e4a917
type: gotcha
description: string pins stay green while a rule is incoherent — a mechanism can be made unreachable by an untouched precondition elsewhere; verifiers must reachability-check new mechanisms, not just grep (2026-07-18 sweep-4)
created: 2026-07-18T06:00:00Z
updated: 2026-07-18T06:00:00Z
agents: [forge-verifier, forge-worker]
superseded-by: null
schema-version: 1
---

In the 2026-07-18 sweep-4 wave, a sliding-window dispatch rule shipped with
every doc-pin green — and was dead on arrival: an UNTOUCHED eligibility
precondition two files away ("batch size ≤ max-parallel-tasks") made the
"surplus tasks" state the new rule described definitionally unreachable. The
worker had even been told to fix the contradicting sentence "if it
contradicts" and reworded only its tail, leaving the load-bearing clause.
String pins (assertIn/assertNotIn) verified the new words existed; nothing
verified the described state could ever occur.

Rules: (1) when a change introduces a mechanism triggered by a state ("when
X exceeds Y", "when the batch has surplus"), the verifier must trace whether
any path can PRODUCE that state — grep every precondition that gates entry to
the mechanism's context, in every file, not just the edited ones; (2) "fix
the sentence if it contradicts" briefs invite tail-only rewording — name the
exact clause to remove, not the sentence to reconsider; (3) after such a
fix, pin the ABSENCE of the old gating clause (assertNotIn), scoped to the
region, alongside the presence pins.
