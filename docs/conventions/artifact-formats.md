# Artifact formats

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## .forge/ layout (Phase 1 subset)

```
.forge/
├── forge.md          # project config
└── queue/tasks/      # one .md per task, flat, state in frontmatter
```

Created on demand (auto-init) by any Forge command if missing.

`.forge/` always lives at the git repo root (`git rev-parse --show-toplevel`), never in a subdirectory — resolve the root before any operation touches it (fg-e101).

## Task files

> Amended by: "Parallel dispatch (Waves amendment, 2026-07-17)", "Claims and crash recovery — amendment (2026-07-17)"

Filename: `<id>-<slug>.md` where slug is the kebab-cased title, max 40 chars.

### Frontmatter (flat YAML, all fields required, exact names)

| Field | Type / values | Notes |
|---|---|---|
| id | `fg-[0-9a-f]{4,8}` | random; check collisions against existing filenames |
| title | string | imperative, one line |
| state | backlog \| ready \| active \| blocked \| done \| dropped | never encoded in folder location |
| tier | trivial \| standard \| full | ceremony level (spec §4.4) |
| priority | 1 \| 2 \| 3 \| 4 | 1 = highest |
| spec | path or null | required non-null when tier is full |
| blocks | [ids] | tasks this one blocks |
| blocked-by | [ids] | must all be `done` before this is dispatchable |
| claimed-by | `<session-id> @ <ISO-8601>` or null | non-null iff state is active |
| parallel-safe | true \| false | same-wave concurrency eligibility (dispatch parallelism arrives Phase 2) |
| created | ISO-8601 date | |
| updated | ISO-8601 date | touch on every edit |

### Body sections (all required, exact headings, in this order)

```
## Acceptance criteria
## Execution plan
## Routing record
## Attempt log
## Outcome
```

- **Acceptance criteria**: one or more EARS clauses — `WHEN [trigger], THE SYSTEM SHALL [behavior]`. Required non-empty for any state except backlog. Each clause must be checkable by a verifier or map to a test.
- **Execution plan**: written at the kernel's PLAN step. `(pending)` until then.
- **Routing record**: one line per attempt: `attempt N: <agent or inline> — <model>/<effort> — <one-line reasoning>`.
- **Attempt log**: what happened per attempt, incl. verifier verdicts and bounce notes.
- **Outcome**: filled at INTEGRATE (or when blocked/dropped). The audit trail's conclusion.

### State machine

```
backlog → ready          criteria complete, ready to schedule
ready   → active         claimed by a session (write claimed-by)
ready   → blocked        blocked-by dependency became unsatisfiable (points at a dropped/missing task, or a dependency cycle); blocker report in Outcome
active  → done           verifier passed; Outcome written
active  → ready          unclaimed (crash recovery, or voluntary release)
active  → blocked        2 failed bounces, or external blocker; blocker report in Outcome
blocked → ready          blocker resolved (human or kernel)
any     → dropped        human decision only
```

No other transitions are legal. `done` and `dropped` are terminal.

`ready → blocked` fires only when a task's declared dependency is genuinely
unsatisfiable (see Waves, below) — it is a different case from, and must not
be conflated with, a task a session voluntarily released this session: a
voluntarily-released task stays `ready` and is simply skipped if the wave
offers it back (kernel PLAN step), never transitioned to `blocked`.

### Claims and crash recovery

- Session ID: `sess-` + 4 lowercase hex, generated once per kernel session.
- Claim = single edit setting `claimed-by: sess-xxxx @ <timestamp>` and `state: active`.
- At SYNC, any `active` task whose claim timestamp is older than the staleness threshold (forge.md, default 2h) is reset: `state: ready`, `claimed-by: null`, note appended to Attempt log.
- **Claim race guard**: immediately before writing a claim, re-read the task file's current `claimed-by`/`state` from disk. If another session has already set `claimed-by` (state is `active` under a different session id) since it was last read, abort this claim — do not overwrite — and move on to the next task in the wave. This closes the read-then-write race window between reading a task as `ready` and writing the claim.

