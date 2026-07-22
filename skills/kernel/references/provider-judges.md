# Provider judges — Phase 1 dispatch mechanics (reference)

NORMATIVE. Implements Phase 1 of `.forge/specs/2026-07-19-provider-profiles.md`
(spec-e8a3), section "Phase 1 — external judges (read-only)", for the
`role-plan-refuter`, `role-spec-review`, and `role-co-verifier` keys
`skills/kernel/references/operator-profiles.md`'s "Providers domain: schema
(fg-c0101)" already schemas. This file is the mechanics `fg-c0101` explicitly
deferred here and `skills/kernel/SKILL.md`'s VERIFY step and
`skills/spec/SKILL.md`'s composition point cite rather than restate. It
ships NO dispatch code of its own kind that mutates the tree — Phase 1 is
read-only judges only. Phase 2 worker dispatch is now built (section 7
below); as of 2026-07-22 (`bm-atomic-doc-fix-canonical-route`) a resolved
`role-worker` provider is R1's automatic-default builder route for eligible
tasks — the `provider:` task field is an override, not the trigger.

## 1. Panel-member-type composition (fg-a10901 ceiling unmoved)

`docs/conventions/verification.md`, "Verification economics — 2026-07-18
(fg-a10901)", Panel policy: **at most one adversarial verifier per task**
(`forge-verifier`, or `forge-ui-verifier` for visual criteria; a genuinely
mixed code+visual task gets both — that pair is the ceiling, never a
panel). This task adds a new panel-member TYPE to that same ceiling; it
does not raise it.

WHEN the active operator profile's `role-co-verifier` resolves to `codex`
(the `providers` Feature is `on` for this repo AND codex's per-provider
trust marker, `.forge/.trust-providers/codex.local`, is present per
`docs/conventions/trust-and-security.md`, "Per-provider trust
confirmation — 2026-07-19 (fg-c0103, spec-e8a3)"), THE SYSTEM SHALL let a
codex judge fill the ONE panel slot fg-a10901 already caps — as a
replacement for, or an addition alongside, `forge-verifier` within that
same single-slot ceiling, never a second uncapped slot on top of it. A
mixed code+visual task's pair (`forge-verifier` + `forge-ui-verifier`)
counts as the ceiling already spent; a codex co-verifier composes into
that pair by taking one of the two existing slots, never adding a third.

The kernel's VERIFY step (`skills/kernel/SKILL.md`) resolves which slot a
codex judge occupies at the moment it would otherwise spawn `forge-verifier`
— this file defines the composition rule; VERIFY step wiring is that
file's own stub citing here.

### 1a. Per-provider toggle — additive fourth gate layer (provider-toggles, 2026-07-21)

Amends this section's own WHEN-clause above without removing or reordering
any of its three existing conditions. `docs/conventions/config-and-
features.md`, "Per-provider dispatch toggles" adds a fourth, independent
gate layer UNDER the `providers` Feature and per-provider trust marker
already named above: forge.md's own `## Providers` section (`- codex: on`,
`- grok: off`, ...). A codex judge fills the panel slot ONLY when ALL FOUR
hold, checked in this order:

1. the `providers` Feature is `on` for this repo;
2. codex's own forge.md `## Providers` toggle is `on` (a toggle absent from
   forge.md, or the whole `## Providers` section absent, resolves to OFF —
   the one place in forge.md config where a missing key does NOT mean
   default-on, mirroring the `providers` Feature's own default-off
   posture);
3. codex's per-provider trust marker
   (`.forge/.trust-providers/codex.local`) is present;
4. the dispatch cap (`max-provider-dispatches-per-session`, section 7.6
   below) has headroom.

Any one layer unmet blocks the dispatch with exactly one labeled line
naming which layer blocked it, never a bare refusal:

```
provider-gate-blocked: codex layer=<layer> — <reason>
```

where `<layer>` is one of `global-feature` (layer 1), `provider-toggle`
(layer 2), `trust-marker` (layer 3), or `dispatch-cap` (layer 4). A blocked
dispatch degrades exactly per section 4's graceful-degrade shape below —
the panel runs Claude-only with this labeled line as its one stated note,
never a silent skip, never a block waiting for the provider.

