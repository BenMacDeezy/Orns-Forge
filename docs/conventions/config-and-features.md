# Config and features

<!-- Shard of docs/conventions.md (fg-b0401). Section bodies below are verbatim from the pre-sharding file; docs/conventions.md is now the index. See docs/conventions.md's Shards manifest for the full section -> shard map. -->

## forge.md (project config)

> Amended by: "Budget keys — amendment (2026-07-17)", "UI+motion task splitting, empty-repo gates-pending, and finder dispatch — 2026-07-18"

```markdown
# Forge config

## Routing overrides
<!-- optional lines: "<pattern or area>: <model>/<effort> — <reason>" -->
(none)

## Budgets
- session-token-cap: none
- max-tasks-per-session: none

## Queue
- claim-staleness-hours: 2

## Gates
- build: (auto-detect)
- test: (auto-detect)
- lint: (auto-detect)
```

Values under Gates may be exact shell commands; `(auto-detect)` tells the kernel to infer from the repo (package.json scripts, Makefile, etc.) and write what it found back into this file.

**Malformed forge.md.** If `.forge/forge.md` exists but cannot be parsed (missing `## Gates` section, unreadable values, truncated file), the kernel does not proceed with undefined gates: it re-infers gates from the repo exactly as it would for `(auto-detect)`, writes the recovered file back, and notes the recovery in the session report. If gates cannot be inferred either (no recognizable build/test tooling), the kernel halts before dispatching any task and reports a clear message asking a human to fill in `.forge/forge.md` manually.

## Asking the user questions (interactive skills)

Any Forge skill that stops to ask the user a decision — `discover`, `onboard`,
the `spec` pipeline's clarifications and approval, and any gated offer — must
**prefer the structured question tool** (Claude Code's `AskUserQuestion`, which
renders selectable option cards, supports a recommended default, allows
multi-select, and always adds an automatic "Other" for free input) over a
free-form prose question **whenever the answer is one of a small, enumerable
set of choices.** Use the structured format for:

- yes/no or recommended-default **gates** — "Run project discovery now?",
  "Approve this draft?", "Install this from the scout shortlist?";
- picking among **known alternatives** — stack/framework choices, an
  architecture pattern, a task's `tier` or `priority`, which milestone to spec
  next;
- any `[NEEDS CLARIFICATION]` whose resolution is effectively multiple-choice
  (offer the candidate answers as options).

Rules for structured questions:

- **Recommendation first.** Where the skill has a recommended answer, make it
  the first option and label it `(recommended)`.
- **One decision per question.** Keep each question to a single decision; you
  may batch a few genuinely related decisions into one `AskUserQuestion` call
  (each as its own question) rather than a long back-and-forth, but never
  merge unrelated decisions into one option list.
- **Don't force-fit open prompts.** Reserve free-text prose questions (asked
  one at a time) for **genuinely open-ended** prompts where enumerating options
  would be artificial — e.g. discovery's "What are you building, and what
  problem does it solve?" or "Who is it for?". For those, ask in prose; do not
  invent throwaway options just to use the tool.

Availability: the structured tool exists when a skill runs **interactively in
the main session**. In a headless/agent context where it isn't available, fall
back to prose questions with the same discipline (one decision at a time,
recommendation stated, candidate answers listed inline).

## Budget keys — amendment (2026-07-17)

Amends the forge.md example above:

- `max-tasks-per-session` is the **PRIMARY enforced cap**: the kernel counts
  dispatches per session and stops with a session report when it is reached.
  A PreToolUse hook (`budget-guard.sh`) may additionally deny dispatches past
  the cap — the one documented exception to the fail-silent-hooks doctrine;
  the kernel's own count remains the portable mechanism.
- `session-token-cap` is **advisory only**: the model may stop early on its
  own spend estimate; it is not the enforcement mechanism. Both keys remain.
- New Queue key: `max-parallel-tasks` (default 3) caps a parallel-dispatch
  batch (see Parallel dispatch, above).

## Budget keys — amendment (2026-07-19): provider dispatch cap (fg-c0113, spec-e8a3)

Amends the forge.md example above and "Budget keys — amendment
(2026-07-17)". Binding text: spec-e8a3
(`.forge/specs/2026-07-19-provider-profiles.md`), "Budget accounting
across billing currencies" (RESOLVED option c).

- New Budgets key: `max-provider-dispatches-per-session` (default 10) —
  counts external-provider dispatches, checked at ROUTE time exactly like
  the existing floors (`max-tasks-per-session`, `session-token-cap`).
- `session-token-cap` remains Claude-token-only: an external-provider
  dispatch is never folded into `session-token-cap` — no cross-currency
  estimate ever, matching the telemetry never-invent-a-number rule.
- A session at the provider cap dispatches no further external work and states so in the session report.

## Features (forge.md)