### Waves

A wave = every `ready` task whose `blocked-by` ids are all `done`. Order within a wave: priority ascending, then created ascending. Phase 1 dispatches sequentially in that order.

**Unsatisfiable dependencies.** While computing the wave, check each `ready` task's `blocked-by` ids against the queue. If any id is missing, or names a task whose `state` is `dropped`, that dependency can never become `done`. Transition the dependent task `ready → blocked` (state machine, above) with a blocker report in Outcome naming the unsatisfiable id, so it surfaces in `/forge:status` instead of sitting invisibly in `ready` forever.

**Dependency cycles.** If a set of `ready` tasks' `blocked-by` chains form a cycle (e.g. A blocked-by B, B blocked-by A, or a longer loop), none of them can ever become dispatchable — the cycle itself is the unsatisfiable dependency. Detect this while computing the wave: transition every task in the cycle `ready → blocked` with a blocker report in Outcome listing the full cycle (ids in order), and have PULL report it as a deadlock — naming the cycle — rather than a clean empty-wave stop.

## Repo map files (`.forge/map/`) — Phase 2

The map answers **what is this system, where do things live, why is it shaped this way**. It is **narrative, not call graphs**: "who calls this / where is this symbol used" is delegated to symbol-precise tooling (LSP / Serena-class MCP), never written as prose — prose call graphs go stale instantly and waste tokens (spec §7.2). All map files are plain markdown.

### Layout

```
.forge/map/
├── architecture.md   # subsystems, data flow, entry points (~1–2k tokens; read every SYNC)
├── index.md          # annotated tree, one line of purpose per significant file/dir
├── conventions.md    # build/test/run commands, patterns, naming, gotchas (worker-brief staple)
├── hotspots.md       # fragile / high-churn areas + bug clusters (bumps router risk)
└── subsystems/       # optional deep-dives, loaded only when a task touches them
```

Created on demand by the `map` skill (`/forge:map` or the kernel).

### Freshness header (required, every map file)

The first line after each file's H1 title:

```
<!-- forge-map-commit: <full-40-char-sha> built: <ISO-8601-UTC> -->
```

- `<full-40-char-sha>` = `git rev-parse HEAD` at build time.
- `<ISO-8601-UTC>` = a real `date -u +%Y-%m-%dT%H:%M:%SZ` timestamp.
- SYNC and the session-start hook grep this line and compute drift with `git rev-list --count <sha>..HEAD` (= commits behind HEAD).
- A map file with no such line is treated as stale.

### architecture.md

Sections: `## Subsystems` (each: name, responsibility, key files), `## Data flow` (how a request/task moves through the system), `## Entry points` (commands, mains, public surfaces). Target ~1–2k tokens — it is read every SYNC.

### index.md

Salience-ordered annotated tree. Significance is **seeded from objective signals — git churn frequency and reference counts (spec §7.3) — then curated by agent judgment; judgment curates, it does not invent the ranking.** One line per significant entry: `path — purpose (churn: N)`.

### conventions.md (map-local — distinct from this plugin file)

Build/test/run commands, code patterns, naming conventions, and gotchas for the target repo. Goes into every worker brief.

### hotspots.md

Fragile / high-churn / bug-cluster areas. Each entry names the area, the risk, and the objective signal (churn count and/or recent bug/task ids). The router bumps a task's risk score when it touches a hotspots.md area.

## Spec files (Phase 3)

Approved specs are the one human gate (spec §9.2). Location: `.forge/specs/`.
Filename: `<YYYY-MM-DD>-<slug>.md` (slug kebab-case, max 40 chars).

### Frontmatter (flat YAML, all fields required, exact names)

