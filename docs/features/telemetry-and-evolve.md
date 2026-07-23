# Telemetry + Evolve (routing-tuning recommendations)

Canonical vocabulary and thresholds:
[`docs/conventions.md`](../conventions.md), "Telemetry vocabulary — 2026-07"
and "Routing-tuning recommendations (Evolve analogue) — 2026-07". Tool:
`tools/telemetry.py`.

## What it aggregates

`tools/telemetry.py` parses every task file's Routing record and Attempt
log into per-agent, per-tier, and per-verify-mode stats: dispatch counts,
first-attempt pass rate, bounce counts (MECHANICAL/JUDGMENT/untagged),
verify-mode mix (gates-inline / verifier / kernel-synthesis), and
`escalate_count`. The exact phrasing of Attempt-log lines is the parser's
grammar and is NORMATIVE — a protocol edit that rewords one of these
phrases must update the parser in the same change, or the tool silently
starts under-counting instead of surfacing drift:

- `attempt N: dispatched <ISO-8601> (<reason>)` — a dispatch.
- `attempt N verify: <model>/<tier> [verifier] -> PASS|FAIL|ESCALATE ...`
  (or `attempt N verdict: ...`) — a first-line verify verdict.
- `attempt N re-verify: <model>/<tier> [focused] -> PASS|FAIL ...` — a
  post-bounce re-verification, never counted in the first-attempt PASS-rate
  denominator.
- `attempt N (bounce, <model>/<tier>[, ...]): <description>` — a bounce
  redispatch, its parenthetical searched for a MECHANICAL/JUDGMENT tag.
- `low-risk verify: qualified — <reason>` and `sampling audit` — the
  kernel's Low-risk verification classification lines.
- `judge-yield: <agent-slug> raised=<N> survived=<M> changed=<K>`, optionally
  with a trailing `p0=A p1=B p2=C p3=D` severity-count suffix — every judge
  verdict the kernel consumed on a task. See
  [Panel policy](verification-economics.md#panel-policy--the-per-task-ceiling)
  and [P0-P3 severity + confidence](verification-economics.md#p0-p3-severity--confidence-on-every-finding)
  for what feeds this line; the base shape parses unchanged whether or not
  the severity suffix is present, and a present-but-malformed suffix fails
  the whole line into the unparsed tally rather than a silent partial parse.

**Honest coverage, as of the 2026-07-18 overhead audit:** the parser reads
roughly 45% of Attempt-log lines by its own admission (`attempt_lines_
unparsed` in its output) — legacy phrasing from before the current
convention landed accounts for most of the gap, not a parser bug. See the
[verification economics page](verification-economics.md) for what a full
manual read found underneath that gap.

## Routing-tuning recommendations (`--recommend`)

Builds on the same aggregates, no new grammar, to surface `(agent slug,
routed tier)` pairings that look mistuned — strictly a **proposal**, never
a self-applying change.

**Qualification (both must hold):** the pairing's dispatch count is ≥ 5,
and its first-attempt FAIL-or-bounce rate is ≥ 40%. Both thresholds are
hard-coded constants in `tools/telemetry.py`
(`RECOMMEND_MIN_DISPATCHES`, `RECOMMEND_MIN_FAIL_RATE`) and change only by
a human editing the conventions section and the constants together.

A qualifying recommendation suggests the next tier up the routed ladder
(`haiku -> sonnet -> opus`, effort held constant while the model bumps; once
already at `opus`, the next effort up instead). **The ceiling is hard-coded
at `opus`/`high` — `fable` is never a recommendation target**, the same
rule as everywhere else in the routing table: `fable` is a human-authorized
escalation, never something a router or a recommendation engine selects.

## Filing and ratification — the same human gate every delta goes through

A qualifying recommendation is recorded as an **UNRATIFIED delta** in
the human-gated changelog process, in the exact format
every other spec delta there already uses. Filing the delta is the
**entire** effect: the kernel that runs `--recommend` at LEARN never edits
the ROUTE+DISPATCH table, a task's Routing record, or `forge.md` itself.
Ratification (or rejection) happens exclusively through the pre-existing
`/forge:spec` delta-ratification flow — the identical human gate every
other spec delta already goes through. No toggle, budget, or
standing-consent setting shortcuts this.

`--recommend` never reports a bare verdict: every recommendation prints its
underlying counts (dispatches, fail-or-bounce count, rate) alongside the
suggested next tier, and a run with nothing qualifying prints
`no recommendations` plus the two thresholds themselves — so "nothing to
recommend" is always distinguishable from "the thresholds are unknown."