> Amended by: "Trust boundary — specs + NL scoping amendment (2026-07-17)"

forge.md carries a `## Features` section of behavior toggles (`on`/`off`).
The config template (`skills/kernel/references/forge-config-template.md`)
holds the defaults; a forge.md written before this section existed simply has
no toggles on disk — **every missing toggle behaves as its default**, and
`/forge:settings` offers to write the section in. `/forge:settings` is the
canonical viewer/editor for all of forge.md's settings.

| Toggle | Default | Meaning |
|---|---|---|
| `natural-language-invocation` | on | Forge skills fire from plain conversation ("work through the queue", "queue this", "let's build X"). `off` = skills activate only on explicit `/forge:*` commands. |
| `continuous-loop` | on | Completing a wave re-checks the queue once for newly-ready tasks (dependencies may have resolved) and continues. `off` = the kernel processes exactly one wave per invocation, then stops with the session report. |
| `auto-queue-capture` | on | Task-shaped ideas mentioned in conversation without an execution ask are OFFERED for capture into the queue — one structured offer per idea, never a silent task creation. `off` = capture only on explicit ask. |
| `express-lane` | on | Standard-tier ideas skip the spec pipeline via one structured confirm card (`forge:spec`, "Express lane"). Never applies to `tier: full` — full-tier work always takes the spec approval gate. |
| `workflow-executor` | on | Parallel-eligible waves and full-tier ship reviews run as deterministic Workflow scripts when the harness offers the Workflow tool (`forge:kernel`, "Executor"). `off` (or tool absent) = the sequential markdown loop, identical behavior. |

**Consent rule:** `continuous-loop: on` constitutes standing human
authorization for the loop to continue pulling waves — the human granted it
by enabling the setting; the kernel still stops at `max-tasks-per-session`,
empty queue, or interrupt. No toggle ever overrides a budget cap, the spec
approval gate for full-tier work, or the trust boundary.

## Freshness convention (date-sensitive skills) — 2026-07-18

Response to `docs/audits/2026-07-18-sweep3-efficiency.md` (task fg-9c0305).
Some skills document guidance that is **ecosystem-dependent** — it describes
the current shape of a fast-moving external surface (a framework version, a
library's API, a tool's default behavior) rather than a timeless Forge
protocol rule. That guidance can go stale silently: nothing about the skill
file itself signals "this was true as of when," so a consumer has no way to
tell a freshly-verified recommendation from one nobody has re-checked in a
year.

**Which skills this applies to.** Date-sensitive skills — concretely, the
frontend/animation cluster (component/framework/tooling guidance tied to a
specific library's current API or defaults) and scout shortlists (vetted
tool/MCP/skill recommendations, which age as the ecosystem moves) — carry a
freshness stamp. Skills whose content is a Forge-internal protocol rule
(kernel, queue, spec, ship, trust boundary, etc.) are not date-sensitive in
this sense and do not require one; timeless guidance doesn't need a
re-verify clock.

**The stamp.** A date-sensitive skill carries a `last-verified: YYYY-MM`
marker — either a frontmatter field or, matching the pattern already in use
across several frontend-cluster skills, an HTML comment on the first line
after the closing frontmatter `---` and before the H1 title:

```
---
name: <skill-name>
description: ...
---

<!-- last-verified: 2026-07 -->

# <Skill title>
```

**Consumer rule.** Treat guidance carrying a `last-verified` stamp older
than **~12 months** as re-verify-before-trusting, not as ground truth to
act on unchecked — the ecosystem it describes may have moved. A skill with
no stamp at all is not implicitly exempt; it simply hasn't been brought
under this convention yet, and should be treated with the same caution as
a stale stamp until it is. Re-verifying and updating the stamp is a normal,
low-ceremony edit — bump the `YYYY-MM` to the current month once the
content has been checked against the current ecosystem state, no other
process required.

## Capability-gap audits (equip) — 2026-07

`forge:equip` (`/forge:equip`) is the project's capability-gap diff engine:
it inventories the actual capability surface (skills, agent roster +
attachments, MCP servers confirmed connected via tool-listing evidence — a
config file merely naming one is never sufficient, `skills/equip/SKILL.md`
INVENTORY (c)), and stack-relevant CLIs), diffs that against
`.forge/project.md`, the map, and backlog themes, and presents ranked
find/create/wire/skip proposals via structured option cards. Equip
**decides whether and why a gap exists; it never fills one itself** — a
FIND action hands the specific tool decision to `forge:scout` (which then
applies its own vet-every-candidate and license rules), a CREATE action
becomes a normal queued task built and verified like any other queue work,
and a WIRE action runs `/forge:seed` or surfaces a disabled MCP for the
human to enable. Equip edits no MCP/`~/.claude`/project config itself, same
hard rule as scout.

