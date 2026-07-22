# Operator profile — kernel gate wiring (reference)

NORMATIVE. Loaded once at SYNC (`skills/kernel/SKILL.md`'s "Operator
profile resolution" stub) and applies for the rest of the session — DISPATCH,
INTEGRATE, and the plan/spec-review points below all consult what this
section resolved without re-reading it. This file wires the shared profile
CONTAINER (`skills/kernel/references/operator-profiles.md`, `fg-b0103`) and
the autonomy DOMAIN content it holds (`fg-b0105`, stock profiles
`full-auto`/`guided`/`high-touch`) into the actual kernel loop steps. It
defines no new profile content of its own — only how the kernel resolves
and enforces whatever the active profile says.

## 1. Resolving the active profile

Read the active-profile pointer from `.forge/forge.md`'s `## Operator
profile` section (`active: stock:<name> | custom:<name>`,
`operator-profiles.md`, "Active-profile pointer").

**Missing-section default mapping.** WHEN no `## Operator profile` section
exists in `.forge/forge.md`, the active profile is the default stock
autonomy profile: **`guided` for a fresh install (a repo with no prior
Forge state), `full-auto` for an existing install (mapping its current
behavior forward unchanged)**. Render it `(default — not yet in
forge.md)` — the same missing-toggle-means-default convention
`docs/conventions.md`'s "Features (forge.md)" already uses. "Fresh" vs
"existing" is decided the same way SYNC already decides it: a `.forge/`
this session's auto-init step just created (it wrote `.provenance`) is
fresh; any `.forge/` that predates this section is existing.

## 2. Precedence engine

Every setting a profile can touch (approval-gate pause points,
verification-panel settings, wave-size) resolves by exactly one order,
lowest to highest:

| Order | Source | Wins when |
|---|---|---|
| 1 (lowest) | Active profile's preset default | Nothing else sets this key |
| 2 | Explicit `.forge/forge.md` value (Features / Budgets / Queue) | The key is set there, overriding the profile's default for that same setting |
| 3 (highest — FLOOR) | Trust boundary, budget caps, `tier: full` spec approval gate | Always — no profile or forge.md value overrides it |

**Pin — precedence order:** *profile default < explicit forge.md value <
FLOOR.* An explicit value already set elsewhere in `.forge/forge.md`
(Features/Budgets/Queue) takes precedence over the active profile's
default for that same setting; the FLOOR (below) always wins over both.

## 3. Floor enforcement (never relaxed)

**Pin — floor-enforcement:** *no profile SHALL relax the trust boundary's
first-touch confirm, raise `max-tasks-per-session` / `session-token-cap`
beyond what the human set, or skip the spec approval gate.* Concretely,
regardless of what any stock, preset, or custom profile's preset would
otherwise set:

- **Trust boundary first-touch confirm** (`skills/kernel/references/
  trust-gate.md`) always fires on an untrusted `.forge/` — no profile
  preset can mark it non-pausing, auto-confirm it, or skip straight to
  PULL.
- **Budget caps are human-set, never profile-raised.** A profile preset
  MUST NOT raise `max-tasks-per-session` or `session-token-cap` above the
  value the human wrote into `.forge/forge.md`'s `## Budgets` section (or
  the config template's default if unset). A profile MAY only ever
  tighten a budget default, never loosen one the human already set.
- **The `tier: full` spec approval gate never becomes skippable.** GATE's
  full-tier precondition (`skills/kernel/SKILL.md`, step 4) and
  `skills/spec/SKILL.md`'s "5. Approval gate (the one human gate)" remain
  in force unconditionally — no profile setting, including `full-auto`,
  removes or auto-answers this gate.

WHEN an autonomy profile's preset would set a value conflicting with any
of the three floors above, the kernel enforces the floor and ignores only
the conflicting portion of the preset — the rest of that profile's preset
still applies normally.

## 4. Pause-point enforcement (all tiers)

**Pin — pause-points-all-tiers:** *pause-point gating applies to ALL
tiers, not only `tier: full`'s existing plan/ship-review steps —
"review all plans" means every dispatch batch can pause.*

The active profile names zero or more of these three kernel points as
pause points. WHEN the kernel reaches a point the active profile marks:

- **Dispatch batch** — `skills/kernel/SKILL.md` step 5 (ROUTE + DISPATCH),
  immediately before dispatching a batch (sequential single-task dispatch
  or a parallel-eligible batch alike).
- **INTEGRATE** — `skills/kernel/SKILL.md` step 7, immediately before a
  PASS is committed and `state: done` is written.
- **Plan/spec review** — `skills/kernel/SKILL.md` step 3 (PLAN), after a
  task's Execution plan is written and before GATE/DISPATCH acts on it;
  and, where the active profile marks it, before `skills/spec/SKILL.md`'s
  own approval gate presents its `AskUserQuestion` card (see `skills/spec/
  SKILL.md`, "5. Approval gate (the one human gate)" — that gate is
  ALWAYS a human gate regardless of profile per the floor above; a
  profile marking this point adds nothing there beyond what's already
  mandatory, but MAY additionally mark the kernel's own PLAN step as
  pausing).

At any marked point, the kernel STOPS and presents a structured
`AskUserQuestion` confirm before proceeding — exactly the pause points
that profile names, no more, no fewer. This applies at every tier
(trivial/standard/full), not only `tier: full`'s pre-existing plan/
ship-review steps. A point the active profile does NOT mark is not
paused by this mechanism (though the floor's own unconditional gates —
trust boundary, spec approval — still apply independently).

## 5. Provider-review graceful-degrade

WHEN an autonomy profile's preset sets a role's review to
`provider-review: advisory | verdict` (the composition point with
`fg-a10902`'s future providers domain), treat that as OPTIONAL input to
the gate:

**Pin — graceful-degrade:** *when no provider is enabled or available
(`fg-a10902` not yet shipped, or the specific provider not opted in for
this repo — `.forge/forge.md` Features `providers: off`, or the specific
provider's per-provider trust marker absent), the gate degrades to a
human-only gate with one stated note — never silently skip the gate and
never block on a provider that isn't there.*

Concretely: run the gate exactly as it would run with no `provider-
review` setting at all (human-only), and add exactly one line to the
gate's presentation naming which provider was configured and why it
didn't participate (e.g. "provider-review: verdict configured for this
role, but `providers` is off — gate ran human-only"). Never treat a
missing/unavailable provider as a reason to skip the gate entirely, and
never treat it as a reason to block progress waiting for the provider to
become available.

## 6. Non-goals of this file

No stock/preset profile CONTENT (names, per-profile pause-point lists,
verification-panel settings, wave-size values) lives here — that is
`skills/kernel/references/operator-profiles.md`'s `## Autonomy` domain
section, `fg-b0105`'s boundary. This file wires whatever that content
says into the loop; it never defines what that content is.
