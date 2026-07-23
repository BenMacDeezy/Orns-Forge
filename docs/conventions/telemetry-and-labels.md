# Telemetry and labels

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## Dispatch display labels — 2026-07

> Amended by: "Dispatch display labels — persona amendment — 2026-07"

When the kernel (or any Forge flow) dispatches an agent through a harness
that shows a human-visible label or description for the run, the label
leads with the task's short human title — e.g. "Low-risk verify tier",
"Verify craft skill" — never with the queue id. Task ids (`fg-xxxx`)
belong in the task file, the Attempt log, the ROUTING line inside the
dispatch prompt, and commit messages, where they key the audit trail; in
a runner UI they are noise the human has to translate. The dispatch
prompt itself still names the id (the contract is unaffected) — only the
display label changes.

## Dispatch display labels — persona amendment — 2026-07

> Amended by: "Dispatch display labels — role-label amendment — 2026-07-18"

Response to fg-9f0101. Amends "Dispatch display labels — 2026-07" above:
the label's task-title half is unchanged; this defines a persona prefix on
top of it. Every roster agent file (`agents/*.md`, all 19) carries a
`display-name:` frontmatter field, placed right after `name:`, naming its
persona. The canonical slug → persona mapping, stated once here:

| Slug | Persona |
|---|---|
| (orchestrator — the kernel/session itself, no agent file) | örn |
| forge-worker | Brokk |
| forge-verifier | Vera |
| forge-ui-verifier | Iris |
| forge-reviewer | Rook |
| forge-security | Aegis |
| forge-legal | Lex |
| forge-architect | Blue |
| forge-debugger | Hex |
| forge-ui | Pixel |
| forge-animator | Flux |
| forge-test-writer | Tess |
| forge-researcher | Sage |
| forge-migrator | Tern |
| forge-scout | Scout |
| forge-mapper | Atlas |
| forge-librarian | Page |
| forge-spec-writer | Quill |
| forge-triage | Doc |
| forge-data | Rune |
| forge-finder | Hound |
| forge-refuter | Foil |
| forge-judge | Gavel |

**Label format.** A composed dispatch label leads with the persona, then
the task's short title: `<Persona> · <short task title>` — e.g.
"Brokk · Fix README typo".

**örn is the orchestrator persona** — the display identity of the kernel
session itself, the one the human talks to. It is not backed by an
`agents/*.md` file. The kernel introduces itself as örn at the top of
session reports and run charters (`forge:kernel` — SYNC's "Run charter"
step and the end-of-run session report).

**Personas are display-layer only.** Routing tables, spawn contracts, task
files, commits, and every other technical reference keep the `forge-*`
agent slugs (and `forge:kernel` for the orchestrator) — a persona name
never appears where a slug is load-bearing: not in Routing-record lines,
not in a spawn contract's ROUTING field, not in the Attempt log, not in
git history.

## Dispatch display labels — task-name amendment — 2026-07-18

Response to fg-a10909 (user 2026-07-18: "why are we still using the number
id tags for things and not like real names"). Amends "Dispatch display
labels — 2026-07" above, extending its rule from dispatch labels to EVERY
human surface: kernel narration, `/forge:status` rows, session reports,
bounce explanations, and wave summaries lead with the task's short human
name, with the id trailing in parens — "stop-hook quiescence (fg-a10906)",
never a bare `fg-xxxx`. The short name is the task's filename slug (the
part after the id) or, when the filename is id-only, the first ~6 words of
the title. Ids remain the ONLY join key everywhere load-bearing —
filenames, frontmatter, `blocked-by` edges, telemetry, grep, commits —
because parallel sessions need collision-free, rename-stable keys; this
amendment changes what humans are shown, never what machines match on.

## Dispatch display labels — role-label amendment — 2026-07-18