Equip is **repeatable maintenance**, not the one-time setup `forge:onboard`
performs, and it **consumes** an existing project charter rather than
interviewing for one (`forge:discover`'s job) — no charter, or an
unapproved `draft` one, routes to discover/onboard first instead of equip
inventing goals from the file tree.

**Skip-decision memory.** When a human picks SKIP on a proposed gap, equip
records it as a `decision` fact via `forge:memory` (what was skipped, why,
when) so re-runs read it back and don't re-nag on an already-decided gap —
the same idempotent-re-run discipline every other Forge audit pass follows.

## Providers Feature — per-repo opt-in and per-provider trust gate — 2026-07-19 (fg-c0103, spec-e8a3)

> Amends: "Features (forge.md)" (above).

Response to `.forge/specs/2026-07-19-provider-profiles.md` (spec-e8a3,
"Per-repo opt-in and per-provider trust"). Extends the Features vocabulary
(table above) with one new toggle and states the gate in full: enabling any
external provider is a two-step confirm, never a single toggle flip.

| Toggle | Default | Meaning |
|---|---|---|
| `providers` | off | External providers (second opinions, cross-model review, and — Phase 2 — worker dispatch) may be enabled for this repo. **OFF by default for every repo that has not explicitly turned it on** — with `providers: off`, Forge never invokes an external provider CLI, regardless of any per-provider trust confirmation already on disk. `on` unlocks per-provider enablement, each still gated by its own once-per-provider-per-repo-per-machine trust confirmation (Step 2, below). |

**Step 1 — the `providers` Feature (per-repo opt-in).** `providers` joins
the Features vocabulary **OFF by default**, unlike every toggle already in
the table above (all default `on`) — external-provider dispatch sends repo
content to another vendor, so this is the one toggle that must be
explicitly turned on before anything downstream can fire, not explicitly
turned off to prevent it. A `forge.md` written before this section existed
has no `providers` line on disk; per the missing-toggle rule above, that
behaves as its default — `off` — exactly like any other missing toggle,
never as an implicit opt-in. `/forge:settings` (and, if `settings.md`
cannot host the flow, a dedicated `/forge:providers` entry point) is the
sole place this Feature is toggled, matching every other Features-table
edit path.

**Step 2 — per-provider trust confirmation (TOFU, applied per provider).**
`providers: on` unlocks the *ability* to enable a provider; it does not by
itself trust one. The first time a specific provider is enabled in a repo,
Forge presents a trust confirmation — dispatching sends this repo's content
to that vendor's CLI — gated with the **same TOFU shape** as
`docs/conventions/trust-and-security.md`'s "Trust model: local
trust-on-first-use (TOFU)", scoped down from per-`.forge/` to per-provider:
confirmed once per provider, per repo, per machine, never re-prompted after
that on the same machine, and never satisfied by a committed record (see
`docs/conventions/trust-and-security.md`, "Per-provider trust confirmation
— 2026-07-19 (fg-c0103, spec-e8a3)" for the confirmation-record format and
storage path).

**Both gates are independent and both must hold.** Turning `providers: on`
without confirming a given provider does not enable that provider — the
per-provider confirmation gate below still blocks it. Turning `providers`
back `off` does not clear any provider's trust confirmation on disk (TOFU
records are additive, same as `.forge/.trust-local`); it only re-closes the
repo-level gate, so re-enabling later does not re-prompt already-confirmed
providers. No toggle or confirmation here overrides a budget cap, the spec
approval gate for full-tier work, or the repo-level trust boundary — same
"No toggle ever overrides..." rule stated above for every other Feature.
## Customization persistence contract — 2026-07-18 (fg-b0101)

Root contract item of `spec-4d2a` (operator profile system). Every Forge
feature that lets a human customize their setup — operator profiles,
provider profiles (`fg-a10902`), ported agents, project-local agents,
custom settings — must write that customization into one of exactly three
storage tiers, never into the plugin's own installed directory
(`${CLAUDE_PLUGIN_ROOT}`). A plugin update overwrites everything under
`${CLAUDE_PLUGIN_ROOT}` wholesale; anything a human customized that lived
there would be silently destroyed on the next `/forge:update`. The three
tiers:

- **Plugin cache** — `${CLAUDE_PLUGIN_ROOT}` itself: the plugin's own
  installed directory (`skills/`, `commands/`, `hooks/`, `tools/`,
  `agents/`, `assets/`, this doc tree). Owned entirely by the Forge
  release process. **Update-survival guarantee: none.** `/forge:update`
  replaces this tree wholesale; nothing a human customized may live here,
  because it will not survive the next update. Forge code reads from this
  tier constantly (stock profile definitions, skill bodies, agent roster
  files) but never writes a human customization into it.
