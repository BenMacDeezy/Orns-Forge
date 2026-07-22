# Operator profile container format (reference)

NORMATIVE. This is the ONE shared overlay-profile container `spec-4d2a`
(operator profile system) and `fg-a10902`'s future providers spec both ride
on — schema-versioned, domain-sectioned, storage-located, and
lossless-switching by construction. It defines the FORMAT only: no
`## Autonomy` domain content (stock profile names, pause points,
verification-panel settings, wave-size keys — `fg-b0105`'s job) and no
`## Providers` domain content (`fg-a10902`'s own future spec) lives here.
A domain spec extends this container by adding its own section body; it
never defines a second file format, storage location, or pointer scheme.

## Why one container, two domains

`fg-a10902` already specifies the overlay-profile MODEL (immutable stock,
named delta-based customs, lossless switching) as its own acceptance
criteria against this same container — see
`.forge/specs/2026-07-19-provider-profiles.md`, "Overlay-profile model —
extends spec-4d2a's shared container". Building that machinery twice would
duplicate storage, pointer, and picker logic and let the two domains drift
out of sync. Resolution: **one profile file format, two optional top-level
domain sections** — `## Autonomy` and `## Providers` — sharing one
schema-versioned container, one storage location, one active-profile
pointer, and (future, `fg-b0105`+picker item) one picker.

## File shape

A profile file is a plain markdown document — no YAML frontmatter, same
house style as `.forge/forge.md` (`docs/conventions.md`, "forge.md
(project config)") — with one required `## Meta` section followed by zero
or more named top-level domain sections:

```markdown
# Profile: <name>

## Meta
- schema-version: 1
- kind: stock            <!-- stock | preset | custom -->
- name: <name>
- base: (none)            <!-- stock/preset: ignored. custom: REQUIRED —
                                the stock/preset name this profile's
                                deltas are computed over. -->

## Autonomy
- <domain-owned key>: <domain-owned value>
<!-- fg-b0105's content lives here; this file defines the container only -->

## Providers
<!-- reserved for fg-a10902; SHALL remain absent from every profile file
     shipped by this task, and from any file this task's validator sees,
     until fg-a10902's own spec populates it. Its presence here is a
     format guarantee, not a promise of content. -->
```

**`## Meta` keys.**

- `schema-version` — positive integer. Bumped only when the container
  FORMAT changes (new required Meta key, new section-nesting rule) — never
  for ordinary domain-content additions, which are forward-compatible by
  the warn-not-fail rule below.
- `kind` — exactly one of `stock | preset | custom`. `stock` is the one
  profile Forge ships as the out-of-the-box default per domain; `preset`
  is any additional Forge-shipped named option; `custom` is a human-created
  overlay. Stock and preset profiles ship READ-ONLY inside the plugin
  (plugin-cache tier, `docs/conventions.md`, "Customization persistence
  contract — 2026-07-18 (fg-b0101)") — never under `.forge/profiles/`, and
  never written to by any Forge code path. Only `custom` profiles live
  under `.forge/profiles/`.
- `name` — the profile's own name, matching its filename stem for a custom
  profile (`.forge/profiles/<name>.md` holds the profile named `<name>`).
- `base` — REQUIRED and non-`(none)` for `kind: custom`: names the
  stock or preset profile this file's sections store DELTAS over. Ignored
  for `kind: stock`/`kind: preset` (no base to overlay).

**Domain sections.** Every top-level `## ` heading other than `Meta` is a
domain section, parsed as `- key: value` bullet lines (identical shape to
`.forge/forge.md`'s Features/Budgets/Queue sections). A domain section
named outside the known set (`Autonomy`, `Providers`) is a forward-compat
WARNING, never an error — a newer Forge, or a future domain spec, may add
sections this container's validator doesn't know about yet. Domain KEY
vocabulary (which keys are valid inside `## Autonomy`, what values they
take) is entirely out of this file's scope — each domain spec owns and
documents its own keys; this container only enforces well-formed
`- key: value` structure and duplicate-key/duplicate-section detection.

## Storage and immutability

- **Stock and preset profiles** ship inside the plugin's own installed
  directory (plugin-cache tier — read by Forge code constantly, never
  written to as a customization target). `/forge:update` replaces them
  wholesale along with the rest of the plugin tree; a human never edits
  one directly.
- **Custom profiles** live ONLY under `.forge/profiles/<name>.md` —
  project space, git-tracked with the repo, byte-for-byte untouched by
  `/forge:update` (`docs/conventions.md`, "Customization persistence
  contract — 2026-07-18 (fg-b0101)"). Customizing a stock or preset
  profile means COPYING it into a new named custom profile file that
  stores only the deltas over its `base` — the stock/preset source file is
  never modified in place. This is the same copy-on-write shape the
  persistence contract requires of every other customizable Forge surface.
- Nothing under `.forge/profiles/` is ever deleted or rewritten by a
  plugin update, a schema change, or a new stock/preset ship — see
  "Update resilience" below.

## Delta-merge rule (NORMATIVE)

A custom profile resolves against its `base` by exactly one rule: a key
PRESENT in the custom profile's domain section OVERRIDES the base's value
for that key; a key ABSENT from the custom profile INHERITS the base's
current value (including any new default a later stock update introduces
for that key). There is no removal/unset syntax in schema-version 1 — a
delta can only override or inherit, never express "delete this base key";
if a consumer needs a key gone, it overrides the key to the base's
documented off/none value instead. Any future task extending this (an
explicit unset marker) must amend this section and bump the schema
version — consumers built against v1 may rely on override-or-inherit
being the complete semantics. (Added kernel-inline at fg-b0103 INTEGRATE,
closing the verifier's delta-precision finding.)

## Active-profile pointer

The active profile is named by exactly one pointer line in a
`.forge/forge.md` `## Operator profile` section (that section's own
template and kernel gate wiring is `fg-b0104`'s boundary, not this file's
— this reference only fixes the pointer's FORMAT so `fg-b0105` and any
future picker consumer agree on it without re-deriving it):

```
## Operator profile
- active: stock:<name> | custom:<name>
```

`stock:<name>` and `custom:<name>` are the only two forms — a preset is
addressed as `stock:<preset-name>` for pointer purposes (it is Forge-shipped
and read-only exactly like the default stock profile; the `kind: preset`
distinction inside the file itself is what future domain/picker logic uses
to label it differently to a human, not the pointer). No `.forge/forge.md`
predating this section behaves as "no profile chosen yet" — same
missing-toggle-means-default convention already used for Features
(`docs/conventions.md`, "Features (forge.md)").

## Lossless switching contract

Switching the `active:` pointer between any two profile names — stock,
preset, or custom — MUST NOT read, write, mutate, or delete any profile
file. The pointer change is the entire switch. Consequences that hold by
construction, not by extra bookkeeping:

- Switching away from a custom profile and back again restores its exact
  prior behavior — the custom file was never touched, so nothing to
  restore is lost.
- Switching FROM a custom profile TO stock never deletes the custom file;
  it remains on disk, unreferenced, until the pointer names it again.
- Creating a new custom profile never overwrites an existing one under a
  different name — one file per name, `.forge/profiles/<name>.md`.

## Update resilience (warn-not-fail degrade)

WHEN a Forge plugin update ships a new stock profile, adds a preset, or
changes the profile schema, no file under `.forge/profiles/` is ever
modified or deleted by that update. If a custom profile's domain section
references a key a newer stock definition has since removed, resolution
degrades that single key to the CURRENT stock default and emits one
warning line — never a hard failure, and never a cascade that invalidates
the rest of the custom profile's deltas. This container's validator
(`tools/validate_config.py`, `validate_profile()`) enforces the
structural half of this guarantee statically (well-formed keys, known
vs. unknown domain sections as warning vs. error); the runtime degrade
itself (resolving a removed key against the CURRENT stock default at
profile-load time) is `fg-b0105`'s kernel-gate-wiring boundary, not built
here.

## Validation

`tools/validate_config.py`'s `validate_profile(path, warnings=None)`
validates one profile file:

- `## Meta` section present, with valid `schema-version` (positive
  integer), `kind` (`stock | preset | custom`), non-empty `name`, and —
  for `kind: custom` only — a non-`(none)` `base`. Missing or malformed:
  error.
- Every other top-level `## ` section is parsed as `- key: value` bullets;
  a malformed bullet line or a duplicate key within one section is an
  error (same structural rules `validate()` already applies to
  `.forge/forge.md`'s sections). A section name outside `{Autonomy,
  Providers}` is a WARNING (forward-compat), never an error.
- Domain-owned key/value SEMANTICS (which keys `## Autonomy` recognizes,
  what values are legal) are out of scope for this validator — that is
  each domain spec's own extension, exactly as `KNOWN_FEATURES` in
  `validate_config.py` only knows Features toggle NAMES, not what each
  toggle does.

`validate_config.py`'s CLI routes an explicit path whose parent directory
is `.forge/profiles/` to `validate_profile()` instead of the `.forge/forge.md`
validator (`validate()`); every other path validates as a project config
file exactly as before. This task ships no live file under
`.forge/profiles/` — that directory, and the stock profile skeleton itself,
are `fg-b0105`'s (autonomy domain) and `fg-a10902`'s (providers domain) to
populate on top of this container.

## Autonomy domain: stock profile content (fg-b0105)

NORMATIVE, content half only. This section defines the `## Autonomy`
domain's key vocabulary and the three stock profile bodies — what a
domain-aware consumer reads once it loads a profile file in the container
format above. It does not itself make the kernel loop pause, resize waves,
or pick a default: that enforcement — reading these keys at PULL/PLAN/
DISPATCH/INTEGRATE, resolving profile-default-vs-explicit-forge.md-value
precedence, and the fresh/existing install default selection — is wired by
`skills/kernel/SKILL.md` and `skills/kernel/references/forge-config-template.md`
under `fg-b0104` (concurrent, not yet landed as of this section's authoring).
Until that wiring ships, this content is inert documentation, the same
"reserved, inert until spec-4d2a ships" posture `skills/agent-factory/SKILL.md`
already uses for its own profile hook.

### `## Autonomy` key vocabulary

Every stock, preset, or custom profile's `## Autonomy` section is parsed as
`- key: value` bullets per the container's structural rule above. Three
keys are domain-defined here; a profile may omit any of them (custom
profiles inherit the omitted key from `base` per the Delta-merge rule
above; it is a validation error for a `kind: stock` profile to omit one,
since stock profiles have no `base` to inherit from).

- **`pause-points`** — a comma-separated subset of the kernel loop's own
  stage names: `plan` (the PLAN stage's plan/spec-review point),
  `dispatch` (each ROUTE+DISPATCH wave), `integrate` (each INTEGRATE
  step), or the literal `none`. Naming a stage here means the kernel stops
  at that stage and presents a structured `AskUserQuestion` confirm before
  proceeding — exactly the stages named, no more, no fewer (spec-4d2a AC,
  "WHEN the kernel reaches a dispatch batch, an INTEGRATE step, or a
  plan/spec review point the active autonomy profile marks as a pause
  point"). **Pause points named here apply across every task tier, not
  only `tier: full`** — "review all plans" means every dispatch batch can
  pause (spec-4d2a resolved clarification #4); a profile does not get a
  separate all-tiers vs. full-tier-only pause list, one `pause-points`
  value governs both.
- **`verification-panel`** — exactly one of `full` (show the complete
  verifier findings panel — every severity tier, full diff context — at
  every VERIFY step before the human is asked to confirm anything gated by
  `pause-points`), `summary` (show a condensed panel: verdict,
  severity counts, and only Critical/Important findings inline, full
  detail available on request), or `quiet` (no panel surfaced by default;
  verifier verdicts still gate INTEGRATE exactly as they do today, only
  the human-facing display is suppressed). This key changes what a human
  is SHOWN at a pause point; it never changes whether verification runs —
  a task with a failing verifier still cannot integrate under any
  `verification-panel` value.
- **`wave-size`** — exactly one of `unchanged` (no profile-imposed cap;
  the kernel's own parallel-dispatch sizing, `skills/kernel/references/
  parallel-dispatch.md`, applies exactly as it does with no profile
  active) or `capped-1` (every dispatch wave is limited to one task,
  regardless of how many parallel-safe tasks the kernel would otherwise
  batch — the human reviews one dispatch at a time).

A newer stock definition may add a fourth key in a later schema-version-1
plugin update without a format change (the Update resilience section
above); a custom profile predating that key simply inherits whatever
default the new stock ships, per the Delta-merge rule.

### Stock profile: `full-auto`

Unchanged from current kernel behavior — this is the profile an existing
install maps to, so its values are chosen to be a no-op overlay, not a new
stance.

```markdown
## Autonomy
- pause-points: none
- verification-panel: quiet
- wave-size: unchanged
```

`pause-points: none` means no profile-added pause beyond the floors that
already apply unconditionally regardless of active profile — the trust
boundary's first-touch confirm, budget caps, and the `tier: full` spec
approval gate (spec-4d2a AC, "no profile SHALL relax the trust boundary's
first-touch confirm... or skip the spec approval gate"; none of those are
`pause-points` values, they are floors this key cannot touch). `wave-size:
unchanged` is the explicit pin for spec-4d2a resolved clarification #3,
"full-auto unchanged" — dispatch sizing is exactly `parallel-dispatch.md`'s
own logic, no cap layered on top.

### Stock profile: `guided`

Full wave sizes, with its own pause points — the fresh-install default.

```markdown
## Autonomy
- pause-points: plan, integrate
- verification-panel: summary
- wave-size: unchanged
```

`wave-size: unchanged` is the explicit pin for spec-4d2a resolved
clarification #3, "guided keeps full wave sizes with its own pause
points" — `guided` differs from `full-auto` in WHEN a human is asked to
confirm (every PLAN stage's plan/spec-review point and every INTEGRATE
step), never in how large a dispatch wave is allowed to be. Per the
all-tiers key vocabulary rule above, both named pause points fire for
every task tier this profile is active for, not only `tier: full`.

### Stock profile: `high-touch`

Every dispatch wave capped at one task, every stage reviewed.

```markdown
## Autonomy
- pause-points: plan, dispatch, integrate
- verification-panel: full
- wave-size: capped-1
```

`wave-size: capped-1` is the explicit pin for spec-4d2a resolved
clarification #3, "high-touch caps waves at 1" — regardless of how many
parallel-safe tasks a wave would otherwise batch, the kernel dispatches
exactly one task per wave while `high-touch` is active. Naming `dispatch`
in `pause-points` (on top of `plan` and `integrate`) means every one of
those single-task waves still gets its own confirm before ROUTE+DISPATCH
proceeds — the cap and the pause are two independent keys that compose,
not one setting implying the other.

### Fresh-install vs. existing-install default

Per spec-4d2a resolved clarification #2: **a fresh Forge install with no
prior `.forge/` state defaults its active autonomy profile to `guided`**;
**an existing install that already has `.forge/` state predating operator
profiles defaults to `full-auto`**, mapping current (pre-profile) kernel
behavior forward unchanged rather than silently adding new pause points to
a repo a human never opted into them for. Distinguishing "fresh" from
"existing" (e.g. by whether `.forge/forge.md` already has an `##
Operator profile` section, versus first-ever `.forge/` init) and writing
the resulting `stock:guided` / `stock:full-auto` pointer into that section
is `fg-b0104`'s kernel-gate-wiring boundary — this section fixes only
which profile name each install class resolves to, not the mechanism that
detects which class a given repo is in.

### Presets

This task's acceptance criteria require exactly the three stock profiles
above; no additional Forge-shipped preset (`kind: preset`) is specified by
`fg-b0105`'s acceptance criteria or by spec-4d2a's resolved clarifications.
No preset ships from this section. (The profile PICKER surface that would
list stock/presets/custom side by side is `fg-b0106`'s own boundary,
`commands/settings.md` — out of scope here regardless.)

## Providers domain: schema (fg-c0101)

NORMATIVE, content half only — same posture as the Autonomy domain section
above. This section populates spec-4d2a's reserved `## Providers` domain
(reserved, empty, in "File shape" above) with `fg-a10902`/spec-e8a3's key
vocabulary and stock/preset content. It defines schema and data only: no
dispatch mechanics, no CLI invocation, no runtime enforcement of role
assignment or tier resolution. Those are `fg-c0106` (Phase 1 judge
dispatch), a future Phase 2 worker-dispatch task, and
`skills/kernel/references/profile-wiring.md` §5 ("Provider-review
graceful-degrade") — this section is inert documentation a domain-aware
consumer reads once it loads a profile file in the container format above,
exactly as the Autonomy section above is inert until `fg-b0104`'s wiring
consumes it.

### `## Providers` key vocabulary

Every stock, preset, or custom profile's `## Providers` section is parsed
as `- key: value` bullets per the container's structural rule above. A
profile may omit any key; a custom profile inherits an omitted key from
`base` per the Delta-merge rule; it is a validation error for `kind: stock`
to omit a key it is required to state (no `base` to inherit from) — the
stock content below states every key explicitly for that reason.

- **`enabled-providers`** — a comma-separated subset of the closed enum
  `codex | grok | antigravity` (`none` for the empty set). Naming a
  provider here is necessary but not sufficient for real dispatch: `grok`
  and `antigravity` are PILOT-GATED per `fg-c0104` (Grok non-interactive
  auth + rate-cap pilot) and `fg-c0105` (Antigravity headless smoke test)
  — both tasks are `state: done` in the queue (the pilot evidence exists),
  but per spec-e8a3's own non-goals ("Enabling Google Antigravity CLI or
  xAI Grok for real dispatch before their respective pilot-test gates...
  close... a human reviews pilot-test evidence") neither provider is
  dispatchable until a human has reviewed that evidence and cleared the
  gate — profile content naming `grok` or `antigravity` in
  `enabled-providers` is accepted and stored, never itself the thing that
  clears the gate. `codex` carries no such pilot gate (spec-e8a3 treats it
  as PRIMARY, fully-enabled-at-ship).
  **Pilot-clearance amendment — 2026-07-22:** clearance is machine-checkable:
  `.forge/.trust-providers/<provider>.pilot-cleared.local` must be present
  for `grok` or `antigravity`. The marker belongs to the same machine-local,
  never-committed, gitignore-covered family as the TOFU markers and is
  written ONLY by `/forge:settings` after the human reviews the applicable
  pilot evidence path through a structured clearance question. A settings
  edit NEVER writes the marker without that flow; an absent marker means the
  pilot gate is closed.
- **Per-role assignment keys** — `role-plan-refuter`, `role-spec-review`,
  `role-co-verifier`, `role-worker`. Each takes exactly one value:
  `claude-only` or a provider name from the `enabled-providers` enum above
  (`codex | grok | antigravity`). Naming a provider in a role key that is
  not also present in `enabled-providers` is domain-owned key/value
  semantics this container's validator does not check (see "Validation
  scope" below) — a future role-resolution consumer treats it as
  unresolvable and degrades to `claude-only`, mirroring the container's own
  warn-not-fail posture. **`role-worker` is Phase-2-gated**: spec-e8a3
  ships Phase 1 (`role-plan-refuter`, `role-spec-review`,
  `role-co-verifier` — read-only judges) at this task's time of writing;
  `role-worker` names the key now so the schema does not need a breaking
  addition later, but no dispatch path reads it until the (not yet queued)
  Phase 2 external-worker task ships — assigning it a provider today has
  no dispatch effect.
- **Provider tier-map keys** — one pair per enabled provider,
  `<provider>-tier-mechanical` and `<provider>-tier-judgment` (e.g.
  `codex-tier-mechanical`, `codex-tier-judgment`; `grok-tier-mechanical`,
  `grok-tier-judgment`; and so on for any future enabled provider). The
  schema defines the KEY only — **values are implementation-pinned
  strings, resolved at implementation time from that provider CLI's own
  live model-listing command, and this file never hardcodes a model ID**
  (spec-e8a3, "Role-based provider assignment and tier map": "exact model
  IDs pinned at implementation time from each CLI's own current
  model-listing command, never hardcoded from this spec's or any
  cutoff-bound knowledge"). A profile that enables a provider but omits
  its tier-map keys leaves tier resolution to whatever the implementing
  dispatch task (`fg-c0106` for Phase 1) resolves as that provider's
  default mechanical/judgment tiers — this section does not itself supply
  a fallback value, only the key names.
- **Trust linkage** — a provider name is only MEANINGFUL in
  `enabled-providers` or any role-assignment key once its per-provider TOFU
  confirmation exists on this machine for this repo
  (`docs/conventions/trust-and-security.md`, "Per-provider trust
  confirmation — 2026-07-19 (fg-c0103, spec-e8a3)" —
  `.forge/.trust-providers/<provider-id>.local`, confirmed once per
  provider per repo per machine). This section does not restate that
  mechanism or gate; profile content naming a provider without a matching
  trust marker is stored exactly as written (the container validator has
  no filesystem-state awareness) and resolves, at dispatch time, exactly
  as an unconfirmed provider always does — not dispatched.

### Interplay with the `providers` Feature toggle and the floor

Two independent gates sit above everything this section defines, neither
of which any `## Providers` profile content can touch:

- **The `providers` Feature toggle** (`.forge/forge.md`, OFF by default —
  `docs/conventions/config-and-features.md`, fg-c0103) gates whether ANY
  provider content in this domain is honored at all. `providers: off`
  means Forge never invokes an external provider CLI regardless of what
  any active profile's `## Providers` section names — the toggle is
  evaluated independently of, and prior to, profile resolution.
- **Profile content never overrides the toggle or the trust floors.**
  `skills/kernel/references/profile-wiring.md` §3 ("Floor enforcement")
  fixes the general shape — no profile setting relaxes a floor the human
  or the trust boundary set; §5 ("Provider-review graceful-degrade") fixes
  the specific provider case: when `providers` is off or the named
  provider's trust marker is absent, a role assignment naming that
  provider degrades to a human-only gate with one stated note, never a
  silent skip and never a block waiting for the provider to appear. This
  section's key vocabulary supplies the DATA those two mechanisms read;
  it implements neither.

### Stock Providers content

Stock = `claude-only` everywhere, matching the `providers` Feature's OFF
default — the same "no-op overlay, not a new stance" posture the Autonomy
stock profile (`full-auto`) uses above.

```markdown
## Providers
- enabled-providers: none
- role-plan-refuter: claude-only
- role-spec-review: claude-only
- role-co-verifier: claude-only
- role-worker: claude-only
```

No tier-map key is stated in stock: with `enabled-providers: none`, no
provider-specific tier-map pair applies (tier-map keys are only meaningful
once their provider is enabled). A custom profile that later enables a
provider adds that provider's own tier-map keys itself.

### Presets

Spec-e8a3's minimum three, per its "Overlay-profile model" AC ("Forge-
shipped presets (at minimum: Claude-only, Cross-check second-judging,
Budget tiers)"). Each is `kind: preset`, ships read-only in the plugin
exactly like a stock profile, and states only its `## Providers` content
here — registering each preset into the shared picker is `fg-c0109`'s own
boundary, not built by this task.

**`claude-only`** — every role stays Claude-native; the explicit,
selectable form of the stock default, for a human who wants to name the
choice rather than rely on the absence of a profile.

```markdown
## Providers
- enabled-providers: none
- role-plan-refuter: claude-only
- role-spec-review: claude-only
- role-co-verifier: claude-only
- role-worker: claude-only
```

**`cross-check-second-judging`** — enables Codex as an advisory second
opinion on plan-refuter and full-tier co-verifier (composing with Claude's
own `forge-verifier` under the existing panel ceiling, never replacing
it), while spec-review and all worker dispatch stay Claude-only.

```markdown
## Providers
- enabled-providers: codex
- role-plan-refuter: codex
- role-spec-review: claude-only
- role-co-verifier: codex
- role-worker: claude-only
- codex-tier-judgment: (implementation-pinned at fg-c0106)
```

Both `role-plan-refuter` and `role-co-verifier` are named in spec-e8a3's
equal-or-higher rule ("a provider-assigned judge for a JUDGMENT-tier or
`tier: full` role resolves to that provider's frontier/highest tier" —
spec-e8a3, "Role-based provider assignment and tier map"), so this preset
states only `codex-tier-judgment`, never a mechanical-tier key for either
role.

**`budget-tiers`** — routes the spec-review advisory pass to Codex's
mechanical tier for a cost-conscious cross-check, keeping plan-refuter,
co-verifier, and all worker dispatch Claude-only.

```markdown
## Providers
- enabled-providers: codex
- role-plan-refuter: claude-only
- role-spec-review: codex
- role-co-verifier: claude-only
- role-worker: claude-only
- codex-tier-mechanical: (implementation-pinned at fg-c0106)
```

Interpretation flag (unverified, stated here rather than silently assumed):
spec-e8a3's equal-or-higher AC names only "a cross-model co-verifier or
second opinion" (i.e. `role-co-verifier` and `role-plan-refuter`) as
required to resolve to frontier tier for a JUDGMENT-tier or `tier: full`
role; `role-spec-review` is not named in that clause. This preset reads
that omission as deliberate — spec-review is a read-only advisory pass
feeding the human spec-approval gate, which remains the authoritative,
un-skippable floor (`profile-wiring.md` §3, "the `tier: full` spec
approval gate never becomes skippable") regardless of what tier judged it
— and assigns it Codex's mechanical tier accordingly. A future task
implementing `fg-c0106` should confirm this reading against spec-e8a3
before wiring `role-spec-review`'s tier resolution; if that confirmation
finds spec-review is in fact covered by the equal-or-higher floor, this
preset's `codex-tier-mechanical` line is the one to change, not the floor.

### Validation scope (no change to `validate_config.py`)

`Providers` is already in `KNOWN_PROFILE_DOMAINS`
(`tools/validate_config.py`), so `validate_profile()` already parses this
domain's `- key: value` bullets structurally (well-formed lines, no
duplicate keys) without error. This task does not add key-level semantic
checks (closed-enum enforcement on `enabled-providers`/role values, tier-
map key-pairing, trust-marker cross-referencing) to `validate_config.py`.
The container's own validation contract states domain key/value semantics
are explicitly OUT OF SCOPE for `validate_profile()` by design ("Domain-
owned key/value SEMANTICS... are out of scope for this validator — that is
each domain spec's own extension, exactly as `KNOWN_FEATURES`... only
knows Features toggle NAMES, not what each toggle does" — "Validation"
section above), matching how the Autonomy domain's own three keys
(`pause-points`, `verification-panel`, `wave-size`) carry no key-level
validator code either. If a future task wants closed-enum/semantic
validation for Providers keys specifically, it is a new, separately-scoped
extension to `validate_profile()` — no such task exists in the queue as of
this writing (checked: no `fg-c0110`/`fg-c0111` task file present).
