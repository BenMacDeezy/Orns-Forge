# Customization persistence

One table: for every surface Forge lets a human customize, where it
persists and whether it survives a plugin update. This page is the
human-facing companion to the rule itself — the full definition of the
three storage tiers (plugin cache / user space / project space), the
`${CLAUDE_PLUGIN_ROOT}` reasoning, and the enforcement gate live in
`docs/conventions/config-and-features.md`, "Customization persistence
contract — 2026-07-18 (fg-b0101)". Read that section first if the tier
names below are unfamiliar; this page does not restate it.

**Reading the table.** "Shipped" means the write path exists in this repo
today and was verified while writing this page (a `state: done` queue task,
or code exercised by the passing test suite). "Not yet shipped" means the
row names the location its own approved spec defines, but no task has yet
landed the code that writes there — the path is a documented future
location, not something you'll find on disk yet.

| Surface | Storage tier | Update-survival guarantee | Status | Source of truth |
|---|---|---|---|---|
| Operator profiles (autonomy domain) | Project space — `.forge/profiles/<name>.md` for a custom profile; `.forge/forge.md` `## Operator profile` section holds the one active-profile pointer | Byte-for-byte unchanged across `/forge:update` (project space) | **Shipped** — `fg-b0103`/`fg-b0104` (container format + kernel wiring) are `state: done`; `.forge/profiles/<name>.md` custom storage and the `## Operator profile` pointer are live per `skills/kernel/references/operator-profiles.md` | `.forge/specs/2026-07-18-operator-profile-system.md` (spec-4d2a), "Shared overlay-profile machinery" + "Autonomy domain" AC |
| Provider profiles (`## Providers` domain) | Project space — same container file, `.forge/profiles/<name>.md` `## Providers` section | Byte-for-byte unchanged across `/forge:update` (project space) | **Shipped** — `fg-c0101` (providers-container-extension) is `state: done`; the `## Providers` schema lives in `skills/kernel/references/operator-profiles.md` | `.forge/specs/2026-07-18-operator-profile-system.md` (spec-4d2a), "Relationship to fg-a10902"; `.forge/queue/tasks/fg-c0101-providers-container-extension.md` |
| Provider trust markers | Project space — `.forge/.trust-providers/<provider-id>.local`, one file per confirmed provider | Byte-for-byte unchanged across `/forge:update`; **machine-local and git-ignored** — never committed, so the confirmation itself does not travel with the repo to another machine or clone (same TOFU shape as `.forge/.trust-local`) | **Shipped** — `fg-c0103` (per-repo opt-in and trust gate) is `state: done` | `docs/conventions/trust-and-security.md`, "Per-provider trust confirmation — 2026-07-19 (fg-c0103, spec-e8a3)" |
| Trust boundary markers | Project space — `.forge/.provenance` (first-party init marker) and `.forge/.trust-local` (human-confirmed marker) | Byte-for-byte unchanged across `/forge:update`; **machine-local and git-ignored** — never committed, by design (a committed marker would let a poisoned fork confer trust on every clone) | Shipped | `docs/conventions/trust-and-security.md`, "Trust model: local trust-on-first-use (TOFU)" |
| Ported agents (`/forge:port`) | Project space — target location, once shipped: `.forge/agents/<name>.md` (canonical) mirrored to `.claude/agents/<name>.md` (harness discovery shim) — the same convention project-local agents already use | Byte-for-byte unchanged across `/forge:update` (project space); the `.claude/agents/` mirror is a load shim, not the source of truth | **Shipped** — `commands/port.md` (`fg-b0203`, `state: done`) drives the detector + mapping stages (`fg-b0201`/`fg-b0202`) behind one collision-checked structured approval | `.forge/specs/2026-07-18-agent-porting-and-lifecycle.md` (spec-6b7c), "Agent porting" AC |
| Project-local agents | Project space — `.forge/agents/<name>.md` (canonical, git-tracked), mirrored to `.claude/agents/<name>.md` so the harness discovers it | Byte-for-byte unchanged across `/forge:update`; the mirror is a load shim regenerated from the canonical file, not independently authoritative | Shipped — `commands/agent.md`, `skills/agent-factory/SKILL.md` | `docs/conventions/agents-lifecycle.md`, "`.forge/agents/` (project-local agents)" |
| Project memory | Project space — `.forge/memory/MEMORY.md` (index) plus `.forge/memory/<type>-<slug>.md` (one fact per file) | Byte-for-byte unchanged across `/forge:update`; facts are never deleted, only marked superseded | Shipped | `docs/conventions/memory.md`, "Project memory files (`.forge/memory/`) — Phase 2" |
| Craft memory (plugin-level) | **Plugin cache** — `<plugin-root>/memory/` (`memory/MEMORY.md` plus `memory/<type>-<slug>.md`), git-tracked with the plugin's own repo, sitting alongside `skills/`, `agents/`, `tools/` | **None** — this is the one memory store that lives inside the plugin's own installed tree, so `/forge:update` overwrites it wholesale exactly like any other plugin-cache path. It is not a human customization written per project; it is Forge's own project-agnostic lesson store, populated only by promotion during the kernel's LEARN step and shipped as part of each plugin release — any fact promoted since the last release ships in the next one, not preserved by the update mechanism itself | Shipped | `docs/conventions/memory.md`, "Memory — agents tag + craft memory (2026-07-17)" |
| Queue | Project space — `.forge/queue/tasks/<id>-<slug>.md`, state machine in frontmatter | Byte-for-byte unchanged across `/forge:update` | Shipped | `docs/architecture.md`, "Subsystems" ("Queue"); `docs/conventions.md` (queue format shard) |
| Specs | Project space — `.forge/specs/<date>-<slug>.md` | Byte-for-byte unchanged across `/forge:update` | Shipped | `docs/architecture.md`, "Subsystems" ("Spec pipeline") |
| `forge.md` config (Features / Budgets / Queue / Gates) | Project space — `.forge/forge.md` | Byte-for-byte unchanged across `/forge:update`; a missing toggle is read as its documented default, never as an implicit opt-out/opt-in | Shipped | `docs/conventions/config-and-features.md`, "forge.md (project config)" and "Features (forge.md)" |
| Constitution (per-project non-negotiables) | Project space — `.forge/constitution.md` | Byte-for-byte unchanged across `/forge:update`; rules are appended or marked `(retired <date>)`, never renumbered or deleted | Shipped — exists on disk in this repo today, ends with an explicit `<!-- Edit freely: add project rules below ... -->` marker, and directly gates VERIFY (the kernel passes its rules to the verifier; any rule returning `no` fails the task) | `docs/conventions/artifact-formats.md`, "constitution.md (Phase 3)" |
| Project charter | Project space — `.forge/project.md` | Byte-for-byte unchanged across `/forge:update`; "never clobbered once it exists" | Shipped-as-write-path via `/forge:discover` — **not instantiated in every repo** (this repo's own `.forge/project.md` does not exist as of this page) | `docs/conventions/artifact-formats.md`, "project.md (project charter)" |
| Project-local skills | Project space — documented convention, discovered per-session by `skills/equip/SKILL.md`'s INVENTORY step ("any project-local (`.forge/`) ... skills discoverable in this session") | Byte-for-byte unchanged across `/forge:update` (project space), same as any other `.forge/` content | **Documented convention only** — `equip` discovers project-local skills if present, but no Forge command currently authors one; there is no schema or write path in this repo to point to beyond that discovery reference | `skills/equip/SKILL.md`, "1. INVENTORY", item (a) |
| User-level custom skills | User space — `~/.claude/skills/`, resolved via `Path.home()` / `$HOME` | Byte-for-byte unchanged across `/forge:update` — a plugin update never touches `~/.claude/...` | Shipped as a discovery target (harness-native, not Forge-authored) — `equip` inventories these if present | `skills/equip/SKILL.md`, "1. INVENTORY", item (a) |

## Not customizable (for contrast)

Two surfaces worth naming explicitly because they are easy to mistake for
customizable: the global agent roster (`agents/*.md`) and the plugin's
skill library (`skills/*/SKILL.md`) both live under
`${CLAUDE_PLUGIN_ROOT}` — **plugin cache**, update-survival guarantee
**none** — and are owned entirely by the Forge release process. A human
extends the roster by adding a *project-local* agent (`.forge/agents/`,
above), never by editing a roster file in place; the same split applies to
skills.

## Scope note: what this table deliberately excludes

`docs/conventions/artifact-formats.md` documents several other `.forge/`
artifacts beyond this table's rows; each is excluded on purpose, not by
oversight:

- **`.forge/map/` (`architecture.md`, `index.md`, `conventions.md`,
  `hotspots.md`, `subsystems/`)** — project space, and technically
  human-editable (it's plain markdown a human could hand-edit), but it is
  not a *customization*: it's a derived artifact the `map` skill
  (re)builds from the repo itself (git churn, reference counts) and
  freshness-checks against `HEAD` every SYNC. Hand-editing it fights the
  next rebuild rather than persisting a preference, so it's out of scope
  here the same way a build output would be.
- **Queue task files (`.forge/queue/tasks/*.md`)** — already a row above
  ("Queue"); not re-listed separately per-field. A task's frontmatter
  fields (`tier`, `priority`, routing overrides) are edits to that same
  row's artifact, not a distinct storage surface.
- **"Offline merge convention," "Parallel dispatch," "Claims and crash
  recovery" (`docs/conventions/artifact-formats.md`)** — none of these
  name a new artifact; they describe kernel *behavior* over the Queue
  (frontmatter merge-conflict resolution, worktree claim/crash rules), not
  a separate storage surface a human customizes. Covered by the Queue row.

If a future artifact-formats.md section names a genuinely new
human-customizable surface not covered above, it belongs as a new row in
the table, not folded silently into this list.

## See also

- `docs/conventions/config-and-features.md`, "Customization persistence
  contract — 2026-07-18 (fg-b0101)" — the tier definitions and the
  `tools/validate_persistence_boundary.py` gate this table's "Shipped"
  rows are checked against.
- `docs/conventions/trust-and-security.md` — the trust-boundary and
  per-provider trust marker mechanics in full.
- `docs/conventions/agents-lifecycle.md` — project-local and ported agent
  lifecycle in full.
- `docs/conventions/memory.md` — project and craft memory in full.