- **User space** — `~/.claude/...`, resolved via `Path.home()` (Python) or
  `$HOME`/`$USERPROFILE` (bash), outside any single project's working
  tree. Holds customizations that follow the human across every repo they
  use Forge in — e.g. `~/.claude/settings.json` hook/autorun wiring, the
  örn banner shim. **Update-survival guarantee: byte-for-byte unchanged**
  across a `/forge:update` — a plugin update only ever touches
  `${CLAUDE_PLUGIN_ROOT}`, never `~/.claude/...`.
- **Project space** — `.forge/` at the repo root, resolved relative to
  `${CLAUDE_PROJECT_DIR}` and git-tracked with the repo. Holds
  customizations scoped to one project — queue tasks, memory, specs,
  `.forge/forge.md` config (including the future `## Operator profile`
  section), `.forge/profiles/*.md` custom overlay profiles,
  `.forge/agents/` project-local and ported agents. **Update-survival
  guarantee: byte-for-byte unchanged** across a `/forge:update`, same
  reasoning as user space — nothing under `.forge/` is part of the
  plugin's own installed directory.

**The gate.** `tools/validate_persistence_boundary.py` scans the plugin
source tree (`skills/`, `commands/`, `hooks/`, `tools/`, `agents/`) for
file-write idioms (`open(path, "w"/"a"/...)`, `Path.write_text`,
`shutil.copy*`/`shutil.move`/`shutil.copytree` in Python; `>`/`>>`
redirects and `cp`/`mv`/`tee` in bash `.sh` scripts) whose destination
resolves under the plugin's own installed directory instead of project
space or user space, and fails with the offending `file:line` if one is
found. It is deliberately scoped to the write-idiom classes actually
present in this repo today — its own module docstring states plainly what
it does not catch (third-party library write methods, shelled-out writes,
dynamic/command-substitution destinations) rather than overclaiming
coverage. A clean run is a precondition for any change touching
`skills/`, `commands/`, `hooks/`, `tools/`, or `agents/`; see
`docs/customization-persistence.md` (`fg-b0104`) for the human-facing
per-surface table this contract backs.

## Operator-profile container format — 2026-07-18 (fg-b0103, spec-4d2a)

The shared overlay-profile container `spec-4d2a` (operator profile system)
and `fg-a10902`'s future providers spec both extend, rather than each
building their own storage/schema/picker machinery — full format defined
in `skills/kernel/references/operator-profiles.md`, NORMATIVE; this section
is the dated-conventions pointer, not a restatement.

