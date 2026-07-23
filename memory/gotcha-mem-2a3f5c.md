---
name: mem-2a3f5c
description: Harness skill auto-activation can hijack orchestrator loop turns in headless runs — never dismiss a repro as an emulation artifact.
type: gotcha
created: 2026-07-17T23:00:14Z
updated: 2026-07-18T00:40:20Z
superseded-by: null
schema-version: 1
---

Harness skill auto-activation (description-matching that fires a skill from
plain conversation text) can hijack a turn inside an active Forge
orchestrator loop — a review/security/git skill's description matches
something in a task's title or output and the harness activates it mid-loop,
diverting the session away from the kernel's own step sequence. This is a
real failure mode observed in headless runs, not a quirk of an interactive
terminal or a simulation artifact: it was falsified as "emulation-only" by a
live headless repro on 2026-07-17.

Mitigations: the kernel's explicit-skill-use-only suppression clause while
the loop is active (`skills/kernel/SKILL.md`, "While the Forge loop is
active, do not auto-invoke any skill via description matching"), plus a
loop-guard hook that intercepts and blocks unintended auto-activations
during a running loop. Both are needed — the prose suppression clause alone
is not sufficient enforcement in a headless context where no human is
present to notice a hijacked turn.

The lesson for any future investigation of "does the harness ever
auto-activate a skill mid-loop": treat a headless repro as real evidence,
not as something to wave away with "that's just how the emulation renders
it." A prior investigation did exactly that and was wrong.

Corroborated 2026-07-17 (later same day): also reproduced in a SUBAGENT
spawn — an opus verifier dispatch was grabbed by the security-review skill's
description matching at startup and died in 7s with zero tool uses. Working
mitigation: open every dispatch prompt with an explicit suppression notice
("do not auto-invoke any skill; follow only this contract") — the retry with
that preamble ran contract-pure.