| Field | Type / values | Notes |
|---|---|---|
| id | `spec-[0-9a-f]{4,8}` | random; collision-checked against existing spec files |
| title | string | one line |
| status | draft \| approved \| superseded | only a human sets `approved` |
| created | ISO-8601 date | |
| approved-date | ISO-8601 date or null | non-null iff status is `approved` (or `superseded`); null while `draft` |

### Body sections (all required, exact headings, in this order)

```
## Goal
## Non-goals
## Acceptance criteria
## Risks
## Task decomposition
## Changelog
```

- **Goal**: the outcome, 1–3 sentences.
- **Non-goals**: explicit out-of-scope items.
- **Acceptance criteria**: one or more EARS clauses (`WHEN [trigger], THE SYSTEM SHALL [behavior]`), each checkable or test-mappable.
- **Risks**: `<concrete risk> -> <mitigation>` lines.
- **Task decomposition**: a checklist of future `tier: full` tasks, each with one-line scope and dependencies; decomposition creates one queue task per item.
- **Changelog**: spec deltas (§9.4). Deltas are appended as `### Proposed delta — <date> — from <task-id> — UNRATIFIED`, then marked `RATIFIED <date>` or `REJECTED <date> — <reason>` at the next spec interaction. Spec truth is never edited silently.

### Clarification markers

`[NEEDS CLARIFICATION] <question>` may appear anywhere in a `draft` spec body. A spec with any such marker **cannot be approved and cannot be decomposed into queue tasks**. An `approved` spec contains zero markers (validator-enforced).

### Approval

Only a human sets `status: approved` + `approved-date`, recording a one-line approval note in the Changelog. Decomposed tasks carry `tier: full` and `spec: specs/<file>.md`; a `tier: full` task must link an `approved` spec.

## constitution.md (Phase 3)

Location: `.forge/constitution.md`. A short, numbered list of per-project non-negotiables, each written to be **mechanically checkable** — the verifier returns a yes/no with concrete evidence per rule (spec §9.1). Format:

```
# Constitution — <project>

1. <rule>
2. <rule>
...
```