**One file format, two optional domain sections.** A profile file is a
plain markdown document (no YAML frontmatter, same house style as
`.forge/forge.md`) with one required `## Meta` section (`schema-version`,
`kind: stock | preset | custom`, `name`, and — for `kind: custom` only —
a `base` naming the stock/preset profile its sections store deltas over)
followed by zero or more named top-level domain sections: `## Autonomy`
(this spec's own domain, content shipped by `fg-b0105`) and `## Providers`
(reserved — absent from every profile file until `fg-a10902`'s own future
spec populates it). One schema-versioned container expresses both an
autonomy stance and, later, a provider stance without a format change.

**Storage split follows the persistence contract above.** Stock and
preset profiles ship read-only inside the plugin (plugin-cache tier —
Forge code reads them constantly, never writes a customization into one).
Customizing a stock or preset profile means copying it into a new named
CUSTOM profile file under `.forge/profiles/<name>.md` (project space)
storing only the DELTAS over its `base` — the stock/preset source is
never modified in place. A Forge plugin update that ships a new stock
profile, adds a preset, or changes the profile schema never modifies or
deletes a file under `.forge/profiles/`; a custom profile referencing a
key the update removed degrades to the current stock default for that key
with one warning line, never a hard failure.

**Lossless switching.** The active profile is named by exactly one
pointer line in a `.forge/forge.md` `## Operator profile` section
(`active: stock:<name> | custom:<name>`; that section's own template and
kernel gate wiring is `fg-b0105`'s boundary). Switching the pointer never
reads, writes, or deletes any profile file — switching back to a
previously-used custom profile restores its exact prior behavior, lossless
in both directions, by construction rather than extra bookkeeping.

**Validation.** `tools/validate_config.py`'s `validate_profile()` checks
the container structurally: `## Meta` required with a valid
`schema-version`/`kind`/`name` (and `base` for `kind: custom`); every
other top-level `## ` section parsed as `- key: value` bullets, with a
malformed line or in-section duplicate key an error, but a domain SECTION
name outside `{Autonomy, Providers}` only a forward-compat WARNING, never
an error — matching the same warn-not-fail shape `KNOWN_FEATURES` already
applies to unrecognized `.forge/forge.md` Features toggle names. A path
under `.forge/profiles/` routes to this validator automatically from
`validate_config.py`'s CLI; every other path validates as `.forge/forge.md`
exactly as before. Domain-owned key/value semantics (what `## Autonomy`
keys mean) are out of scope for this validator by design — each domain
spec owns its own key vocabulary. This task ships the container only: no
live file under `.forge/profiles/` exists in this repo yet, and no
`## Providers` content — `fg-b0105` and `fg-a10902` populate their own
domains on top of it.

## Operator profile system — 2026-07-18 (fg-b0104, spec-4d2a)

Wires the shared profile container (above, `fg-b0103`) into the kernel
loop. Full NORMATIVE detail lives in `skills/kernel/references/
profile-wiring.md`; this section is the dated-conventions pointer, not a
restatement.

**Pointer + missing-section default.** The active profile is named by a
`.forge/forge.md` `## Operator profile` section (`active: stock:<name> |
custom:<name>`, template: `skills/kernel/references/
forge-config-template.md`). A forge.md predating this section behaves as
if it named the default stock profile for this install — `stock:guided`
for a fresh install (no prior `.forge/` state), `stock:full-auto` for an
existing install (maps current behavior forward unchanged) — rendered
`(default — not yet in forge.md)`, the same missing-toggle-means-default
convention "Features (forge.md)" already establishes.

**Precedence.** Every profile-covered setting (approval-gate pause
points, verification-panel settings, wave-size) resolves lowest to
highest: the active profile's preset default, overridden by an explicit
value already set elsewhere in `.forge/forge.md` (Features/Budgets/
Queue), overridden in turn by the FLOOR below, which always wins.

**Floor (never relaxed).** No profile preset — stock, preset, or custom —
relaxes the trust boundary's first-touch confirm, raises
`max-tasks-per-session` / `session-token-cap` beyond what the human set,
or skips the `tier: full` spec approval gate
(`skills/spec/SKILL.md`, "5. Approval gate"). A preset value conflicting
with any of the three is enforced as the floor; only the conflicting
portion of the preset is ignored, the rest still applies.

**Pause-point enforcement — all tiers.** The active profile names zero or
more of three kernel points as pause points: a dispatch batch (ROUTE +
DISPATCH), INTEGRATE, and plan/spec review (PLAN, and — where marked —
before the spec skill's own always-mandatory approval gate). At a marked
point the kernel stops and presents a structured `AskUserQuestion`
confirm — exactly the pause points that profile names, no more, no
fewer. This applies at every tier, not only `tier: full`'s pre-existing
plan/ship-review steps — "review all plans" means every dispatch batch
can pause.

**Provider-review graceful-degrade.** A profile preset setting a role's
review to `provider-review: advisory | verdict` is OPTIONAL gate input.
WHEN no provider is enabled or available (`providers: off`, or the
specific provider's per-repo trust marker absent), the gate degrades to
human-only with one stated note naming which provider was configured and
why it didn't participate — never a silent skip, never a block waiting
for the provider.

**Settings surface.** `/forge:settings` renders the `active:` pointer
(missing-section default included) alongside Features/Budgets/Queue;
picking a different profile, listing stock/preset/custom side by side,
and the create-custom-profile flow are `fg-b0106`'s picker UX, not built
by this task.

## Plugin lifecycle: uninstall + rollback — 2026-07-20

Two shipped commands, `/forge:uninstall` (`fg-b0205`) and `/forge:update
--version vX.Y.Z` (`fg-b0206`), together define Forge's plugin lifecycle
surface — removal and rollback — on the same "Forge sequences the real CLI,
Forge never touches the network itself" posture the "Customization
persistence contract" above already establishes for installs. This section
is a dated summary by citation; the full normative text lives in
`commands/uninstall.md` and `commands/update.md` and is never restated
here.

**`/forge:uninstall` — confirm-gated removal, interactive-only.** Full
contract: `commands/uninstall.md`. It sequences the real CLI's own
`claude plugin uninstall` / `claude plugin marketplace remove` commands,
cleans up the shims Forge itself installed
(`python tools/banner_install.py uninstall`), then offers `.forge/`
removal through exactly one structured `AskUserQuestion` confirm — scoped
to the current repo's own `.forge/` only, never a filesystem scan for any
other repo's. **Interactive-only**: no `--yes`/`--force` flag exists or
will be added; invoked from a non-interactive context it stops and reports
that an interactive session is required instead of guessing an answer.
Declining the `.forge/` prompt leaves it fully intact — no queue task,
spec, memory file, constitution, or config under it is touched.

**`/forge:update --version vX.Y.Z` — rollback with a schema-check stop
rule.** Full contract: `commands/update.md`, "Version rollback:
`/forge:update --version vX.Y.Z`". It installs exactly the tree the public
mirror's `vX.Y.Z` tag points at (fresh-history-per-release,
`fg-a10913`'s release convention). Before installing anything it runs a
**proactive schema-version compatibility check** — the single,
narrowly-declared exception to Forge's standing "never fetches or executes
plugin code from the network itself" rule, scoped to a **read-only** read
of the target tag's `SUPPORTED_SCHEMA` constant (grep, or `git show
<tag>:tools/validate_task.py` piped through a plain-text constant
extraction — never a clone-and-run, never importing or `eval`-ing anything
from the fetched tree). If the target version's supported schema is lower
than the highest `schema-version` already present across this repo's
`.forge/` task, spec, and memory files, it surfaces the `fg-e106`
compatibility message verbatim and **stops before installing** — never
partially applying the rollback. **Scope — plugin version rollback only:**
this flow never rewinds mid-task queue execution state (in-flight claims,
partial diffs, an interrupted wave); that concern stays `fg-a10302`'s
deferred/backlog item per that spec's own Non-goals, untouched by which
plugin version is installed.


## Codex native skill discovery — optional registration (codex-skill-loading, 2026-07-21)

Full normative rules for skill materialization (the guaranteed floor every
provider dispatch gets) and this optional registration surface live in
`skills/kernel/references/provider-judges.md`, section 8 — this section is
the dated conventions pointer plus the registration how-to, not a second
copy of the normative text.

**What this is.** Codex CLI (verified against the installed 0.137.0,
provider research 2026-07-21) natively discovers Agent Skills from
`$CODEX_HOME/skills` (`~/.codex/skills`) and the cross-tool standard root
`~/.agents/skills` (plus a project-local `.agents/skills`, project taking
precedence over user) — discovery is automatic, no CLI flag, and
`[[skills.config]]` in `config.toml` only enables/disables skills already
discovered, never adds a root. Forge's SKILL.md frontmatter (`name` +
`description`) is verbatim-compatible with what Codex reads.

**Curated subset, not all 60.** Loading is lazy per the agentskills spec
(metadata first, body on trigger), but the metadata pass is budgeted to
roughly 2% of context or 8,000 characters, whichever is smaller. Forge's
full skill set (~60 skills) carries roughly 29,200 measured characters of
descriptions — about 3.5x that budget — and overflow behavior once the
budget is exceeded is undocumented upstream. Registering the whole
`skills/` directory globally is therefore NOT recommended. Instead,
register only the curated subset actually attached to provider-eligible
roles (the skills a `provider:`-routed task's contract would attach) —
keeping registered metadata well under the 8,000-character ceiling and
avoiding undocumented overflow behavior entirely.

**Registration steps (human-run, per skill, no admin rights on Windows):**

```
mklink /J "%USERPROFILE%\.agents\skills\<name>" "<forge-plugin-root>\skills\<name>"
```

Run once per skill in the curated subset — a per-skill junction, not one
parent junction over all of `skills/` (recursion depth under Codex's scan
roots is unverified). Junctions survive `codex` CLI updates because
`$CODEX_HOME` is untouched by npm/CLI upgrades.

**Precondition — human-run canary test.** Before relying on native
discovery in any automated flow, a human must confirm `codex exec`
(Codex's non-interactive dispatch mode) discovers registered skills
identically to the interactive TUI — this is UNVERIFIED by this task's
research and Forge itself SHALL NOT run `codex exec` to test it: zero live
provider dispatches until a human has logged in and the per-provider trust
marker (`.forge/.trust-providers/codex.local`) is present. Materialization
(provider-judges.md §8.1) remains the guaranteed floor regardless of
whether this canary test has been run or what it finds.

**Trust note.** Registering skills into `~/.agents/skills` exposes their
content to every Codex session on the machine, not only Forge-dispatched
ones — broader exposure than a single dispatch's worktree materialization.
This is the same trust boundary the per-provider TOFU confirmation already
covers (`docs/conventions/trust-and-security.md`, "Per-provider trust
confirmation — 2026-07-19"); registration is why it stays human-run rather
than something Forge does on the provider's behalf.

## Per-provider dispatch toggles (`forge.md` Providers section) — 2026-07-21 (provider-toggles)

> Amends: "Providers Feature — per-repo opt-in and per-provider trust gate
> — 2026-07-19" (above).

Origin: 2026-07-21 user directive ("per-provider toggles + 'a more in
depth setting system'"). Extends the `providers` Feature (above) with a
per-provider on/off toggle in a new `.forge/forge.md` `## Providers`
section — `- codex: on`, `- grok: off`, ... (template:
`skills/kernel/references/forge-config-template.md`). This is a DIFFERENT
surface from an operator profile's own `## Providers` DOMAIN section
(`enabled-providers`/`role-*`/tier-map keys, `skills/kernel/references/
operator-profiles.md`) — the forge.md toggle gates WHETHER a provider may
dispatch at all for this repo; the profile domain decides WHICH provider a
given role resolves to once dispatch is allowed. Both must cooperate: a
profile assigning a role to a provider whose forge.md toggle is off still
does not dispatch.

**Four independent gate layers.** A provider dispatches only when ALL of
the following hold, each checked independently and in this order —
mechanics, the exact blocked-dispatch line format, and the wiring into the
codex co-verifier resolution chain live in `skills/kernel/references/
provider-judges.md`, section 1a (NORMATIVE; cited here, not restated):

1. the global `providers` Feature (above) is `on` for this repo;
2. that provider's OWN forge.md `## Providers` toggle is `on`;
3. that provider's TOFU trust marker
   (`.forge/.trust-providers/<provider-id>.local`) is present
   ("Per-provider trust confirmation — 2026-07-19", above);
4. the dispatch cap (`max-provider-dispatches-per-session`, "Budget keys —
   amendment (2026-07-19)", above) has headroom.

A blocked dispatch always states which ONE layer blocked it via a single
labeled line (`provider-judges.md` §1a's `provider-gate-blocked: <provider>
layer=<layer> — <reason>` format) — never a bare refusal, never a
multi-line dump of every layer's state.

**Missing-toggle exception — the one surface where missing means OFF.**
Every other forge.md toggle this doc's "Features (forge.md)" section
documents behaves as its DEFAULT when absent from disk, and most Features
defaults are `on` — a missing key there means the feature is active. The
per-provider `## Providers` toggle inverts that norm on purpose: a
provider id absent from the section, or the whole `## Providers` section
absent from forge.md, resolves to OFF, not to some documented "default"
value. This is stated explicitly because it is the exception, not because
a new rule was invented — it mirrors the global `providers` Feature's own
default-off posture (a repo that has never touched provider config gets
zero external dispatch, full stop) rather than the missing-toggle-means-
default-ON shape every other Features/Budgets/Queue key follows.

**Toggling off never clears TOFU.** Setting a provider's forge.md toggle to
`off` leaves that provider's `.forge/.trust-providers/<provider-id>.local`
marker untouched — re-enabling the toggle later does not re-prompt the
trust confirmation, the same additive-record behavior "Both gates are
independent and both must hold" (above) already guarantees one level up
for the `providers` Feature itself.

**Pilot gates are never overridden by a toggle.** `grok` and `antigravity`
stay undispatchable pending human pilot-evidence review regardless of what
their forge.md toggle says (`operator-profiles.md`'s "accepted and stored,
never itself the thing that clears the gate" posture applies identically
here) — a toggle is accepted and stored but never itself the mechanism
that clears a pilot gate.

**Settings surface.** `/forge:settings` is the sole editor for this section
(`commands/settings.md`) and its per-provider view additionally shows each
provider's trust-marker presence and pilot-gate status alongside the
toggle — see "Settings schema registry" below for the canonical key list
this and every other forge.md setting is drawn from.

## Settings schema registry — one canonical place — 2026-07-21 (settings-system-depth)

Origin: same 2026-07-21 user directive as the section above (batched
sibling pair). `/forge:settings`, `tools/validate_config.py`, and this doc
tree each independently knew a subset of "every setting forge.md can carry"
before this task — a new key added to only one of the three would silently
drift the others out of sync. `skills/kernel/references/settings-
schema.md` (NORMATIVE) is now the ONE canonical place a new forge.md
setting is added: every section (Features / Budgets / Providers / Queue /
Gates / Routing overrides), every key's type, default, allowed values,
one-line meaning, and whether it carries a floor-protection flag.
`/forge:settings`'s no-args full view, `tools/validate_config.py`'s
key-level checks, and this doc's own Features/Budgets/Providers tables
above all read from that one registry rather than each maintaining a
separate copy — adding a key means editing `settings-schema.md` once, not
three files in three different styles.

**Floor-protected settings.** A subset of forge.md's surface is a FLOOR —
never relaxed by a settings edit regardless of how the edit is phrased:
trust confirmations (a settings edit never clears or forges a
`.forge/.trust-providers/*.local` or `.forge/.trust-local` marker),
human-set budget caps (`max-tasks-per-session`, `session-token-cap`,
`max-provider-dispatches-per-session` — an edit may only ever be set BY a
human through this same surface, never silently raised past what a human
set as a side effect of some other change, mirroring `skills/kernel/
references/profile-wiring.md`'s "Floor (never relaxed)"), the `tier: full`
spec approval gate (no forge.md key exists, or will be added, to skip it),
and the `providers` Feature's default-off posture (no edit path may change
what a repo that has never touched provider config gets — zero external
dispatch — since that default IS the floor, not merely a starting value).
`settings-schema.md` marks each registry entry that carries one of these
four floors; `/forge:settings` refuses a write that would cross one and
names the floor in its refusal, per `commands/settings.md`'s own edit
step.

## Provider dispatch checkpoints — 2026-07-22 (owner-ratified)

Amends "Budget keys — amendment (2026-07-19): provider dispatch cap
(fg-c0113, spec-e8a3)" above at the owner's direction: a hard
per-session dispatch ceiling does not fit long-running, self-improving
kernel sessions, and the provider's own plan rate limits (surfaced by
the provider CLI itself) are the true consumption backstop. Ratified
2026-07-22 by the owner via structured question ("Checkpoint model").

- `max-provider-dispatches-per-session` remains schemaed and, when set
  to a number, keeps its original hard-cap semantics unchanged — a repo
  that wants a hard ceiling still gets one. `none` (the new recorded
  value in this repo) disables the hard ceiling.
- New Budgets key: `provider-dispatch-checkpoint-every` (default 10) —
  WHEN the session's running provider-dispatch tally crosses a multiple
  of this value, THE SYSTEM SHALL post a one-line spend checkpoint
  (tally, providers used, exact model slugs per the provider-dispatch-
  labels convention) and continue unless the human objects — a
  visibility-and-consent cadence, not a stop.
- The running tally itself appears in every session report regardless
  of cadence, and a provider-side rate-limit error is always surfaced
  verbatim as a labeled line, never retried silently.
- **Global, provider-agnostic**: this is the SHIPPED DEFAULT for every
  Forge repo and every provider (codex, grok, antigravity, and any future
  provider profile alike) — the config template records
  `max-provider-dispatches-per-session: none` +
  `provider-dispatch-checkpoint-every: 10`, and the tally/checkpoint
  counts all providers combined with per-provider breakdown in the
  checkpoint line. A repo wanting a hard ceiling sets a number and gets
  the original fg-c0113 semantics unchanged. Provider enablement itself
  is untouched: the `providers` Feature and every per-provider gate stay
  default-off, so the checkpoint model only ever governs dispatches a
  human has already enabled.
- Floors unchanged: this amendment touches ONLY the cap key's value and
  adds the checkpoint cadence — the four-layer per-provider gate, TOFU
  confirmations, and pilot gates are untouched by it.

## Startup banner removed — 2026-07-22 (owner-directed)

The startup-banner feature (the welcome-area `orn-motd.sh` SessionStart
hook plus the opt-in `/forge:banner install|uninstall|status` launcher-shim
takeover) is removed after three real-machine incidents traced to its
patch-engine code. The historical sections above (and the shard files they
point to) that describe the banner shim, its `startup-banner` toggle, and
its persistence-boundary row remain as-is — they are the record of what was
built and why it was hardened, not a live spec. The full incident history
and hardening record lives in queue record `bm-banner-takeover.md`.

## max-parallel-tasks: auto default — 2026-07-23 (owner-directed)

Amends this file's "Budget keys — amendment (2026-07-17)" entry
(`max-parallel-tasks` "default 3"), and the same "default 3" parenthetical in
`docs/conventions/dispatch-and-routing.md` ("Sliding-window dispatch") and
`docs/conventions/artifact-formats.md` (batch-size rule). The key and its
sliding-window semantics are UNCHANGED; only the default and the accepted
value set change.

**`max-parallel-tasks` now defaults to `auto` and accepts
`auto | none | <positive int>`.**

- **`auto`** (the new default, and what an absent key means) derives the
  window from the machine: `min(cores - 2, 16)`, floored at 1. Two cores stay
  free so the orchestrating session stays responsive while workers build, and
  the ceiling keeps N concurrent worktree installs/builds/test-runs from
  thrashing disk and RAM — past the physical ceiling runs get slower and
  flakier, not faster, and bogus build failures cost real tokens on bounce +
  re-verify. Mirrors the harness's own `min(16, cores - 2)` agent-concurrency
  shape.
- **`none`** removes the window entirely — unbounded simultaneous spawns.
  Supported deliberately; whoever sets it owns the resource contention and any
  rate-limit fallout.
- **A positive integer** is used verbatim, no derivation.

`tools/validate_config.py`'s `resolve_max_parallel_tasks()` is the single
resolver: callers read it rather than re-deriving `auto`, so the window means
the same thing everywhere. The old hard-coded `3` was a conservative constant,
never a derived one (this repo's own `forge.md` already overrode it to 6 by
hand), and it left a 32-core machine near 10% utilisation — against the
ratified parallelization-first objective.

**This is a throughput knob, NEVER a spend guard.** It caps how many workers
run AT ONCE, never how many tasks a session eventually runs — surplus tasks
still dispatch the moment a slot frees. Total cost stays bounded by
`max-tasks-per-session`, `session-token-cap`,
`max-provider-dispatches-per-session`, and `budget-guard`; widening or
removing this window overrides none of them. `.forge/` writes and merges stay
strictly serialized and kernel-owned at any window size (Hard Rule 4 /
INTEGRATE sequencing).
