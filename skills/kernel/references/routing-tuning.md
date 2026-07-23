# Routing-tuning recommendations (reference)

Loaded by `skills/kernel/SKILL.md` LEARN when `tools/telemetry.py`
exists AND this session did protocol work. NORMATIVE — moved verbatim
from LEARN, not summarized; follow it before filing any routing-tuning
recommendation.

**Routing-tuning recommendations (Evolve analogue, fg-a10102).** WHEN
`tools/telemetry.py` exists AND this session did protocol work (touched
queue, kernel, skill, or agent files — not a routine feature build), the
kernel MAY run `python tools/telemetry.py --recommend` at LEARN. Each
qualifying recommendation is recorded as an UNRATIFIED delta in
`docs/specs/2026-07-16-forge-design.md`'s `## 17. Changelog`, in the exact
format its existing UNRATIFIED entries use (`### Proposed delta — <date> —
from <task-id> — UNRATIFIED`, ending "This delta is a proposal only — spec
truth is unchanged until a human ratifies it at the next spec interaction
(§9.4)."; never invent a new format). The kernel NEVER edits the
ROUTE + DISPATCH table, any task's Routing record, or `forge.md` on the
strength of a recommendation — filing the UNRATIFIED delta is the entire
LEARN-time effect. Ratification happens only through the existing
`/forge:spec` delta flow, never automatically. Thresholds and the
qualification formula live once in `docs/conventions.md`,
"Routing-tuning recommendations (Evolve analogue) — 2026-07" — cited here,
not restated. `fable` is never recommended: the next-tier ladder hard-stops
at `opus`, the same model-vocabulary rule as ROUTE + DISPATCH above.