Rules are numbered and stable (audit references depend on the numbers): add by appending, retire by marking `(retired <date>)`, never renumber or delete. Seed defaults (see the spec skill's `references/constitution-template.md`):

1. Every bug fix ships with a test that fails without the fix.
2. No speculative abstraction (no indirection for a caller that doesn't exist).
3. Tests exist before implementation for standard-and-full-tier tasks.
4. No new dependency without a stated reason.
5. No secret, key, or token is committed to the repo.

When `.forge/constitution.md` exists, the kernel passes its rules to the verifier at VERIFY; any rule returning `no` fails the task.

## project.md (project charter)

Location: `.forge/project.md`. The project-level charter produced by the
`discover` skill (`/forge:discover`) — vision, users, stack, and roadmap,
established once up front so specs have something to align against. It sits
above specs in the hierarchy: specs are feature-level; `project.md` is
project-level and specs reference it, not the other way around.

### Frontmatter (flat YAML, all fields required, exact names)

| Field | Type / values | Notes |
|---|---|---|
| title | string | one line |
| status | draft \| approved \| superseded | only a human sets `approved` |
| created | ISO-8601 date | |
| approved-date | ISO-8601 date or null | non-null iff status is `approved` (or `superseded`); null while `draft` |

### Body sections (all required, exact headings, in this order)

```
## Vision
## Users & use cases
## Success criteria
## Non-goals
## Tech stack & rationale
## Architecture
## Constraints
## Risks
## Roadmap
```

(`## Architecture` was added after `## Tech stack & rationale`; see the
Architecture section addendum below.)

- **Vision**: the problem being solved and what's being built, a few
  sentences.
- **Users & use cases**: user types and their 1-3 key use cases each.
- **Success criteria**: what success looks like, concrete and checkable.
- **Non-goals**: explicitly out-of-scope items.
- **Tech stack & rationale**: each stack/architecture choice with why it was
  made, not just what was picked.
- **Constraints**: platform, timeline, budget, regulatory, or security
  constraints stated up front.
- **Risks**: `<concrete risk> -> <mitigation>` lines.
- **Roadmap**: a numbered list of phased milestones, each title + one-line
  outcome + rough dependency order. Each milestone is a future `/forge:spec`
  entry point — the roadmap is the backlog of specs-to-be, not prose.

### Approval

Only a human sets `status: approved` + `approved-date`, same one-human-gate
rule as specs (spec §9.2). A `draft` charter is provisional; only an
`approved` charter is the project's source of truth. `.forge/project.md` is
never clobbered once it exists — later discovery passes update it via
explicit, user-directed edits or a dated revision note, never a silent
overwrite.

### Relationship to specs

When drafting a spec, if `.forge/project.md` exists and is `approved`, the
spec skill reads it first and aligns the spec's Goal/Non-goals with the
charter. A spec that would contradict the charter is surfaced to the human
rather than silently diverging.

### Architecture section (addendum)

`## Architecture` is a required body section, inserted immediately after
`## Tech stack & rationale` — the full body-section order is now: Vision,
Users & use cases, Success criteria, Non-goals, Tech stack & rationale,
Architecture, Constraints, Risks, Roadmap.

- **Architecture**: top-level components/modules and their responsibilities,
  data flow, key patterns/conventions, integration points (external
  services/APIs), and the rationale for the major architectural choices —
  not just what was picked, why.

Established or confirmed by the `discover` skill's Stack & Architecture
pass, which is idempotent: if `.forge/map/architecture.md` already has real
content, or a root `ARCHITECTURE.md` / `docs/architecture.*` exists, or this
section is already populated, discovery reads it back and confirms it with
the human instead of redrafting. The charter's `## Architecture` holds
intent and rationale; `.forge/map/architecture.md` holds the code-level view
(subsystems, entry points) — the two are reconciled, not duplicated
verbatim.

## Offline merge convention

Response to fg-e103 (offline / multi-machine safety for the queue). Task and
spec ids may now be `fg-[0-9a-f]{4,8}` / `spec-[0-9a-f]{4,8}` — 4 to 8
lowercase hex chars, not just the original fixed width of 4. New ids are
generated as `fg-`/`spec-` + 6 lowercase hex chars (still collision-checked
against existing filenames), which lowers cross-machine collision risk while
staying short; existing 4-char ids remain valid and are never renamed or
migrated.

**Frontmatter conflict resolution.** When two machines' `.forge/` queues are
merged (e.g. via `git merge`/`git pull`) and a task or spec file's
frontmatter hits a merge conflict, resolve it **per field**, preferring
whichever side represents the more-advanced state, rather than picking one
side's whole file:

- Progress-tracking fields (`state`, `claimed-by`, `updated`, and the body's
  Attempt log / Outcome content) take the value from whichever side is
  further along: a later `updated` timestamp wins, and a state further along
  the state machine (e.g. `active` or `done`) wins over a less-advanced one
  (e.g. `ready`) from the other side.
- Declarative fields (`title`, `tier`, `priority`, `spec`, `blocks`,
  `blocked-by`, `parallel-safe`) take the more complete/specific value; if
  genuinely ambiguous, surface the conflict to a human rather than guessing.
- If the merge would leave two different files carrying the **same id**
  (e.g. both sides independently created a task or spec with a colliding id
  before ever syncing), regenerate a fresh id for one of them, rename its
  file, and update any `blocks`/`blocked-by` references that pointed at the
  old id.

## Readable task ids — 2026-07-20

> Amends: "Offline merge convention" (above).

Response to spec-f0c2 Amendments item 2 (2026-07-20 ratification): a new
task or spec id minted after this convention lands is a human-readable
kebab-case name describing the work (e.g. `database-migration`,
`color-refactor`) -- 3-40 chars, `[a-z0-9][a-z0-9-]*[a-z0-9]`, no leading or
trailing `-`, no `--` run -- checked unique against every id already in the
repo before minting. Legacy `fg-`/`spec-` hex ids are grandfathered
permanently and never renamed to this scheme.

This extends the "Offline merge convention" collision rule (above) with
rename-on-collision: when two machines independently mint the **same name**
for **different work** and their queues merge, resolve it the same way an
id collision was already resolved there -- regenerate rather than clobber
-- except the replacement is a suffixed variant of the same name
(`-2`, `-3`, ...) instead of a fresh hex id, and the filename plus any
`blocks`/`blocked-by` references that pointed at the renamed side are
updated to match. Name collisions are rare but possible by design; the
presence manifests (spec-f0c2 items 1-2) make concurrent minting visible
across machines, which is the primary mitigation, not this rename step.

## Multi-operator coordination — 2026-07-20

> Amends: "Offline merge convention" (above).

Response to spec-f0c2 (ratified 2026-07-20; folds in and supersedes
`fg-e103`, whose `state: done` and Outcome remain untouched historical
record — its task file now carries `superseded-by-spec: spec-f0c2`). Four
git-mediated, kernel-executed mechanisms, shipped across `fg-f0101` through
`fg-f0104`:

- **Presence manifests.** Each running kernel session writes/updates
  `.forge/coordination/<operator-handle>.md` at SYNC and at every milestone
  boundary (a task claim, a wave dispatch, or an INTEGRATE), and PULL reads
  every peer manifest before computing a wave, excluding peer-claimed task
  ids and peer in-flight wave-boundary paths from the claimable set —
  schema, write/read procedure, and the 4-hour staleness rule are
  `skills/kernel/references/coordination-gate.md` §§1-7 (not restated
  here).
- **Roster gating.** Peer-manifest honoring is narrowed to operator handles
  listed in a committed `.forge/coordination/roster.md`; behavior is
  open-by-default when no roster file exists, and a malformed or
  unreadable roster degrades to open-by-default rather than ever locking a
  peer out — `coordination-gate.md` §11.
- **Sync cadence.** SYNC pulls `staging` before PULL computes a wave or any
  task is claimed; INTEGRATE pushes the integration commit to `staging`
  (never `main`) before the next claim, retrying via the "Offline merge
  convention" above on a diverged push; an explicit human instruction to
  push elsewhere takes precedence over this multi-operator default for
  that push — `coordination-gate.md` §10.
- **Readable ids + rename-on-collision.** New task/spec ids mint as
  human-readable kebab-case names, with rename-on-collision extending the
  "Offline merge convention" id-collision rule above — see "Readable task
  ids — 2026-07-20" (above), not restated here.
- **Notification channel dropped.** spec-f0c2's outbound-only notification
  channel design point (decomposition item 5) was dropped entirely at
  ratification (Amendments item 3) — no channel content ships anywhere in
  this convention.

## schema-version

Response to fg-e106 (schema versioning + migration path for `.forge/`
artifacts). Task, spec, and memory-fact frontmatter accept an **optional**
`schema-version` field (a plain integer). It is never required: a file with
no `schema-version` is treated as `schema-version: 1` and validates exactly
as it did before this field existed. New files written by this version of
Forge stamp `schema-version: 1` explicitly.

Each validator defines `SUPPORTED_SCHEMA` (currently `1`). If a file
declares a `schema-version` greater than `SUPPORTED_SCHEMA`, the validator
does not fall through to a generic field error — it reports a specific,
actionable message: `<path>: produced by a newer Forge (schema-version N >
1) — upgrade the plugin`. Bump `SUPPORTED_SCHEMA` (and the templates'
stamped value) only on a breaking change to a file's format, never for
additive/backward-compatible changes — those stay invisible to older
validators by design.

## Parallel dispatch (Waves amendment, 2026-07-17)

Amends the Waves sections above: "Phase 1 dispatches sequentially" is no
longer the whole story. The default is now **parallel when eligible,
sequential otherwise** — sequential stays the fallback for every ineligible
task.

A batch of same-wave tasks is parallel-eligible iff ALL of:

- ≥2 tasks, each `parallel-safe: true`;
- no `blocked-by` edges among the batch members;
- every member declares a file scope (Execution plan files-to-touch /
  spawn-contract May-modify paths) with no overlap between members — a task
  with no declared scope is NOT parallel-eligible;
- batch size ≤ `max-parallel-tasks` (forge.md Queue section, default 3).

Mechanics (full text in `forge:kernel`, GATE / ROUTE + DISPATCH / VERIFY /
INTEGRATE):

- The kernel claims ALL batch tasks before dispatching any worker (one atomic
  file-write each, same re-read-before-write race guard as any claim).
- Each task is its own worker spawn with git worktree isolation. Workers in
  worktrees still never touch `.forge/` — all `.forge/` writes are
  kernel-only, on the main branch.
- Verifiers (one per task, equal-or-higher tier) may run in parallel; their
  verdicts are consumed at INTEGRATE.
- **INTEGRATE is strictly sequential and kernel-owned:** one worktree at a
  time, completion order — verify → merge → gates on the merged result →
  commit. Merge conflicts bounce the task to `blocked` (conflict noted in
  Attempt log, never resolved speculatively). The merged-gates run is
  authoritative over any per-worktree pass.
- One worker failing/blocking does not stop the rest of the batch. A dead
  session's orphaned worktrees are flagged by the SYNC stale-worktree sweep
  for human cleanup — never auto-deleted.

## Claims and crash recovery — amendment (2026-07-17)

Amends "Claims and crash recovery" above:

- Default `claim-staleness-hours` is lowered from 2 to **0.5** (30 minutes).
  The forge.md example above predates this amendment; new configs use 0.5.
- **Orphaned-edit guard.** At claim recovery, before resetting a stale
  `active` task to `ready`: run `git status --porcelain` filtered to the
  task's declared scope paths. If uncommitted changes exist there, do NOT
  silently reset — append `possible orphaned edits from a dead session in
  <paths> — needs human git diff review` to the Attempt log and set
  `state: blocked` instead.

## Optional task fields — 2026-07-22 (phase2-external-workers)

Task frontmatter accepts OPTIONAL fields beyond the required set in "Task files" above. Absence of an optional field never fails validation; each field states what its own absence means — not automatically "no change."

**`provider`** (bm-provider-schema-field, `docs/specs/2026-07-22-phase2-external-workers.md`)

- **Values**: a task's `provider:` field, if present, must be one of `tools/validate_config.py`'s existing `PROVIDER_ENUM` constant (`codex | grok | antigravity`) union the `"claude-only"` sentinel — i.e. `codex | grok | antigravity | claude-only`. Imported and reused by `tools/validate_task.py`, never a second restated copy of the enum. A value outside that set is a validation ERROR, the same severity as a bad `state:`/`tier:`/`priority:` value.
- **Fail-closed near-miss keys.** A frontmatter key matching `/^providers?$/i` case-insensitively but NOT the exact lowercase singular `provider` (e.g. the `providers:` plural typo, or an any-case variant like `Provider:`) is a validation ERROR, never a silently-ignored unknown key. A silently-dropped near-miss key could leave an intended override unapplied while the task still resolves to the external default, with no error surfaced anywhere.
- **Honest absence framing.** When a task omits `provider:` entirely, that means **"no task-level override is present"** — NOT "behaves exactly as before this field existed." Per the kernel's ROUTE step (R1, the same spec), when the active profile's `role-worker` resolves to a provider (not `claude-only`), that resolution becomes the task's DEFAULT builder route whenever no `provider:` override is present. For a repo that already sets `role-worker: codex`, an EXISTING task with no `provider:` field will, once that routing ships, resolve its builder to `codex` by default where it previously resolved to Claude — a real routing-behavior change on upgrade, not a backward-compatible no-op. This documents the schema/validation side only; the ROUTE-step default/override mechanics are a separate decomposition item.
