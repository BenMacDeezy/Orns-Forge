# Settings schema registry (reference)

NORMATIVE. The ONE canonical place a `.forge/forge.md` setting is defined
(`docs/conventions/config-and-features.md`, "Settings schema registry —
one canonical place — 2026-07-21", settings-system-depth). `/forge:settings`
(`commands/settings.md`), `tools/validate_config.py`, and the doc tree's
own Features/Budgets/Providers tables all read this registry rather than
each keeping a separate copy — a new setting is added HERE first, then
wired into the validator and cited from `commands/settings.md`'s view; it
is never added to any of those three surfaces without first landing here.

This file registers **flat settings only** — every `- key: value` bullet a
forge.md section can carry. The `## Operator profile` section's `active:`
pointer is deliberately OUT of this registry: it names a profile file, not
a scalar value, and its own picker/precedence/floor rules live in
`skills/kernel/references/profile-wiring.md` and `operator-profiles.md` —
restating it here would fork that contract, not extend it.

**Columns.** Section — the forge.md `## ` heading the key lives under.
Key — the exact `- key:` name. Type — `on/off`, `int`, `"none"|int`, or
`string`. Default — the value a MISSING key resolves to (never blank; see
each section's own missing-key convention below, one of which inverts the
norm). Allowed values — the closed set or shape a write must satisfy.
Meaning — one line. Floor — one of the four floor names below, or `—` if
this key carries no floor.

**The four floor names** (`docs/conventions/config-and-features.md`,
"Settings schema registry", "Floor-protected settings"; full rules there,
cited by name only in the table below):

- `trust-confirmation` — a settings edit never clears or forges a
  `.forge/.trust-providers/*.local` or `.forge/.trust-local` marker.
- `human-set-cap` — a budget key may only ever be raised or lowered BY a
  human through this same surface, never silently raised past what a
  human set as a side effect of any other edit.
- `spec-approval-gate` — no key exists, or will be added, that skips the
  `tier: full` spec approval gate.
- `providers-default-off` — no edit path changes what a repo that has
  never touched provider config gets: zero external dispatch.

## Features

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `natural-language-invocation` | on/off | on | on, off | Forge skills fire from plain conversation, not only explicit `/forge:*` commands. | — |
| `continuous-loop` | on/off | on | on, off | Completing a wave re-checks the queue once for newly-ready tasks and continues; off = one wave per invocation. | — |
| `auto-queue-capture` | on/off | on | on, off | Task-shaped ideas in conversation are offered for capture into the queue. | — |
| `express-lane` | on/off | on | on, off | Standard-tier ideas skip the spec pipeline via one structured confirm; never applies to `tier: full`. | `spec-approval-gate` (cannot be set to bypass full-tier's own gate) |
| `workflow-executor` | on/off | on | on, off | Parallel-eligible waves and full-tier ship reviews run as deterministic Workflow scripts when the harness offers the Workflow tool. | — |
| `providers` | on/off | **off** | on, off | External providers (second opinions, cross-model review, worker dispatch) may be enabled for this repo at all. | `providers-default-off` |

Missing-key convention: every Features key above resolves to its listed
Default when absent from forge.md (`docs/conventions/config-and-
features.md`, "Features (forge.md)").

## Budgets

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `max-tasks-per-session` | `"none"\|int` | none | "none" or a positive integer | PRIMARY enforced cap: the kernel counts dispatches per session and stops with a session report when reached. | `human-set-cap` |
| `session-token-cap` | `"none"\|int` | none | "none" or a positive integer | Advisory only — not the enforcement mechanism. With `continuous-loop: off` the model may stop early on its own spend estimate; with `continuous-loop: on` a spend estimate (or elapsed time / session length) is NEVER a reason to voluntarily pause the drain — only a hard cap stops it. | `human-set-cap` |
| `max-provider-dispatches-per-session` | `"none"\|int` | none (checkpoint model, owner-ratified 2026-07-22; was 10) | "none" or a positive integer | Counts external-provider dispatches only, checked at ROUTE time; never folded into `session-token-cap`. | `human-set-cap` |
| `provider-dispatch-checkpoint-every` | int | 10 | positive integer | Spend-checkpoint cadence across ALL providers combined (per-provider counts in the checkpoint line): at each multiple, post a one-line tally checkpoint and continue unless the human objects (`docs/conventions.md`, "Provider dispatch checkpoints — 2026-07-22"). Only meaningful alongside `max-provider-dispatches-per-session: none`; a numeric cap keeps hard-cap semantics. | no |

Missing-key convention: every Budgets key above resolves to its listed
Default when absent from forge.md.

## Providers

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `codex` | on/off | **off** | on, off | Per-provider dispatch toggle, layered under the global `providers` Feature. All four gate layers must hold (`provider-judges.md` §1a). | `providers-default-off`, `trust-confirmation` (toggling off never clears TOFU) |
| `grok` | on/off | **off** | on, off | Same toggle shape as `codex`. Pilot-gated (`bm-grok-pilot-test`) — never dispatchable regardless of this toggle until a human clears the pilot gate. | `providers-default-off`, `trust-confirmation` |
| `antigravity` | on/off | **off** | on, off | Same toggle shape as `codex`. Pilot-gated (`bm-antigravity-smoke-test`) — never dispatchable regardless of this toggle until a human clears the pilot gate. | `providers-default-off`, `trust-confirmation` |
| `codex-default-model` | string | `gpt-5.6-sol` | owner-allowed set (2026-07-22, verified against the live models_cache catalog): `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5` | Recorded per-provider default model slug — the last-resort fallback in the model/effort resolution order (`docs/conventions/telemetry-and-labels.md`, "Provider dispatch labels — 2026-07-22"; `provider-judges.md` §2). Owner-set 2026-07-22. | — |
| `codex-default-effort` | string | `medium` | low, medium, high, xhigh | Recorded per-provider default reasoning effort — same resolution-order fallback as `codex-default-model`. Owner-set 2026-07-22. | — |

**Provider default keys carry no floor (floor-flag: no).** Unlike the
on/off toggles above, `codex-default-model` and `codex-default-effort`
are not gated by `providers-default-off` or `trust-confirmation` — they
are pure fallback values the orchestrator MAY override per dispatch via
a task's routing override or the class-based routing vocabulary
(`telemetry-and-labels.md`, "Provider dispatch labels — 2026-07-22",
"Resolution order"), never a value a settings edit alone forges trust
or dispatch permission from.

**Missing-key convention — the exception.** Every OTHER section in this
registry resolves a missing key to its listed Default, and most of those
defaults are the "on"/enabled posture. `## Providers` inverts that norm on
purpose: a provider id absent from forge.md, or the whole `## Providers`
section absent, resolves to **OFF** — stated explicitly here because it is
the one surface in this registry where missing-key-means-default does NOT
mean missing-key-means-on. It mirrors the `providers` Feature's own
default-off row above, not a new invention
(`docs/conventions/config-and-features.md`, "Per-provider dispatch
toggles").

## Queue

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `claim-staleness-hours` | number | 0.5 (repo may set its own; template default 2) | positive number | Hours after which a stale task claim is eligible for recovery. | — |
| `max-parallel-tasks` | int | 3 | positive integer | Caps the size of one parallel-dispatch wave batch. | — |

Missing-key convention: `## Queue` itself is OPTIONAL; a missing section,
or a key the section omits, resolves to the Default above.

## Gates

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `build` | string | (auto-detect) | any non-empty shell command, "(auto-detect)", or a "none (...)" explanation | Build command the kernel runs at the gate step. | — |
| `test` | string | (auto-detect) | same shape as `build` | Test command. | — |
| `lint` | string | (auto-detect) | same shape as `build` | Lint command. | — |

Missing-key convention: `## Gates` is the only REQUIRED section
(`tools/validate_config.py`) — all three keys must be present and
non-empty, or the kernel re-infers and writes them back
(`docs/conventions.md`, "Malformed forge.md").

## Routing overrides

| Key | Type | Default | Allowed values | Meaning | Floor |
|---|---|---|---|---|---|
| `<area or path pattern>` | string | (none) | `<model>/<effort> — <reason>`, model in {haiku, sonnet, opus, fable}, effort in {low, medium, high}; OR the provider-qualified form `<provider>/<slug>/<effort>` (e.g. `codex/gpt-5.6-sol/high`, provider from the `## Providers` section, slug verbatim as passed to `-m`, effort from that provider's own vocabulary) | Per-area routing override; a `fable/<effort>` line is itself the human authorization required to use fable for that area. A provider-qualified line is resolution-order step 1 for provider dispatches (`docs/conventions.md`, "Provider dispatch labels — 2026-07-22") — without this form a routing override could not express a provider model at all (cross-model verify catch, 2026-07-22). | — |

Missing-key convention: `## Routing overrides` is a free-form list, not a
fixed key set — `(none)` (no overrides) is the template default; an
absent line for a given area simply means no override applies to it.

## Operator profile (pointer — outside this registry's flat-key scope)

Named here only so a reader scanning this file for "every forge.md
setting" isn't left wondering where it went: the `## Operator profile`
section's `active: stock:<name> | custom:<name>` pointer is a single
non-flat value governed by its own container/precedence/floor contract
(`skills/kernel/references/profile-wiring.md`, `operator-profiles.md`) —
`/forge:settings` renders it (step 1's first bullet, `commands/
settings.md`) but this registry does not re-describe its shape.

## Adding a new setting

1. Add one row to the appropriate section table above (or a new section
   heading, following the same column shape) — this is the ONE place the
   key is defined.
2. Wire it into `tools/validate_config.py`'s per-section parsing (type/
   allowed-values check, forward-compat WARNING for an unrecognized name
   within a known section — never a hard error for a name this validator
   doesn't yet know).
3. Cite it from `commands/settings.md`'s no-args view (which renders every
   registry row) — never re-describe its meaning there beyond a
   one-line summary matching this table's Meaning column.
4. If it is a Features/Budgets/Providers key, add or amend the matching
   table in `docs/conventions/config-and-features.md` so the doc and the
   registry state the same default/meaning — a mismatch between the two is
   a drift bug against this file's own purpose.