**Toggling off never clears trust.** Setting codex's forge.md toggle to
`off` (layer 2) leaves `.forge/.trust-providers/codex.local` (layer 3)
untouched — re-enabling the toggle later does not re-prompt the trust
confirmation, same additive-record behavior the `providers` Feature itself
already guarantees (`docs/conventions/config-and-features.md`, "Both gates
are independent and both must hold").

**Pilot gates are never overridden by a toggle.** `grok` and `antigravity`
stay undispatchable pending human pilot-evidence review
(`bm-grok-pilot-test` / `bm-antigravity-smoke-test`) regardless of what
their forge.md `## Providers` toggle says — a toggle set to `on` for a
pilot-gated provider is accepted and stored (same "accepted and stored,
never itself the thing that clears the gate" posture `operator-
profiles.md`'s `enabled-providers` already states) but never itself
dispatches; the pilot gate is checked independently of, and in addition
to, the four layers above.

**Pilot-clearance mechanism — 2026-07-22.** A pilot gate is cleared only
when `.forge/.trust-providers/<provider>.pilot-cleared.local` is present.
This marker is in the same machine-local, never-committed, gitignore-covered
family as the TOFU markers. It is written ONLY by `/forge:settings` after
the human reviews pilot evidence through the structured clearance question,
which shows the applicable evidence path
(`docs/pilots/2026-07-19-grok-pilot.md` or `docs/pilots/2026-07-19-antigravity-smoke.md`); a settings edit
NEVER writes the marker without that flow. An absent marker means the pilot
gate is closed.

## 2. Dispatch shape — Codex CLI (Codex CLI 0.137.0, pinned 2026-07-20)

Pinned invocation shape, matching `.forge/specs/2026-07-19-provider-
profiles.md`'s "Provider-specific enablement gates" AC and
`docs/conventions/verification.md`'s "External-provider dispatch rules —
2026-07-19 (fg-c0112, spec-e8a3)" JSON/JSONL-only rule:

```
codex exec --json -o <output-file> -m <model-slug> -c model_reasoning_effort=<effort> \
    --sandbox read-only "<judge prompt>"
```

- `--json` — print events to stdout as JSONL. The kernel captures this
  stream (or discards it) but NEVER treats it as the verdict source of
  truth.
- `-o, --output-last-message <FILE>` — the final-message capture file. THE
  SYSTEM SHALL parse ONLY this file's contents (or the structured JSONL
  stream, never a scraped TTY transcript) as the judge's verdict/findings
  payload — the same JSON/JSONL-only capture rule fg-c0112's docs section
  already states, restated here as this task's own binding mechanics.
- `-m, --model <MODEL>` plus `-c model_reasoning_effort=<effort>` — tier
  resolution (section 3 below); Codex CLI 0.137.0 has ONE model dimension
  (`-m`) crossed with a separate reasoning-effort dimension (`-c
  model_reasoning_effort=...`), not two distinct model IDs per tier the
  way the schema's `<provider>-tier-mechanical` / `<provider>-tier-
  judgment` key PAIR implies — both keys are still populated (section 3),
  one naming the model slug, its effort level folded into the same
  resolved string.
- `--sandbox read-only` — Phase 1 judges never write to the tree; this is
  the read-only contract's enforcement flag, not merely a description of
  intent. Phase 1 dispatch NEVER uses `workspace-write` or
  `--dangerously-bypass-approvals-and-sandbox` — the latter is
  categorically forbidden for every provider profile regardless of phase
  (`docs/conventions/trust-and-security.md`, "Provider dispatch security
  rules — 2026-07-19 (fg-c0112, spec-e8a3)").
- `--skip-git-repo-check` — Phase 1 judge dispatch runs inside the
  kernel's own worktree/repo context (never a bare non-repo directory), so
  per spec-e8a3's own AC this flag is treated as UNNECESSARY and never
  added by default; listed here only to record that this task's dispatch
  shape does not add it, not to recommend it.

**Read-only contract.** A Phase 1 codex judge dispatch produces a
verdict/findings payload ONLY — it never writes to the worktree, never
runs `git commit`/`git add`, and never invokes any codex subcommand beyond
`exec` with the flags above. `--sandbox read-only` is the enforcement
mechanism; a dispatch helper that ever passes `workspace-write` or the
full-bypass flag for a Phase 1 judge role is a defect against this
section, not a valid degrade.

**Label + slug recording at dispatch time (provider-dispatch-labels,
2026-07-22).** Amends this section without reordering or restating any
flag above. WHEN this dispatch shape is invoked for a labeled panel
role, THE SYSTEM SHALL record, at the moment `-m <model-slug>` is
resolved, both (a) the dispatch's display label in the `<Persona> —
<role> — <provider>/<model-slug> — <task name>` shape
(`docs/conventions/telemetry-and-labels.md`, "Provider dispatch labels
— 2026-07-22") and (b) the exact slug in the task's Routing record /
Attempt log (same section's telemetry rule) — never a label or record
written before `-m`'s value is known, and never a slug string other
than the literal one passed to this invocation.

## 3. Tier resolution — model IDs pinned at implementation time

> Amended by section 9 (2026-07-22): the tier map below is the historical record; section 9's re-pin governs.

Per spec-e8a3's "Role-based provider assignment and tier map" AC and
`operator-profiles.md`'s Providers-domain schema ("Provider tier-map
keys" — `<provider>-tier-mechanical` / `<provider>-tier-judgment`, values
implementation-pinned, never hardcoded from spec text or training
knowledge): Codex CLI 0.137.0 ships NO dedicated non-interactive
model-listing subcommand (`codex --help`, `codex features list --help`,
`codex login --help` checked 2026-07-20 — none exposes one). The values
below are pinned instead from the CLI's OWN locally-cached model catalog
that the installed CLI itself fetched and maintains —
`$CODEX_HOME/models_cache.json` (`fetched_at: 2026-07-20T18:13:05Z`,
`client_version: 0.137.0` in the cache file read for this pin) — a
genuine live-CLI artifact, not a value read from spec text, docs, or
training-data recall. A future re-pin SHOULD prefer a real model-listing
subcommand if a later Codex CLI version ships one; until then, this
cache-file read is the CLI's own live listing.

```
- codex-tier-judgment: gpt-5.5 (model_reasoning_effort=xhigh)
- codex-tier-mechanical: gpt-5.4-mini (model_reasoning_effort=medium)
```

- `gpt-5.5` — catalog `description`: "Frontier model for complex coding,
  research, and real-world work"; `default_reasoning_level: xhigh`;
  catalog `priority: 7`, the lowest (best) priority number of any
  non-review model in the cache — matches spec-e8a3's "JUDGMENT routes to
  its frontier tier" requirement on its own catalog wording, not an
  inference from the model name.
- `gpt-5.4-mini` — catalog `description`: "Small, fast, and cost-efficient
  model for simpler coding tasks"; `default_reasoning_level: medium`;
  catalog `priority: 23` — matches "MECHANICAL routes to that provider's
  cheap/mini tier."
- `codex-auto-review` (catalog `priority: 43`, "Automatic approval review
  model for Codex") exists in the same catalog but is NOT selected for
  either tier: its own description scopes it to Codex's internal
  auto-approval review flow, not a general judge/second-opinion role — a
  false match on the word "review" would misuse a narrow-purpose model for
  this task's judge roles.

**Equal-or-higher floor.** Both `role-co-verifier` and `role-plan-refuter`
are named by spec-e8a3's equal-or-higher clause ("a provider-assigned
judge for a JUDGMENT-tier or `tier: full` role resolves to that provider's
frontier/highest tier, never its mechanical/mini tier") — every codex
dispatch under either role resolves to `codex-tier-judgment` (`gpt-5.5`),
never `codex-tier-mechanical`, regardless of the dispatching task's own
tier field.

**KERNEL RULING — role-spec-review tier (recorded, not relitigated).**
`operator-profiles.md`'s "Providers domain: schema (fg-c0101)" flagged an
unverified interpretation and asked this task to confirm it before wiring
dispatch. CONFIRMED: spec-e8a3's equal-or-higher WHEN-trigger names only
"a cross-model co-verifier or second opinion" — i.e. `role-co-verifier`
and `role-plan-refuter` — as required to resolve to frontier tier for a
JUDGMENT-tier or `tier: full` role. `role-spec-review` is a distinct role
outside that floor: it is a read-only advisory pass feeding the human
spec-approval gate, which remains the authoritative, un-skippable floor
regardless of what tier judged it. **Ruling: spec-review MAY run at
mechanical tier; co-verifier and plan-refuter judge roles MUST resolve to
frontier/judgment tier.** This confirms the `budget-tiers` preset's
`codex-tier-mechanical` assignment for `role-spec-review` in
`operator-profiles.md` as valid and does not change it.

## 4. Graceful-degrade (mirrors profile-wiring.md §5's advisory\|verdict framing)

`skills/kernel/references/profile-wiring.md` §5, "Provider-review
graceful-degrade": WHEN no provider is enabled or available, the gate
degrades to a human-only gate with one stated note — never silently skip,
never block waiting for the provider. This section applies that identical
shape to every Phase 1 judge role:

WHEN `providers` is `off`, OR codex is not named in the active profile's
`enabled-providers`, OR codex's per-provider trust marker
(`.forge/.trust-providers/codex.local`) is absent, THE SYSTEM SHALL run
the panel exactly as it would with no provider judge configured at all
(Claude-only: `forge-verifier`/`forge-ui-verifier` alone for
`role-co-verifier`, a single Claude architect for `role-plan-refuter`, no
extra pass for `role-spec-review`) and add exactly ONE stated note to the
verdict/plan/spec presentation naming which provider role was configured
and why it did not participate (e.g. "role-co-verifier: codex configured,
but providers is off — panel ran Claude-only"). A missing or unavailable
codex is NEVER a reason to skip the gate entirely, and NEVER a reason to
block progress waiting for codex to become available — the panel proceeds
Claude-only with that one note, same turn, no pause.

**Provider-toggle layer folds into the same note (provider-toggles,
2026-07-21).** Section 1a above adds forge.md's own per-provider toggle as
a fourth gate layer. WHEN that layer is the one that blocked (codex's
forge.md toggle is `off` or absent while the other three layers would
otherwise pass), THE SYSTEM SHALL use the same one-note graceful-degrade
shape this section already defines, with section 1a's labeled
`provider-gate-blocked: codex layer=provider-toggle — ...` line as that
note's content — no second degrade path, no new note format.

## 5. Judge-yield telemetry — provider-distinguishable slug

`docs/conventions/verification.md`, "Verification economics — 2026-07-18
(fg-a10901)", Judge-yield telemetry: `judge-yield: <agent-slug>
raised=<N> survived=<M> changed=<K>`. A codex judge's Attempt-log line
uses a provider-prefixed slug, `codex:<agent-slug>` (e.g.
`judge-yield: codex:forge-verifier raised=2 survived=1 changed=1`) — the
SAME line shape, a provider-qualified slug value, never a new line
grammar. `tools/telemetry.py` parses the provider prefix and aggregates it
BOTH under the exact slug (backward-compatible with every existing
per-slug consumer) AND under a separate per-provider bucket
(`report["judge_yield_by_provider"]`) distinct from per-Claude-agent
yield, so a demoted-or-promoted-by-evidence decision (fg-a10901's own
data-ruled-both-directions rule) can compare codex's aggregate yield
against Claude's without hand-filtering slugs.

## 6. Non-goals of this file

Phase 2 worker dispatch (`provider:` field routing, worktree-scoped
mutation) is now built — section 7 below (`fg-c0111`,
`bm-provider-worker-dispatch`), not a separate future task anymore. No
changes to `tools/validate_config.py`'s Providers-domain validation scope
(still out of scope per `operator-profiles.md`'s "Validation scope"
section). No new provider besides codex — grok and antigravity stay
pilot-gated exactly as `operator-profiles.md`'s "Providers domain: schema
(fg-c0101)" already states; section 7 adds no dispatch mechanics for
either beyond the same gate check codex itself passes.

## 7. Phase 2 — external worker dispatch (fg-c0111)

Implements Phase 2 of `.forge/specs/2026-07-19-provider-profiles.md`
(spec-e8a3), section "Phase 2 — external workers", for the `role-worker`
key `operator-profiles.md`'s Providers-domain schema already names but
leaves Phase-2-gated ("no dispatch path reads it until the... Phase 2
external-worker task ships"). This section is that task: it un-gates
`role-worker` by defining the mechanics a dispatch-time consumer follows.

### 7.1 Route gate — role-worker automatic-default (R1), provider: as override

R1 (`docs/specs/2026-07-22-phase2-external-workers.md`, "R1 (RESOLVED) —
role-worker is the automatic default; provider: is the override",
RESOLVED by human ruling 2026-07-22): `role-worker`'s resolution to a
provider IS the default BUILDER route for an ELIGIBLE task — no per-task
`provider:` field is required to activate it. A task is ELIGIBLE when it
passes `tools/route_table.py`'s canonical `precedence_chain()`: not
classified sensitive-domain (chain step 2) and passing every provider
gate (chain step 3). This section states the CONDITIONS below; it never
restates the chain's STEP ORDER, which lives solely in
`tools/route_table.py` — read that module, do not re-derive it here.

**Automatic default (chain step 4).** WHEN the kernel's ROUTE step
assigns a BUILDER for a task, THE SYSTEM SHALL treat the active
profile's `role-worker` resolution to a provider (not `claude-only`) as
that task's DEFAULT builder route whenever ALL of the following hold,
checked at ROUTE:

- the active profile's `role-worker` resolves to that provider (not
  `claude-only`);
- the `providers` Feature is `on` for this repo
  (`docs/conventions/config-and-features.md`, "Providers Feature");
- that provider's per-provider trust marker
  (`.forge/.trust-providers/<provider>.local`) is present
  (`docs/conventions/trust-and-security.md`, "Per-provider trust
  confirmation");
- for `grok` or `antigravity`, the provider's pilot gate
  (`bm-grok-pilot-test` / `bm-antigravity-smoke-test`) has been
  human-reviewed and cleared — `codex` carries no such pilot gate
  (`operator-profiles.md`, "Providers domain: schema").

Any one condition unmet: `role-worker`'s resolution is inert for this
dispatch and the task routes to a Claude `forge-worker` exactly as if
`role-worker` resolved to `claude-only` — the same graceful-degrade shape
`profile-wiring.md` §5 already establishes (one stated note, never a
silent skip, never a block waiting for the provider).

**`provider:` is an override, never a required conjunct (chain step
1).** WHEN a task's frontmatter carries a `provider:` field, THE SYSTEM
SHALL treat it as an OVERRIDE of the automatic default above for that
task only — NOT as an additional precondition role-worker's resolution
needs in order to take effect. `provider: <name>` requests that specific
provider, subject to the same four conditions listed above; on an
ORDINARY (non-sensitive-domain) task the field alone is sufficient to
route to that provider, no elevated authorization required. `provider:
claude-only` always forces an in-harness Claude builder, on any task,
sensitive or not, with no elevated provenance needed. WHEN `provider:
<name>` names an external provider on a task classified
sensitive-domain, THE SYSTEM SHALL require a valid, unconsumed, matching
un-forgeable authorization envelope before that override can cross the
carve-out below — the envelope mechanics themselves are
`bm-sensitive-override-provenance`'s scope, cited here, not built here.

**Sensitive-domain default outranks the automatic default (chain step 2
precedes step 4) — the whole safety story, stated explicitly.** A task
classified sensitive-domain by the fail-closed pre-dispatch classifier
(`bm-sensitive-classifier-backstop`, `sensitive-classifier.md`) defaults
its BUILDER to Claude regardless of what `role-worker`
resolves to, and this sensitive-domain default is checked at chain step
2 — BEFORE role-worker's automatic default at step 4 is ever reached.
R1's automatic-default therefore NEVER by itself crosses the
sensitive-domain carve-out: a sensitive-domain task never reaches step
4's automatic role-worker resolution at all unless step 1 already
supplied a valid crossing envelope. Ordinary (non-sensitive-domain)
tasks are the only tasks step 4's automatic default ever resolves.

Read `tools/route_table.py`'s `precedence_chain()` for the full
five-step order (step 1 override incl. the sensitive-provider-crossing
case, step 2 sensitive-domain default, step 3 provider gates, step 4
this section's automatic default, step 5 task-shape tie-break) — this
section states condition text only, never a second copy of that
ordering.

### 7.1a. Worker dispatches pass the SAME gate layers — 2026-07-22

A Phase-2 worker dispatch requires ALL of: the global `providers` Feature
on; that provider's own forge.md `## Providers` toggle on (missing = OFF);
the provider's TOFU trust marker present; the budget check per section 7.6
as amended; PLUS the pilot gate for `grok` or `antigravity`, proven open
only by `.forge/.trust-providers/<provider>.pilot-cleared.local` (an absent
marker means the pilot gate is closed). These layers are checked in
addition to section 7.1's profile-role resolution and `provider:` route
contract.

A toggled-off provider never dispatches as a worker regardless of profile
role resolution.

When any layer blocks a worker dispatch, use section 1a's
`provider-gate-blocked:` labeled-line format by citation; do not restate or
invent a second block format. The ordinary section 7.1 graceful-degrade to a
Claude `forge-worker` remains unchanged.

Every worker dispatch under this section ALSO executes section 8's skill-materialization contract and its INTEGRATE exclusion — section 8 is a REQUIRED step of worker dispatch, not an optional sibling.

### 7.2 Worktree isolation and Hard Rule 4 — identical to a Claude worker

WHEN a route-gated provider dispatch performs mutating work, THE SYSTEM
SHALL run it inside the SAME kernel-managed git worktree isolation an
in-harness Claude `forge-worker` would get — `skills/kernel/references/
parallel-dispatch.md`'s worktree mechanics apply unchanged, cited here,
not restated. Hard Rule 4 holds identically: the external worker never
touches `.forge/`; every `.forge/` write is kernel-only, on the main
branch, never inside the external worker's worktree. The worker never
commits — the kernel integrates the resulting diff per fg-a10815's shard
merge/verify/bisect/atomicity contract (`parallel-dispatch.md`, "Shard
merge, verify, bisect, atomicity (fg-a10815)") when the dispatch is part
of a batch/shard set, and per ordinary single-task INTEGRATE otherwise —
no new merge path is introduced for external workers.

### 7.3 Dispatch shape — Codex CLI, workspace-write sandbox

Mutating Phase 2 dispatch differs from Phase 1's read-only shape (section
2 above) only in the sandbox/approval flags:

```
codex exec --json -o <output-file> -m <model-slug> -c model_reasoning_effort=<effort> \
    --sandbox workspace-write --ask-for-approval never "<worker prompt>"
```

`--sandbox workspace-write --ask-for-approval never` is the auto-approve/
workspace-sandbox PAIRING `docs/conventions/trust-and-security.md`'s
"Provider dispatch security rules" requires — `--dangerously-bypass-
approvals-and-sandbox` is categorically forbidden here exactly as it is
for every provider profile, Phase 1 or 2.

**WSL2 preference on Windows.** WHEN this dispatch runs on Windows, THE
SYSTEM SHALL prefer WSL2 for the dispatch, per the Phase 0 research
verdict that Codex's native Windows sandbox is EXPERIMENTAL; WHEN WSL2 is
unavailable, THE SYSTEM SHALL fall back to `--sandbox workspace-write`
with an explicit stated caveat in the dispatch note and session report
that the native sandbox is experimental on this platform — never
silently treated as equivalent to the WSL2 path.

### 7.3a Status-line dispatch marker — visibility only (2026-07-22, bm-atomic-doc-fix-canonical-route)

External background dispatches (`codex exec`, etc.) appear to the harness
as background shell tasks, NOT as native Claude subagents — so they never
show up in the agent-activity widget the way in-harness workers do. To
make them visible in a custom status-line command WITHOUT wrapping the
dispatch in a babysitter Claude agent (which would defeat the token
savings of routing externally), THE SYSTEM SHALL maintain a
visibility-only marker file per live external dispatch:

- **On launching** an external background dispatch: (a) ensure
  `.forge/.active-dispatches/` exists, creating it with a self-ignoring
  `.gitignore` (first line `*`, second line `!.gitignore`) if absent so
  markers never enter git in any project; (b) delete any marker file in
  that directory older than 30 minutes (stale-leak self-heal — a crashed
  prior session's markers are purged by the next dispatch); (c) write
  `.forge/.active-dispatches/<task-id>` containing exactly one line, the
  display string `<provider> <model>/<effort>` (e.g. `codex sol/high`).
- **On the dispatch reaching ANY terminal outcome** — integrated, bounced,
  blocked, or failed — THE SYSTEM SHALL delete that task's marker.

The marker is visibility-only: it NEVER gates dispatch, is never read by
any routing decision, and carries no authorization meaning. Removal on
terminal outcome plus the 30-minute pre-write purge bound leaks without a
separate sweep step. A status-line command reads these one-line markers
(filtering to those with a recent mtime) and appends them to its output —
that wrapper is user-machine config (settings.json `statusLine`), not
plugin state, so the plugin's only job is to keep the markers accurate.
Because external dispatches already log to the task's Routing record, this
marker adds a live view, never a second source of truth.

### 7.4 Output contract — retry-then-force, then bounce/blocked (not auto Claude-fallback)

JSON/JSONL-only capture (section 2 above; `docs/conventions/
verification.md`, "External-provider dispatch rules") applies
identically to Phase 2. Retry-then-force: re-prompt up to 2 times on
malformed output before the dispatch counts as failed.

**KERNEL RULING — fallback wording (recorded, not relitigated).** This
task's own spawn contract paraphrased the post-2nd-failure path as
"falls back to a Claude worker." Spec-e8a3's actual AC text ("Phase 2 —
external workers") reads: "WHEN an external worker's output fails the
output-contract retry-then-force protocol twice, THE SYSTEM SHALL treat
the dispatch as failed and fall through to the task's normal bounce/
blocked handling — never a silent partial-credit acceptance of malformed
external output." That is bounce/blocked handling, NOT an automatic
re-dispatch to a Claude worker — the kernel treats the task as any other
failed dispatch (bounce with the malformed-output failure noted in the
Attempt log; a human or a later session decides whether to re-route it
`claude-only`), never silently re-dispatching it to `forge-worker` in the
same breath. This file follows the spec's actual wording, not the
paraphrase.

### 7.5 Verification floor unmoved

A Phase 2 external worker's diff is verified by a Claude-side
`forge-verifier`/`forge-ui-verifier` at the task's normal equal-or-higher
tier, exactly as documented in `docs/conventions/verification.md`,
"External-provider dispatch rules" — no reduced protocol, no
provider-specific carve-out, the same VERIFY step (`skills/kernel/
SKILL.md`, section 6) any in-harness worker's diff goes through.

### 7.6 Budget accounting — provider-dispatch cap checked at ROUTE

WHEN this repo is at its `max-provider-dispatches-per-session` cap
(default 10; `docs/conventions.md`, "Budget keys — amendment
(2026-07-19): provider dispatch cap"), THE SYSTEM SHALL dispatch no
further Phase 2 external-worker builds this session — the task routes to
a Claude `forge-worker` instead (same graceful-degrade shape as section
7.1) — and states the capped state in the session report.

**Checkpoint-model amendment — 2026-07-22.** Since 2026-07-22 the shipped
default is the checkpoint model:
`max-provider-dispatches-per-session: none` plus `provider-dispatch-checkpoint-every: 10` (`docs/conventions.md`,
"Provider dispatch checkpoints — 2026-07-22"). The kernel keeps a running
provider-dispatch tally and, at every multiple of the checkpoint cadence,
posts the one-line checkpoint with per-provider counts and the exact model
slugs used, then continues unless the human objects. Provider rate-limit
errors are surfaced verbatim. A NUMERIC
`max-provider-dispatches-per-session` value retains the original hard-cap
semantics above unchanged.

**Visibility, not control — stated plainly.** The checkpoint cadence is a
VISIBILITY mechanism, not a stopping CONTROL: it never itself halts
dispatch, only reports and continues by default at every multiple of
`provider-dispatch-checkpoint-every`, and stops nothing on its own even
when the human does not respond to a posted checkpoint. The ONLY actual
stopping control is a NUMERIC `max-provider-dispatches-per-session` value
(the unamended paragraph above) — with the checkpoint model's shipped
`none` default, provider-dispatch count for the session is UNBOUNDED,
gated by nothing but the per-10 visibility report. A numeric cap remains
OPTIONAL: a human sets one explicitly when they want a hard stop instead
of unbounded dispatch with reporting (`docs/specs/
2026-07-22-phase2-external-workers.md`, "Budget — checkpoints are
visibility, not control; a real optional hard cap").

## 8. Skill materialization (codex-skill-loading, 2026-07-21)

Origin: `.forge/queue/tasks/codex-skill-loading.md` ("make sure that codex
can fully utilise the skills we have attached here since they live within
forge"). Research (provider research 2026-07-21, verified against the
installed codex-cli 0.137.0): Codex natively discovers Agent Skills from
two roots — `$CODEX_HOME/skills` (`~/.codex/skills`, OpenAI's own managed
bucket) and the cross-tool standard root `~/.agents/skills` (plus a
project-local `.agents/skills`, project taking precedence over user).
Discovery is automatic — no CLI flag triggers it — and `[[skills.config]]`
in `config.toml` can only enable/disable skills already discovered, never
add a root. Loading is lazy per the agentskills spec (name+description
metadata scanned first, a skill's body only read on trigger), but that
metadata pass is budgeted to roughly 2% of context or 8,000 characters,
whichever is smaller — Forge's ~60 skills carry roughly 29,200 characters
of descriptions, about 3.5x that budget, and overflow behavior at the
budget ceiling is UNDOCUMENTED upstream. Registering Forge's whole
`skills/` directory as a global discovery root is therefore NOT safe as a
default; section "Native discovery registration" below scopes it to a
curated subset instead. Forge's SKILL.md frontmatter (`name` +
`description`) is verbatim-compatible with what Codex reads — Codex reads
only those two fields, and the filename case (`SKILL.md`, exact case)
must be preserved for either discovery path to find it.

### 8.1 Materialization — the guaranteed floor, every provider dispatch

WHEN a provider dispatch's spawn contract attaches skills (the same
"Attached-skills list" concept `skills/kernel/SKILL.md` already uses for
in-harness agents), THE SYSTEM SHALL materialize each attached skill's
`SKILL.md` — plus its `references/` subdirectory, if the skill has one —
into the dispatch worktree at `.forge-dispatch/skills/<name>/`, copied
verbatim from the plugin's own `skills/<name>/` tree, before the worker
prompt is sent. This applies identically whether the target provider has
any native discovery mechanism of its own or not — materialization is the
floor every provider dispatch gets, never conditional on native discovery
being present, current, or verified.

The dispatch prompt SHALL be prepended with one directive line naming the
materialized path and instructing the worker to read each attached skill
there before starting work, e.g.: "Attached skills are materialized at
`.forge-dispatch/skills/<name>/SKILL.md` — read each one before you begin."
This is the ONLY skill-loading mechanism the dispatch prompt may assume
worked; it never assumes the provider's own discovery surface picked the
attachment up on its own.

**INTEGRATE-time exclusion.** `.forge-dispatch/` is dispatch-worktree
scratch space, never task output. THE SYSTEM SHALL exclude
`.forge-dispatch/` from the diff INTEGRATE merges back to the kernel's
branch — the same way `parallel-dispatch.md`'s worktree mechanics already
scope a worker's merged diff to its own task's files — so materialized
skill copies never enter the merged diff, never get committed, and never
leak into the task's Files-changed list. A dispatch helper that merges
`.forge-dispatch/` content into the integrated diff is a defect against
this section.

### 8.2 Native discovery registration — optional, human-run, additive

WHEN Codex's native Agent Skills discovery is confirmed current (section
above; re-verify against the installed `codex --version` before relying on
this — the discovery paths and budget are this task's dated research
snapshot, not a permanent guarantee), THE SYSTEM SHALL document — but
never itself execute — a one-time registration a human can run to expose
a CURATED SUBSET of Forge's `skills/` directory to Codex's native
discovery, via per-skill directory junctions into `~/.agents/skills` (no
admin rights needed on Windows; `mklink /J` per skill, not one parent
junction over all of `skills/` — recursion depth under Codex's scan roots
is unverified, and per-skill junctions survive `codex` CLI updates because
`$CODEX_HOME` is untouched by them). Full registration steps and the
curated-subset rationale live in `docs/conventions/config-and-features.md`,
"Codex native skill discovery — optional registration (codex-skill-loading,
2026-07-21)" — cited here, not restated. Native discovery, where a human
has registered it, is a BONUS surface layered on top of materialization —
it never substitutes for the attachment step in 8.1, which stays
mandatory regardless of whether discovery is registered, current, or
working.

### 8.3 Attachment is a requirement, not merely a discovery hint

WHEN a contract names attached skills, THE SYSTEM SHALL treat that
attachment as a requirement the worker is told to follow (8.1's directive
line) — this holds regardless of whether native discovery is registered,
current, or even exists for the target provider. Native discovery is
never a substitute for the contract explicitly naming what applies to a
given task; a provider stumbling onto a relevant skill via its own
discovery surface does not excuse the contract from attaching (and
materializing) the skills the task actually needs.

### 8.4 Trust note — skill content travels with the dispatch

WHEN skills are materialized into a dispatch worktree or registered for a
provider's native discovery, THE SYSTEM SHALL treat that as skill content
traveling to that provider — the same trust boundary the per-provider TOFU
confirmation already covers (`docs/conventions/trust-and-security.md`,
"Per-provider trust confirmation — 2026-07-19", `.forge/.trust-providers/
<provider>.local`). Global native-discovery registration (8.2) widens that
exposure further than a single dispatch's materialization does — it
exposes the registered skills' content to EVERY Codex session on the
machine, not only Forge-dispatched ones — which is exactly why 8.2 scopes
registration to a curated subset and requires a human to run it, rather
than Forge registering skills globally on the provider's behalf.

**UNVERIFIED — flagged, not asserted.** The following are open questions
this task's research could not confirm and that a later task or human
canary run must close before automation relies on them: whether `codex
exec` (non-interactive dispatch mode) discovers native skills identically
to the interactive TUI; the exact overflow behavior once registered
skill-description metadata exceeds the ~8,000-character/2%-of-context
budget; and precedence behavior across the `~/.codex/skills`,
`~/.agents/skills`, and project-local `.agents/skills` roots when a name
collides. Forge itself SHALL NOT run `codex exec` to test any of this —
zero live provider dispatches until a human has logged in and confirmed
the per-provider trust marker; the canary test in
`docs/conventions/config-and-features.md`'s registration section is
human-run, by design.

### 8.5 Builder tool allowlist + dispatch-contract bridge — R2 enforcement (2026-07-22, bm-atomic-doc-fix-canonical-route)

Two enforcement points make R2's crossing-provenance structural, not
merely detected-after-the-fact:

- **Builder tool-allowlist exclusion (`bm-builder-tool-allowlist-exclusion`).**
  THE SYSTEM SHALL exclude `AskUserQuestion` from every BUILDER-role
  dispatch contract — the in-harness Claude `forge-worker` and every
  external-provider worker alike. A builder therefore cannot structurally
  issue the live main-session `AskUserQuestion` call that a crossing
  envelope is bound to (`carve-out-provenance.md` §2). For external CLI
  providers (`codex exec`, etc.) this is automatic — the subprocess has no
  access to Forge's tools at all; for an in-harness Claude builder it is
  the allowlist that removes the tool. This is what makes
  `route_table.REJECTION_CATEGORIES`' `worker-originated` category a
  structurally-prevented case, not only a rejected one.
- **Dispatch-contract bridge (`bm-dispatch-contract-bridge`).** WHEN the
  router resolves a builder for a task, THE SYSTEM SHALL record the
  resolved builder (Claude `forge-worker` or the provider slug) in the
  task's Routing record, and SHALL bind any crossing envelope to that
  task's current content-hash (`carve-out-provenance.md` §2, field 5). Any
  bounce, edit, or re-dispatch of the task invalidates the envelope: the
  content-hash no longer matches (`stale`, category 5) and the single-use
  nonce is burned (category 4), so a crossing authorization never survives
  into a second dispatch of a mutated task.

<!-- Historical heading pin: ### 9. Tier re-pin + owner-allowed model set — 2026-07-22 -->
## 9. Tier re-pin + owner-allowed model set — 2026-07-22

The pin-staleness trigger (`docs/conventions.md`, "Provider dispatch
labels — 2026-07-22", resolution-order step 2) FIRED: a newer
`codex-default-model` (`gpt-5.6-sol`) was recorded than the 2026-07-20
catalog snapshot section 3's pins were taken from, and dispatch
evidence confirmed the staleness concretely (`gpt-5.6-sol` required a
CLI upgrade the old snapshot predated). Re-verified against the LIVE
`models_cache.json` catalog, fetched 2026-07-22; owner ratified the
allowed set the same day ("we should also allow for us to use terra
and luna and 5.5").

Superseding tier map (section 3's 2026-07-20 lines remain in place as
the historical record; THIS section governs):

```
- codex-tier-judgment: gpt-5.6-sol (model_reasoning_effort=high)
- codex-tier-balanced: gpt-5.6-terra (model_reasoning_effort=medium)
- codex-tier-mechanical: gpt-5.6-luna (model_reasoning_effort=medium)
```

- `gpt-5.6-sol` — catalog: "Latest frontier agentic coding model",
  priority 1 (best) — judgment/adversarial-judge work.
- `gpt-5.6-terra` — catalog: "Balanced agentic coding model for
  everyday work", priority 2 — standard worker builds.
- `gpt-5.6-luna` — catalog: "Fast and affordable agentic coding
  model", priority 3 — mechanical sweeps, bulk work.
- `gpt-5.5` — prior frontier ("Frontier model for complex coding,
  research, and real-world work", priority 7) — allowed alternative
  when a dispatch wants the previous generation; no role routes to it
  by default.

Every slug above is in the owner-allowed set schemaed by
`settings-schema.md`'s `codex-default-model` row; a dispatch naming any
other slug is a routing-record anomaly to flag, not silently accept.
The next re-pin fires on the same staleness trigger, never on a
calendar.

## 10. Plan consensus escalation — 2026-07-22 (spec cross-model-consensus)

Implements `docs/specs/2026-07-22-cross-model-consensus.md` AC A and AC B
— NORMATIVE. This is an ESCALATE-ONLY addition on top of the existing
single Architect-plan-refuter pass (`docs/conventions/verification.md`,
"Architect-plan refuter — 2026-07"): that section's ONE refuter pass stays
the default entry point for every `tier: full` plan (and any `tier:
standard` plan carrying the per-task `consensus-loop: on` routing-note
opt-in), gated by the SAME checklist trigger that section already cites
(`skills/spec/SKILL.md`'s Express-lane tier-escalation checklist) — never
nominal `tier: full` status alone. A clean plan — the single pass returns
zero REJECT decision ids — costs EXACTLY ONE advisor dispatch, ever; this
section fires ONLY when that pass returns at least one REJECT.

### 10.1 The fixed two-critique cap

WHEN the Architect-plan-refuter pass (`C1`) returns at least one REJECT
decision id, THE SYSTEM SHALL escalate: Claude revises (`R1`) and
re-proposes (`P1`), and the advisor issues exactly ONE further critique,
`C2` — `C1 -> R1(=P1) -> C2`, a FIXED cap of exactly TWO advisor critiques
total, never three. `C1` IS the existing single refuter pass, not a
separate step. Success is a critique (`C1` or `C2`) that returns zero
outstanding `P0`/`P1`-severity REJECT decision ids with full coverage of
the plan's decision manifest (10.2, below); THE SYSTEM SHALL stop early at
`C1` when it is already clean. WHEN `C2` still returns at least one
outstanding `P0`/`P1`-severity REJECT decision id, Claude MAY record a
further response, but THE SYSTEM SHALL mark that response explicitly
UNREVIEWED (no third critique exists to accept or reject it) and route the
plan STRAIGHT to the per-id human resolution pass (10.5, below) with NO
consensus claim made for any decision id still carrying that unreviewed
response.

**Economy rule — cosmetic REJECTs never gate another round.** WHEN a
critique's REJECT decision ids are ALL severity `P3` (cosmetic, per the
existing severity taxonomy `docs/conventions/verification.md`, "Finding
severity + confidence — 2026-07-18 (fg-a10911)"), THE SYSTEM SHALL have
Claude fix them INLINE in the same revision and record each as
`fixed-inline` in the ledger (10.4, below) — a `P3` REJECT NEVER by itself
triggers `C2`, and a mix of `P0`/`P1` REJECTs alongside `P3` REJECTs in the
same critique triggers `C2` for the `P0`/`P1` ids only, with the `P3` ids
already closed as `fixed-inline` before `C2` is dispatched. This mirrors
the existing delta-re-verify-only-P0/P1 policy
(`docs/conventions/verification.md`, "Marginal-gain stop rules — 2026-07-22
(human-ratified)") that already limits re-verification scope to P0/P1
severity, never P3 cosmetic findings.

### 10.2 Decision-id schema and state machine

WHEN the codex advisor reviews a proposed plan, THE SYSTEM SHALL require
its verdict to conform to a normative consensus-verdict JSON schema, not a
free-text "looks mostly fine" vibe verdict:

- `proposal_id`: identifies which proposal (`P0`, `P1`) this critique
  responds to.
- `decision_ids`: an exhaustive, ordered manifest of the plan's discrete
  decisions, kernel-authored at `P0` time and STABLE across `C1`/`R1`/`C2`
  unless explicitly withdrawn or superseded (state machine, below).
- For every id in `decision_ids`, the verdict SHALL carry exactly one
  `ACCEPT` or `REJECT`, a required `severity` (`P0`/`P1`/`P3`, required
  only for `REJECT`), a required `reason`, and — for every `REJECT` — a
  required `alternative`.
- An exact-coverage check applies: a verdict missing an id, or carrying an
  id not in the current manifest, is MALFORMED output, not a valid
  critique.
- This is the SAME structured-verdict discipline section 2's JSON/JSONL-
  only capture rule already requires for judge output; the schema above is
  this task's own addition to that captured payload, not a new capture
  mechanism.

**Decision-id state machine.** A decision id, once introduced at `P0`, is
in exactly one of: `open` (no verdict yet), `accepted` (the current
critique returned ACCEPT for it), `rejected` (the current critique
returned REJECT for it and Claude has not yet revised in response),
`fixed-inline` (a `P3` REJECT closed per the economy rule, 10.1 above), or
`resolved` (accepted in the most recent critique AND untouched by any
subsequent revision). A decision id MAY be marked `withdrawn` by Claude in
a revision (the underlying plan decision no longer exists) — a withdrawn
id is excluded from the NEXT critique's required coverage but its prior
history stays in the ledger. A decision id MAY be `reopened` if a later
revision reintroduces materially the same decision — reopening SHALL reuse
the original id (never mint a new id for the same decision) and resets its
state to `open`. Stale ids (present in an earlier manifest but silently
absent from a later proposal without an explicit `withdrawn` marking) are a
MALFORMED proposal, same as a missing verdict.

WHEN a critique produces at least one `P0`/`P1` REJECT decision id, THE
SYSTEM SHALL have Claude respond to EACH such id individually in its
revision (either incorporating the advisor's alternative, or stating a
reasoned counter-position), keyed to that decision id — a revision that
silently drops a REJECT id without an explicit, id-keyed response is a
defect against this section, not a valid round. (`P3` REJECTs are handled
via the economy rule, 10.1 above, not this per-id response requirement.)

### 10.3 Malformed output — retry-then-force extended to this judge role

Malformed output (missing coverage, missing reason/alternative/severity, or
a non-conforming payload) triggers the retry-then-force protocol defined in
section 7.4 (NOT section 2, which defines capture mechanics only) — this
section explicitly EXTENDS section 7.4's Phase-2-worker retry-then-force
protocol to this judge role: up to 2 re-prompts before the critique counts
as failed and the escalation degrades per 10.6's graceful-degrade shape.
Each retry is itself another provider CLI invocation and counts against the
dispatch tally exactly as section 7.6 already defines — "one critique" is
NOT "one dispatch" when a retry occurs, each retry is a distinct counted
invocation, closing the counting loophole where malformed-output re-prompts
would otherwise dispatch for free.

### 10.4 Exchange artifact contract — ledger plus append-only raw record

WHEN the exchange record is written, THE SYSTEM SHALL maintain TWO
artifacts, never one:

1. A compact, kernel-authored LEDGER appended to the spec/plan file itself
   under a `## Plan consensus record` section (always present for a spec
   the escalation has run against, even if empty before it runs) — one row
   per critique: critique id (`C1`/`C2`), the decision ids touched with
   their outcome (ACCEPT/REJECT/fixed-inline/withdrawn/reopened), a
   one-line kernel-written summary per id (never raw provider text), and a
   link to the matching span in the exchange artifact (below). The ledger
   closes with one summary line stating the outcome (`consensus reached —
   C1` / `consensus reached — C2` / `cap reached at C2 — see human
   resolution below`).
2. A dedicated, kernel-owned, APPEND-ONLY exchange artifact at
   `docs/specs/consensus/<spec-basename>-exchange.md`, holding the full raw
   proposal/critique/revision text for every critique. Provider output (the
   codex advisor's critique text) SHALL be neutralized before insertion:
   wrapped in a fenced code block (escaping any embedded triple-backtick
   sequences), never rendered as live markdown headings or bullets, so
   provider text can NEVER inject a heading, a clarification-marker
   marker, or any other structurally-significant token into a normative
   file. Claude's own proposal/revision text may be rendered as normal
   markdown since it is kernel-authored. The artifact carries a stated
   max-size note (a single spec's exchange artifact SHALL be flagged for
   human review, not silently truncated, if it exceeds a reasonably-sized
   document — exact threshold left to implementation) and is append-only: a
   resumed or re-run escalation appends a new dated section, it never edits
   or removes a prior critique's record.

**Crash/resume.** Because the ledger is written incrementally per critique
and the exchange artifact is append-only, a partially-recorded critique
(process interrupted mid-`C1`/mid-`R1`/mid-`C2`) is resumable: on resume,
the kernel reads the ledger's last CLOSED critique to determine the next
expected step, re-issues only that step, and appends the result — it never
replays or duplicates a critique already closed in the ledger.

### 10.5 Cap-out — per-id human resolution, never a silent adoption

WHEN `C2` is reached WITHOUT full consensus (at least one `P0`/`P1` REJECT
decision id still outstanding, including any left explicitly UNREVIEWED
per 10.1's cap-out rule), THE SYSTEM SHALL NOT silently adopt either side's
position. THE SYSTEM SHALL treat this as a PRE-approval clarification pass
(never folded into the same ask as spec approval):

- For EACH outstanding decision id, THE SYSTEM SHALL issue its own
  structured `AskUserQuestion` (one decision per question, per
  `docs/conventions/config-and-features.md`, "Asking the user questions"),
  presenting Claude's final stance and the advisor's final REJECT
  reason/alternative verbatim, with two pre-rendered exact-text options
  (Claude's position, the advisor's position) plus the standard "something
  else" escape hatch.
- Picking one of the two pre-rendered exact-text options MAY close that
  decision id directly with no further review.
- Picking "something else" (a third option) or requesting a redraft SHALL
  rerun the review affected by that decision id BEFORE the plan is
  considered settled for that id.
- Only once EVERY outstanding decision id from the cap-out is resolved
  does the spec proceed to the human spec-approval gate
  (`skills/spec/SKILL.md`, section 5) — the same "cannot proceed while any
  marker remains" floor `docs/specs/2026-07-16-forge-design.md` section 9.2
  already states for clarification-marker markers, now extended explicitly
  to cap-out decision ids. Cap-out resolution is its OWN pre-approval step,
  never conflated with the approval ask itself.

### 10.6 Provider-advisor slot, budget accounting, and graceful-degrade

WHEN the plan consensus escalation's provider-advisor slot resolves per the
active profile's `role-plan-refuter` key (`operator-profiles.md`), THE
SYSTEM SHALL run the pass/escalation with a codex advisor ONLY when that
role resolves to `codex` AND section 1a's four gate layers all pass; WHEN
`role-plan-refuter` resolves to `claude-only`, or any gate layer blocks,
THE SYSTEM SHALL degrade to a single Claude-only second-opinion pass (a
second `forge-architect` spawn), the same graceful-degrade shape section 4
already defines, with one stated note — never a silent skip, never a block
waiting for the provider. The escalation's codex advisor role applies the
equal-or-higher floor exactly as section 3's "Equal-or-higher floor" and
section 9's re-pinned tier map already require — `role-plan-refuter`
resolves to `codex-tier-judgment` (`gpt-5.6-sol` per section 9), never a
mechanical/mini tier, on every critique, including retries.

WHEN a consensus-escalation critique or revision dispatches the codex
advisor, THE SYSTEM SHALL count EVERY provider CLI invocation — including
every malformed-output retry issued under 10.3's retry-then-force protocol
— against the SAME provider-dispatch accounting section 7.6 already
defines (checkpoint model: tallied, checkpointed every
`provider-dispatch-checkpoint-every` dispatches, or hard-capped when
`max-provider-dispatches-per-session` is numeric). No new budget dimension,
no exemption from the existing cap/checkpoint machinery.

**Mid-cap outstanding-REJECT termination.** WHEN a numeric hard cap
(`max-provider-dispatches-per-session`) is reached, or a provider CLI
invocation fails outright, WHILE a P0/P1 REJECT decision id from the most
recent critique is still outstanding and has NOT yet been re-reviewed by a
subsequent critique, THE SYSTEM SHALL terminate the escalation as
UNRESOLVED (not as a completed cap-out, not as a Claude-only degrade) and
route it directly to the same per-id human resolution pass 10.5 defines
for cap-out. Falling back to a Claude-only second-opinion pass (this
section's graceful-degrade shape, above) is permitted only for gate-layer
blocks BEFORE a codex REJECT exists in the current round — it is NEVER a
substitute for reviewing an outstanding codex REJECT that the budget or a
provider failure prevented from being re-critiqued. A codex REJECT is never
silently erased by a Claude-only fallback.

### 10.7 Economy — no cost added to a clean plan

Nothing in this section changes `docs/conventions/verification.md`'s
"Architect-plan refuter — 2026-07" section's own trigger, cost, or
behavior for a plan `C1` accepts outright: the single pass still runs
exactly as that section states, and a plan with zero REJECT decision ids
never dispatches a second advisor call. This section is additive scope
gated strictly behind a REJECT, never a default widening of the existing
pass.

## 11. Sequential cross-model review + dualverify exception — 2026-07-22 (spec cross-model-consensus)

Implements `docs/specs/2026-07-22-cross-model-consensus.md` AC D —
NORMATIVE. Formalizes the bidirectional verify floor in substance: the
codex-builds/Claude-verifies half is UNCHANGED (section 7.5, cited not
restated — a Phase 2 external worker's diff is verified by a Claude-side
`forge-verifier`/`forge-ui-verifier` at the task's normal equal-or-higher
tier); this section adds the Claude-builds/sensitive-or-full half.

**Scope correction (bm-anti-collusion-verify-guard, 2026-07-22).** This
whole section — the automatic codex-adversarial-slot rule in 11.1, its
findings-review mechanic, and the dualverify exception in 11.2 — governs
ONLY the Claude-builds half named above. WHEN the task's BUILD was
dispatched to an external provider instead, this section does not apply
at all: section 7.5 governs in full and alone (Claude verifies, no codex
co-verifier substitution), per the unconditional anti-collusion invariant
in section 11.4 below.

### 11.1 Automatic sequential cross-model review

WHEN a task's BUILD is a Claude in-harness worker AND the task is `tier:
full` or touches a forge-security trigger domain (per
`docs/conventions/verification.md`'s panel-policy trigger list — the same
list the sensitive-domain carve-out cites,
`docs/conventions/dispatch-and-routing.md`, "Sensitive-domain build
carve-out — 2026-07-22"), THE SYSTEM SHALL, by ratified human decision
(2026-07-22), route the adversarial-verifier slot to codex AUTOMATICALLY
(gates permitting) — still the EXISTING one-adversarial-verifier
panel-slot ceiling (section 1, above), still grouped-verification
compatible, never a second slot — and THEN have Claude review ONLY what
codex flags: a findings-review pass over the codex verdict (validating,
refuting, or prescribing fixes per finding), never an independent full
re-sweep of the diff. The cheap fast model sweeps everything; the deep
model reads findings, not diffs.

**Findings-review doubles as the delta re-verify.** Budget interplay with
`docs/conventions/verification.md`'s "Marginal-gain stop rules — 2026-07-22
(human-ratified)": the codex sweep is the artifact's FIRST judgment pass
and Claude's findings-review is its SECOND AND FINAL — the findings-review
doubles as the delta re-verify (it validates fixes in the same pass), so
the lifetime cap of two is never exceeded; anything still disputed after it
escalates to the human.

Provider-gate degrade unchanged: any gate layer blocking codex routes the
slot back to a Claude verifier with one stated note (section 4, above), and
the sensitive-domain carve-out's BUILDER default is untouched (verifying is
a judge role — the carve-out binds the builder role only, section 1a
above).

### 11.2 Dual-verifier ceiling amendment — command-only

A genuinely SIMULTANEOUS dual-verifier pair (Claude and codex each
independently sweeping the same task, distinct slots) is NOT a default
anywhere — by ratified human decision (2026-07-22) it exists ONLY behind an
explicit command (`/forge:dualverify`), for audit-shaped work where blind
double-sweep is the point. The default posture everywhere else is the
sequential pattern above: one model audits, the other reviews the audit —
"semi-minimal, biggest bang per buck" (owner's words). The
one-adversarial-verifier ceiling (section 1, above) is amended ONLY inside
that command's scope, nowhere else. `/forge:dualverify`'s own command doc
(`commands/dualverify.md`) is out of this section's scope — this section
states only the exception this command is permitted to carve, not the
command's own mechanics.

### 11.3 Disagreement reconciliation — through the existing filter, never free-form synthesis

WHEN a Claude verifier and a codex co-verifier produce conflicting findings
across different tasks in a grouped-verification pass (or, under the
dual-verifier amendment, on the same task), THE SYSTEM SHALL reconcile
finding-by-finding through the EXISTING verifier-finding filter/
reproduction protocol (`docs/conventions/verification.md`,
"Verifier-finding filter (bounce pre-check) — 2026-07") — NOT via
free-form "kernel synthesis." Specifically: union all non-conflicting
surviving findings from both verifiers; for a challenged or contradicting
finding, run exactly ONE clarification pass through the existing
filter/reproduction protocol; and BLOCK (escalate to the human via the
task's normal blocked-state) on any contradiction that remains unresolved
AND outcome-affecting after that pass. The kernel does not become an
unacknowledged third judge inventing its own resolution — every
reconciliation step is traceable to the existing filter/reproduction
protocol, recorded in the task's Attempt log (which findings were kept,
dropped, or merged, and why).

WHEN a Claude/codex verifier disagreement cannot be confidently resolved
through the finding-by-finding reconciliation above (a factual
contradiction neither verifier's evidence settles after the one
clarification pass), THE SYSTEM SHALL escalate to the human via the task's
normal blocked-state, plain-English blocker report — the same "fail ->
bounce -> blocked" path `docs/specs/2026-07-16-forge-design.md` section 4.1
step 7 already defines, never a forced kernel guess presented as settled.

### 11.4 Anti-collusion invariant — builder/verifier separation (never a self-graded build)

Implements `docs/specs/2026-07-22-phase2-external-workers.md`, "Anti-
collusion invariant — builder/verifier separation (corrects section 11's
scope)" — NORMATIVE, highest-priority correctness finding from codex's
round-1 critique on that spec.

WHEN a task's BUILD is dispatched to an external provider (via the R1
automatic-default or a `provider:` override), THE SYSTEM SHALL require the
mandatory adversarial verifier for that task to be Claude
(`forge-verifier`/`forge-ui-verifier`) — exactly as section 7.5 already
states. A provider co-verifier SHALL NEVER occupy the sole adversarial
panel slot for a task that same provider, or ANY provider, built. This is
an INVARIANT, not a default subject to profile customization, and it holds
UNCONDITIONALLY — regardless of how the active profile's `role-co-verifier`
is set, including when `role-co-verifier` resolves to the SAME provider
that built the task, or to a DIFFERENT external provider than the builder:
neither case ever substitutes for the Claude verifier on that task. Section
4's graceful-degrade (any gate layer blocking a provider routes the
affected slot back to a Claude worker/judge) never degrades this rule the
other direction — a gate blocking Claude is not itself possible here, since
Claude is always available as the fallback judge.

**Section 11's scope, restated as the correction this invariant makes.**
Section 11.1's automatic codex-adversarial-slot rule applies EXCLUSIVELY
WHEN the BUILDER is a Claude in-harness worker AND the task is `tier: full`
or sensitive-domain (11.1's own WHEN clause already says so) — that
condition is EXCLUSIVE, not merely a default: WHEN the BUILDER is an
external provider instead, section 11 in its entirety (11.1's two-stage
codex-sweep/Claude-findings-review mechanic and 11.2's dualverify
exception alike) is simply inapplicable, and section 7.5 governs alone —
Claude verifies, period, with no codex co-verifier substitution, no
findings-review split, and no dualverify carve-out standing in for it.
This correction changes no other section-11 mechanic: for Claude-built
`tier: full`/sensitive-domain work, 11.1-11.3 above are unchanged and
unaffected by this section.
