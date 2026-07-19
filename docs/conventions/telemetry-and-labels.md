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