Response to fg-a10213 (user 2026-07-18: runner labels still show task ids
plus a redundant verb; wants "Aegis (security)"). Amends "Dispatch display
labels — persona amendment — 2026-07," above: replaces that section's
composed format, `<Persona> · <short task title>`, with `<Persona>
(<short-role>)` — e.g. "Aegis (security)", "Brokk (build)". The task being
worked is discoverable from the queue and the runner's own timing column;
it no longer belongs in the label at all — no task id (unchanged from the
base 2026-07 section's original rule) AND no task title / verb phrasing
(what this amendment removes).

**Persona -> role mapping — NORMATIVE**, giving each persona from the
slug -> persona table (persona amendment, above) its short role word:

| Persona | Role |
|---|---|
| Aegis | security |
| Vera | verify |
| Iris | ui-verify |
| Rook | review |
| Lex | legal |
| Brokk | build |
| Blue | architect |
| Hex | debug |
| Pixel | ui |
| Flux | motion |
| Tess | test |
| Sage | research |
| Tern | migrate |
| Scout | scout |
| Atlas | map |
| Page | library |
| Quill | spec |
| Doc | triage |
| Rune | data |
| Hound | find |
| Foil | refute |
| Gavel | judge |
| Grud | grunt |

örn (orchestrator) carries no role word — same "display-layer only, no
`agents/*.md` file" carve-out the persona amendment already states.

**Swarm disambiguation.** WHEN multiple instances of the same persona run
in parallel (a swarm / sharded fan-out, "Sharded fan-out — 2026-07-18,"
above), the label adds an instance number between persona and role —
`<Persona> #N (<role>)`, e.g. "Grud #3 (grunt)" — never the task id.

**Harness agent-type prefix is not the Forge label.** A runner UI's own
agent-TYPE column or prefix (e.g. "forge:forge-security") is harness-owned,
derived from the spawned agent's slug — it is NOT part of this convention.
The Forge label supplies ONLY "<Persona> (<role>)" (or its `#N` swarm
variant); it must never re-state or duplicate that harness prefix with a
verb or description of its own.

## Dispatch display labels — mobile-pair amendment — 2026-07-21

Response to `forge-mobile-agent`: two new roster agents,
`agents/forge-mobile.md` and `agents/forge-mobile-verifier.md`, join the
slug → persona table ("Dispatch display labels — persona amendment —
2026-07," above) and the persona → role table ("Dispatch display labels —
role-label amendment — 2026-07-18," above) without editing either table's
already-shard-conserved body — this section adds the two rows as a tail
amendment instead, per house convention (existing sections keep their
prose/rows byte-identical; a mapping addition always lands in a new dated
section).

| Slug | Persona |
|---|---|
| forge-mobile | Roam |
| forge-mobile-verifier | Lens |

| Persona | Role |
|---|---|
| Roam | mobile |
| Lens | mobile-verify |

## Telemetry vocabulary — 2026-07

> Amended by: "Token capture — 2026-07-19 (fg-a10212)"

Response to fg-a10101. `tools/telemetry.py` aggregates every task file's
Routing record and Attempt log into per-agent, per-tier, and verify-mode
telemetry. The exact phrases below are the parser's grammar — **NORMATIVE**:
a future protocol edit that rewords one of these phrases must update
`tools/telemetry.py` (and this list) in the same change, or the parser
silently starts under-counting instead of surfacing drift. This is the same
discipline as every other cited-by-name section in this file.

**Attempt log line shapes** (one physical line each; every non-blank line in
the section is classified parsed or unparsed, never silently skipped):

- `attempt N: dispatched <ISO-8601> (<reason>)` — a dispatch.
- `attempt N verify: <model>/<tier> [verifier] -> PASS|FAIL|ESCALATE ...` (or
  `attempt N verdict: ...`) — a first-line verify verdict. `->` or `→` both
  parse. A `FAIL` may carry a `(MECHANICAL)` or `(JUDGMENT)` tag (case-
  insensitive) — the FAIL-NOTES tag from "Latency rules" above.
- `attempt N re-verify: <model>/<tier> [focused] -> PASS|FAIL ...` — a
  post-bounce re-verification; never counted in the first-attempt PASS-rate
  denominator (only a real `verify`/`verdict` at attempt 1 is).
- `attempt N (bounce, <model>/<tier>[, ...]): <description>` — a bounce
  redispatch; its parenthetical is searched for a `MECHANICAL`/`JUDGMENT`
  tag (case-insensitive) and a `<model>/<tier>` pair.
- `low-risk verify: qualified — <reason>` (kernel's classification line, per
  "Low-risk verification" above) and `sampling audit` are matched as
  case-insensitive substrings anywhere in the section, marking the task
  low-risk / sampling for verify-mode purposes.

**Routing record line shapes** (best-effort only — not subject to the
Attempt-log unparsed tally, since only the Attempt log names that contract):
`attempt N: <slug> — <model>/<tier> — <rationale>`, `finder — verification:
kernel synthesis (mode 3) — <model>/<tier>`, `inline (kernel) — ...`, and the
legacy trivial-tier shapes `GATE: execute inline ...` / `GATE: inline ...` /
`Delegation GATE: ...`. Agent slugs are matched against the roster's
`forge-*` names (longest-name-first, so `forge-ui-verifier` is never
mis-attributed to `forge-ui`) plus `finder`; a bare `inline` mention with no
roster slug present classifies as `kernel-inline`.

**`<model>/<tier>` pair:** `(haiku|sonnet|opus|fable)/(low|medium|high|max)`,
matched wherever it appears in a line — kernel's model-vocabulary rule
above ("fable is human-authorized-only") is unaffected by telemetry merely
counting whichever tier a Routing record or bounce line names. `max` is a
valid effort value here — it is what the kernel's ROUTE+DISPATCH table
names for its top-severity "Critical/forensic (security, final gate on big
merges)" row (`skills/kernel/SKILL.md`), routed at `opus/max` — so those
lines parse and count instead of falling into the unparsed bucket. `max` is
deliberately absent from the Routing-tuning recommendation ladder below
(`tools/telemetry.py`'s `_EFFORT_LADDER`, `["low", "medium", "high"]`):
`opus`/`high` remains the hard recommendation ceiling ("Suggested next
tier," below — a qualifying pairing already at `opus`/`high` says
"already at ceiling," it never fabricates `opus`/`max`), so `max` is
parsed and counted here but never a tier telemetry recommends escalating
TO.

## Routing-tuning recommendations (Evolve analogue) — 2026-07

Response to fg-a10102. `tools/telemetry.py --recommend` builds ON the
Telemetry vocabulary aggregates above — same Routing-record and Attempt-log
parsing, no new grammar — to surface routing pairings that look mistuned,
strictly as a proposal a human reviews, never a self-applying change.

**Thresholds (canonical; changeable only by a human editing this section).**
A `(agent slug, routed tier)` pairing **qualifies** when BOTH hold:

- **dispatches ≥ 5** — the pairing's task count (each task counted once, at
  the tier named by its OWN attempt-1 Routing-record entry) meets or exceeds
  five, so a recommendation is never fired off two or three unlucky tasks.
- **first-attempt FAIL-or-bounce rate ≥ 40%** — of that pairing's dispatches,
  the fraction whose attempt 1 either verified FAIL or triggered a bounce
  (Telemetry vocabulary's `parse_attempt_log` primitives, unchanged) is 40%
  or higher.

Both numbers are hard-coded in `tools/telemetry.py` as
`RECOMMEND_MIN_DISPATCHES` (5) and `RECOMMEND_MIN_FAIL_RATE` (0.40) —
keep the constants and this paragraph in sync; a change to either requires a
human editing this section (and the constants) directly, never an automated
adjustment from a recommendation itself.

**Qualification formula.** For each `(slug, tier)` pairing:
`fail_or_bounce / dispatches >= 0.40 AND dispatches >= 5`. A qualifying
recommendation always states its counts alongside the verdict — see the
honesty rule below.

**Suggested next tier.** A qualifying recommendation suggests the next tier
UP the routed ladder `haiku -> sonnet -> opus` (effort held constant while
the model bumps); once already at `opus`, it suggests the next effort UP
`low -> medium -> high` instead. **The ceiling is hard-coded at `opus`/`high`
— `fable` is never a recommendation target,** the same rule as "Model
vocabulary — fable amendment (2026-07-17)" above (`fable` is a human-
authorized escalation, never a route a router or a recommendation engine
selects on its own). When a pairing is already at `opus`/`high` and still
qualifies, the recommendation says so plainly — "already at ceiling —
investigate task-class instead" — rather than fabricating a tier that
doesn't exist.

**Delta format + human-only ratification.** A qualifying recommendation is
recorded as an **UNRATIFIED delta** in
`docs/specs/2026-07-16-forge-design.md`'s `## 17. Changelog` section, in the
exact same format every other spec delta there already uses: `### Proposed
delta — <date> — from <task-id> — UNRATIFIED`, prose describing the
recommendation (pairing, counts, suggested next tier), ending "This delta is
a proposal only — spec truth is unchanged until a human ratifies it at the
next spec interaction (§9.4)." Filing the delta is the entire effect of a
recommendation: the kernel that runs `--recommend` at LEARN (`forge:kernel`,
"Routing-tuning recommendations (Evolve analogue, fg-a10102)") never edits
the ROUTE + DISPATCH table, a task's Routing record, or `forge.md` itself —
ratification (or rejection) happens exclusively through the pre-existing
`/forge:spec` delta-ratification flow, the identical human gate every other
spec delta already goes through. No toggle, budget, or standing-consent
setting shortcuts this gate.

**Honesty rule.** `--recommend` never reports a bare verdict — every
recommendation block prints its underlying counts (dispatches,
fail-or-bounce count, rate) alongside the suggested next tier, and a run
that finds no qualifying pairing prints `no recommendations` plus the two
thresholds themselves, so "nothing to recommend" is always distinguishable
from "the thresholds are unknown."

## Token capture — 2026-07-19 (fg-a10212)

NORMATIVE. Response to fg-a10209 audit recommendation 1 (the relative-cost
model in `docs/audits/2026-07-18-protocol-overhead-audit.md`, A.3, is a
labeled ESTIMATE because "no per-spawn token counts exist anywhere in the
record" — the harness DOES report token usage at subagent-spawn
completion). Amends "Telemetry vocabulary — 2026-07" (above): every
dispatch / verify / re-verify / bounce Attempt-log line — the same four
shapes that section's "Attempt log line shapes" enumerates — grows an
OPTIONAL trailing suffix:

- `[tokens: <N>]` — the harness-reported token count for that spawn's
  completion (build, verify, re-verify, ship-judge, finder, or refuter),
  digits only.
- `[tokens: unreported]` — the spawn completed but the harness reported no
  number; recorded explicitly, never omitted, never invented.

The suffix is appended by whichever actor writes that Attempt-log line
(kernel, worker, ship-judge, finder, refuter) once the spawn returns — one
suffix per line, trailing whatever content that line shape already carries.

**Backward compatibility (coverage honesty).** A line carrying NO suffix at
all parses EXACTLY as it did before this amendment — the base four line
shapes are unchanged; this is a pure addition, the same discipline as
"Finding severity + confidence — 2026-07-18 (fg-a10911)"'s judge-yield
suffix. A suffix that IS present but malformed (non-numeric, empty, missing
the closing bracket, any keyword other than a bare integer or `unreported`)
fails the WHOLE line, which falls into the unparsed tally rather than a
silent partial parse — mirroring JUDGE_YIELD_RE's strict-whole-match
discipline exactly.

**`tools/telemetry.py`.** `TOKEN_RE` matches the strict suffix grammar; a
companion loose pattern distinguishes "no suffix present" (line untouched)
from "suffix-shaped but malformed" (whole line -> unparsed) — the
malformed/absent distinction the base four regexes never needed until now.
`parse_attempt_log` strips a well-formed suffix before running the existing
DISPATCH_RE/VERIFY_RE/BOUNCE_RE checks, so those regexes see identical
input whether or not this amendment applies to a given line. `aggregate`
sums MEASURED token totals per layer — build (dispatch lines), verify
(verify + re-verify lines), bounce (bounce lines) — and per agent-slug,
using the SAME Routing-record slug attribution `agent_dispatch_counts`
already applies (a task's totals are added to every slug its Routing
record names, not re-derived per-attempt). An explicit `[tokens:
unreported]` suffix is tallied separately from a line that simply carries
no suffix at all — the former is recorded absence, the latter is legacy
data that predates this amendment; the two are never conflated.

**Report and `--json` fields — measured, never estimated.**
`report["tokens"]` carries `measured` (per-layer + total, real harness
numbers only), `unreported` (count of explicit `[tokens: unreported]`
spawns), `lines_with_tokens` (numeric + unreported suffix lines), and
`per_slug`. These render labeled MEASURED everywhere they appear
(`render_table`'s "Token usage — MEASURED, not the legacy relative-cost
estimate" heading) specifically so they are never confused with the
audit's relative-weight ESTIMATE table (`docs/audits/2026-07-18-protocol-
overhead-audit.md`, A.3) — `tools/telemetry.py` has never computed that
estimate and does not start computing it here; this amendment converts
real spawns from unmeasured to measured one line at a time, it does not
retrofit historical Attempt-log lines that predate it.

## Provider dispatch labels — 2026-07-22

Response to `provider-dispatch-labels` (user 2026-07-21: "does it show
that it is vera being spawned and it is a codex model like 5.6 sol
doing the work?"). Extends "Dispatch display labels — role-label
amendment — 2026-07-18" and "Telemetry vocabulary — 2026-07" (both
above) to external-provider dispatches, which those sections never
covered — a codex judge or worker fills the same panel slot / role a
Claude `forge-*` agent would (`skills/kernel/references/
provider-judges.md` §1, §7), so it gets a label too, PLUS the provider
identity the in-harness label has no field for.

**Label format — provider dispatches.** A provider dispatch's display
label is `<Persona> — <role> — <provider>/<model-slug> — <task name>`,
e.g. `Vera — co-verifier — codex/gpt-5.6-sol — auth-session hardening`.
This is a DISTINCT shape from the in-harness `<Persona> (<role>)`
format ("Dispatch display labels — role-label amendment," above) — a
provider dispatch adds the provider/slug field the in-harness format
has no need for, and keeps the task name because a provider dispatch
does not sit inside the harness's own runner-UI task column the way an
in-harness agent-type prefix does ("Harness agent-type prefix is not
the Forge label," same section). Fields:

- **Persona** — the SAME slug -> persona table ("Dispatch display
  labels — persona amendment," above) a Claude agent filling the
  identical panel slot would carry: a codex co-verifier composing into
  the `forge-verifier` slot (`provider-judges.md` §1) is labeled Vera,
  a codex `role-plan-refuter` labeled Blue (forge-architect's
  persona), a codex `role-spec-review` labeled Quill
  (forge-spec-writer's persona), a codex `role-worker` labeled Brokk
  (forge-worker's persona) — the persona names WHO the dispatch is
  standing in for, never a new provider-specific persona.
- **Role** — the profile role key the dispatch fills
  (`operator-profiles.md`'s Providers-domain schema), stripped of its
  `role-` prefix: `co-verifier`, `plan-refuter`, `spec-review`,
  `worker`. This is deliberately the role KEY, not the generic
  persona -> role word ("Dispatch display labels — role-label
  amendment," above uses "verify" for Vera) — a provider dispatch's
  role field names which of the four provider-profile slots it
  occupies, since that is the fact a human needs to tell a codex
  co-verifier apart from a codex worker at a glance.
- **`<provider>/<model-slug>`** — the provider id and the EXACT string
  passed to `-m` for this dispatch (`provider-judges.md` §2) — never a
  family name, a remembered slug, or a rounded/informal name like
  "codex" alone or "gpt-5". See "Telemetry never-invent-a-number
  extends to model identity," below.
- **Task name** — the same short human task name every other human
  surface uses ("Dispatch display labels — task-name amendment,"
  above): the task's filename slug, id trailing in parens where the
  surface already does that.

**Swarm disambiguation still applies.** A provider dispatch that is
part of a sharded fan-out gets the same `#N` instance number the
in-harness swarm rule already defines ("Dispatch display labels —
role-label amendment," above), inserted between persona and role:
`<Persona> #N — <role> — <provider>/<model-slug> — <task name>`.

**Telemetry never-invent-a-number extends to model identity.** WHEN a
provider dispatch is recorded in telemetry or a task's Routing record,
THE SYSTEM SHALL name the provider AND the exact model slug used — the
literal string passed to `-m` for that dispatch, read back from the
dispatch invocation itself, never "an external model," never a slug
recalled from memory or from a DIFFERENT dispatch's line. This is the
same discipline "Token capture — 2026-07-19 (fg-a10212)" (above)
already applies to token counts (`[tokens: unreported]` recorded
explicitly rather than omitted or guessed) — extended here from
numbers to model identity strings. A Routing record line for a
provider dispatch is the same `attempt N: <slug> — <model>/<tier> —
<rationale>` shape "Telemetry vocabulary — 2026-07" (above) already
defines, with `<model>` populated as `<provider>/<model-slug>` instead
of a Claude model name — e.g. `attempt 1: codex — codex/gpt-5.6-sol/
judgment — role-co-verifier panel slot`. The Judge-yield line
(`provider-judges.md` §5) already carries this discipline for its own
`codex:<agent-slug>` prefix; this section states the same requirement
for the label and Routing-record surfaces that section's telemetry
rule does not itself cover.

**Blocked/degraded dispatches use the same labeled voice.** WHEN a
provider-side dispatch degrades or is blocked (Feature off, trust
marker absent, toggle off, cap reached), THE SYSTEM SHALL say so in
the same labeled voice a present dispatch gets, so absence is as
visible as presence — never a bare silent skip. This is not a new
message shape: `provider-judges.md` §1a's `provider-gate-blocked:
codex layer=<layer> — <reason>` line (cited here, not restated) IS
that labeled voice for the four-layer gate, and §4's one-stated-note
graceful-degrade shape is where it surfaces to the human.

**Resolution order — model + reasoning effort choosability
(provider-dispatch-labels, 2026-07-22).** WHEN a codex dispatch (Phase
1 judge or Phase 2 worker) is prepared, THE SYSTEM SHALL make its `-m
<slug>` and `-c model_reasoning_effort=<effort>` values explicitly
choosable, resolved in this order — never an unstated hardcode:

1. **Task routing override** — forge.md's `## Routing overrides`
   section (`settings-schema.md`, "Routing overrides"), checked
   FIRST, the same override-first spot `skills/kernel/SKILL.md`'s
   ROUTE step already checks for Claude dispatches.
2. **Class-based routing vocabulary** — the dispatching task's
   MECHANICAL/JUDGMENT class (`docs/conventions/verification.md`'s
   FAIL-NOTES tag vocabulary) or, for a Phase 1 judge, whether its
   role is one of the adversarial-judge roles `provider-judges.md`
   §1's equal-or-higher floor already names (`role-co-verifier`,
   `role-plan-refuter`): MECHANICAL resolves effort to the recorded
   per-provider default effort (step 3, below); JUDGMENT, or any
   adversarial-judge role, resolves effort to `high` — or to a
   §3 role pin's pinned effort where that is HIGHER (the pin
   implements spec-e8a3's equal-or-higher floor; `high` never lowers
   an `xhigh` pin). Where `provider-judges.md` §3 already pins a
   specific model for a role (co-verifier / plan-refuter ->
   `codex-tier-judgment`), that existing pin satisfies this step
   directly and is not overridden by step 3's general default.
   **Pin-staleness trigger**: WHEN a newer `codex-default-model` is
   recorded than the catalog snapshot a §3 pin was taken from, the
   pin SHALL be re-verified against the live catalog before the next
   dispatch under that role — model availability is CLI-version-
   dependent (observed 2026-07-22: `gpt-5.6-sol` required a CLI
   upgrade the §3-era snapshot predated), so a stale pin can name a
   model the installed CLI serves differently or not at all.
3. **Recorded per-provider defaults** — the floor every dispatch with
   no routing override and no role-specific pin falls back to:
   `codex-default-model: gpt-5.6-sol`, `codex-default-effort: medium`
   (owner-set 2026-07-22, floor-flag: no — the orchestrator MAY
   override per dispatch via step 1 or 2 above), recorded in
   `skills/kernel/references/settings-schema.md`'s Providers table
   and surfaced by `/forge:settings`' Providers view
   (`commands/settings.md`).

Every dispatch's chosen `-m`/`-c model_reasoning_effort=` pair traces
to exactly one of these three steps — the choice itself is recorded
alongside the label and Routing-record slug this section already
requires, so a human reading the Attempt log can see which step
resolved a given dispatch's model and effort, never merely the
resulting values with no resolution trail.

## Consensus escalation labels — 2026-07-22

Implements `docs/specs/2026-07-22-cross-model-consensus.md`'s labeling
half of AC C. Extends "Provider dispatch labels — 2026-07-22" (above)
to the plan consensus escalation
(`skills/kernel/references/provider-judges.md`, "10. Plan consensus
escalation — 2026-07-22 (spec cross-model-consensus)") — cited, not
restated: this section states only the escalation-specific label
content that existing section's `<Persona> — <role> — <provider>/
<model-slug> — <task name>` shape has no field for.

**Label format — consensus dispatches.** A plan-consensus-escalation
dispatch's display label carries the round marker in the `<role>`
field's place, in the shape `<Persona> — plan-refuter — <provider>/
<model-slug> — <plan name> — round <Cn>`, e.g. `Blue — plan-refuter —
codex/gpt-5.6-sol — cross-model-consensus — round C2`. `<plan name>`
is the same short human task-name convention "Dispatch display labels
— task-name amendment — 2026-07-18" (above) already uses, applied to
the spec/plan file's basename rather than a queue task's filename
slug. `round <Cn>` is `C1` or `C2` exactly — never `R1`/`P1`, which
name Claude's own revision/re-proposal steps, not advisor critiques,
and are never dispatch-labeled since they are not provider
invocations.

**Every invocation, including retries, gets its own tally line.** Per
`provider-judges.md` section 10.3 and 10.6 (retry-then-force extended
to the plan-refuter judge role, every retry counted as a distinct
provider CLI invocation against section 7.6's dispatch tally), THE
SYSTEM SHALL emit one tally line per invocation, never one line per
critique — a malformed-output retry under `C2` is its own line, tagged
`round C2 retry <n>` (`n` = 1 or 2, section 10.3's retry cap), so the
Attempt log's invocation count matches the actual CLI-call count
exactly, closing the same "one critique is not one dispatch" loophole
`provider-judges.md` section 10.3 states in prose. A clean `C1` with no
escalation and no retry emits exactly one tally line, matching the
"a clean plan costs exactly one advisor dispatch, ever" floor
(`docs/specs/2026-07-22-cross-model-consensus.md`, Goal).

## Consensus rollout telemetry — 2026-07-22

NORMATIVE. Once a plan consensus escalation completes, its `## Plan consensus
record` carries exactly one parser-owned summary line:

`consensus-rollout: c1-rejects=<N> c1-resolved=<N> c2-rejects=<N> c2-resolved=<N> cap-out=yes|no baseline-cost=<N> consensus-cost=<N> baseline-latency-ms=<N> consensus-latency-ms=<N>`

All reject/resolved counts are P0/P1 decision ids. Cost is provider CLI
invocations (including retries); latency is elapsed wall-clock milliseconds.
`tools/telemetry.py` reads only this strict summary, so malformed or duplicate
lines yield no rollout observation rather than fabricated zeroes.

- **Cap-out rate** is `cap-outs / escalations`: an escalation cap-outs only
  when C2 leaves at least one P0/P1 id outstanding.
- **Per-critique judge yield** is `resolved / rejects`, separately for C1 and
  C2, showing which critique closes disputed decision ids.
- **Cost and latency vs single-pass baseline** compare the summed consensus
  invocation count and elapsed time against the one-advisor-pass baseline;
  the report includes totals, delta, and ratio, never an estimate.

**Initial values pending evidence — promotion / rollback.** Treat these as
starting review thresholds, not self-executing routing changes: promote the
escalate-only rollout only after at least 20 escalations with cap-out rate at
or below 15% and C2 judge yield at or above 60%; propose rollback or human
review after 20 escalations if cap-out rate exceeds 30%, C2 yield stays below
25%, or median cost or latency is more than 3x the single-pass baseline.
Any action remains a human-ratified LEARN/spec delta.
