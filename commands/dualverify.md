---
description: Run a human-invoked, audit-shaped simultaneous Claude+codex dual verification over one task or task group
argument-hint: "<task-id | task-group>"
---

Run one blind dual-verifier audit over `$ARGUMENTS`.

- **Human-ask only.** This is the ONLY legal surface for a simultaneous
  Claude+codex verifier pair. Never invoke it from the kernel loop, a wave,
  or standing consent; accept exactly one task or one explicitly named task
  group per invocation, and only where two independent audit sweeps are the
  point.
- **State the extra cost up front.** Before dispatch, say that this runs two
  full blind sweeps, rather than the normal sequential sweep plus a
  findings-review pass. If that cost is not appropriate, use the normal
  verifier route instead.
- **Sweep blind, then reconcile.** Give both read-only verifiers the same
  scope and criteria but neither verifier's findings. Reconcile their output
  finding-by-finding through `docs/conventions/verification.md`,
  "Verifier-finding filter"; do not replace that filter with free-form
  synthesis. Preserve non-conflicting findings, run its one clarification /
  reproduction pass for contradictions, and surface any outcome-affecting
  unresolved contradiction as a human blocker.
- **Provider-gate degradation.** If any codex provider gate layer blocks,
  run one stated Claude single-verifier pass instead--never a silent skip or
  a dual-Claude substitute--per `provider-judges.md` section 1a, "Provider
  gate layers." Report the blocking layer and the degraded run plainly.

Reply with the target, whether the run was dual or degraded, the up-front
cost statement, both blind findings (or the single-verifier result), and the
verifier-finding-filter reconciliation outcome.
