---
description: View and edit Forge settings (forge.md Features, Budgets, Queue)
argument-hint: "[natural-language edit, e.g. \"turn off auto loops\"]"
---

Read `.forge/forge.md` at the repo root (resolve root first — `forge:queue`,
Auto-init). If `.forge/` or forge.md is missing, say so in one line and offer
to auto-init (queue skill) before continuing.

**Canonical schema source.** Every setting this command renders, validates,
or writes is drawn from `skills/kernel/references/settings-schema.md`
(NORMATIVE, ONE canonical registry — `docs/conventions/config-and-
features.md`, "Settings schema registry"). This step's per-section bullets
below are that registry rendered, not a second definition of it — a
setting added to the registry appears here automatically; this file is
never edited to add a setting's meaning independently of that registry.

1. **Render current settings.** No-args invocation shows EVERY setting the
   schema registry knows, grouped by section exactly as the registry orders
   them (Features / Budgets / Providers / Queue / Gates / Routing
   overrides, plus the Operator profile pointer first) — each with its
   current value, its schema-registry default, and its one-line meaning.
   A setting absent from disk is shown AT its registry default, labeled
   `(default — not yet in forge.md)`, same treatment for every section, not
   only Features:
   - **Operator profile** — the `active:` pointer (`stock:<name>` or
     `custom:<name>`). **Missing `## Operator profile` section:** treat the
     active profile as the default stock autonomy profile — `stock:guided`
     for a fresh install, `stock:full-auto` for an existing install — and
     render it `(default — not yet in forge.md)`, same convention as a
     missing Features toggle below (`skills/kernel/references/
     profile-wiring.md`, "Missing-section default mapping"). Picking a
     different profile, listing stock/preset/custom side by side, and the
     create-custom-profile flow are the profile picker, step 2 below.
   - **Features** — every toggle (`natural-language-invocation`,
     `continuous-loop`, `auto-queue-capture`, `express-lane`,
     `workflow-executor`, `providers`) with `on`/`off` and its one-line
     meaning (`settings-schema.md`, "Features"). `providers` defaults `off`
     — call this out explicitly when rendering it, since every other
     toggle defaults `on`.
   - **Budgets** — `max-tasks-per-session`, `session-token-cap` (note which is
     the enforced primary cap vs advisory), `max-provider-dispatches-per-session`
     (default `none` — external-provider dispatches only, checked at ROUTE
     time, never folded into `session-token-cap`) and
     `provider-dispatch-checkpoint-every` (default `10`). The shipped checkpoint model keeps a
     running tally, posts the one-line per-provider-count/exact-slug checkpoint
     at each multiple, and continues unless the human objects; setting a
     NUMERIC cap retains the original hard-cap semantics.
   - **Providers** — one row per provider the schema registry names
     (`codex`, `grok`, `antigravity`), each showing THREE fields together,
     never split across separate views: its forge.md `## Providers` toggle
     (`on`/`off`, default `off`), whether its TOFU trust marker
     (`.forge/.trust-providers/<provider-id>.local`) is present, and its
     pilot-gate status (`codex`: "no pilot gate"; `grok`/`antigravity`:
     show "cleared" only when
     `.forge/.trust-providers/<provider>.pilot-cleared.local` is present, otherwise "pilot-gated, clearance marker
     absent" and name `bm-grok-pilot-test` / `bm-antigravity-smoke-test` —
     stated regardless of the toggle's own value, since the pilot gate is
     never overridden by it). **Missing toggle or missing `## Providers`
     section:** unlike every
     other section in this view, a missing toggle here resolves to `off`,
     NOT to a documented "default" line that happens to read `off` for
     other reasons — this is the one exception to the missing-setting-
     means-default-on norm every other section follows, and the render
     states that inversion explicitly next to the section heading, not only
     in a footnote (`settings-schema.md`, "Providers", "Missing-key
     convention — the exception"). Also rendered alongside each provider's
     row: its recorded default model/effort fallback (`codex-default-model`
     / `codex-default-effort`, `settings-schema.md`, "Providers") used only
     when the model/effort resolution order's routing-override and
     class-vocabulary steps resolve nothing (`docs/conventions/
     telemetry-and-labels.md`, "Provider dispatch labels — 2026-07-22").
     Offering to toggle a provider, or to run its trust confirmation,
     routes through step 5 below — this row is read-only display.
   - **Queue** — `claim-staleness-hours`, `max-parallel-tasks`.
   - **Gates** — `build`, `test`, `lint` (required; a missing or malformed
     `## Gates` section re-infers and writes back, `docs/conventions.md`,
     "Malformed forge.md" — never shown as merely "default", since Gates
     has no registry default other than `(auto-detect)` itself).
   - **Routing overrides** — the free-form override list, `(none)` when
     empty.
   **Missing `## Features` section:** an existing forge.md written before the
   Features section existed has no toggles on disk — treat every toggle as its
   default (the config template's values — `on` for every toggle except
   `providers`, which defaults `off`), render them marked `(default — not yet
   in forge.md)`, and offer to write the section in.

2. **Profile picker.** Entered when the human asks to switch, pick, or
   customize the operator profile (explicit `/forge:settings` argument, a
   natural-language ask like "switch to high-touch", or the "Change operator
   profile" option offered alongside step 3's edit question below). Rides the
   shared container `skills/kernel/references/operator-profiles.md` defines
   (`spec-4d2a`) — this step never defines a second file format, storage
   location, or pointer scheme of its own.

   a. **List side by side.** Render one listing, grouped by domain and then by
      kind within each domain — never as separate screens or separate prompts
      per kind:
      - **`## Autonomy`** (the only domain shipping content today,
        `fg-b0105`):
        - *Stock* — `full-auto`, `guided`, `high-touch`
          (`operator-profiles.md`, "Stock profile: ..." bodies), each shown
          with a one-line summary of its `pause-points` /
          `verification-panel` / `wave-size`.
        - *Presets* — Forge-shipped `kind: preset` profiles beyond stock.
          None ship for Autonomy yet (`operator-profiles.md`, "Presets") —
          show the group heading with "(none yet)" rather than omitting it,
          so the group itself is always visible.
        - *Custom* — every `.forge/profiles/<name>.md` file whose `## Meta`
          parses `kind: custom`, shown with its `base` and a one-line delta
          summary (which Autonomy keys it overrides vs. inherits).
      - **`## Providers`** (`fg-c0109`, populated by `fg-c0101`/spec-e8a3 —
        registered into this SAME listing per the extensibility guarantee
        below, not a second listing mechanism):
        - *Stock* — `claude-only` everywhere (`operator-profiles.md`,
          "Stock Providers content"), shown with a one-line summary ("all
          roles Claude-native — no-op overlay, matching `providers` Feature's
          OFF default").
        - *Presets* — the three Forge-shipped `kind: preset` profiles
          (`operator-profiles.md`, "Presets" — minimum three per spec-e8a3's
          "Overlay-profile model" AC):
          - `claude-only` — every role stays Claude-native; the explicit,
            selectable form of the stock default.
          - `cross-check-second-judging` — Codex as an advisory second
            opinion on plan-refuter and full-tier co-verifier, composing
            with Claude's own `forge-verifier`; spec-review and all worker
            dispatch stay Claude-only.
          - `budget-tiers` — routes the spec-review advisory pass to Codex's
            mechanical tier for a cost-conscious cross-check; plan-refuter,
            co-verifier, and all worker dispatch stay Claude-only.
        - *Custom* — every `.forge/profiles/<name>.md` file whose `## Meta`
          parses `kind: custom` and which carries a `## Providers` section,
          shown with its `base` and a one-line delta summary (which
          Providers keys it overrides vs. inherits, per
          `operator-profiles.md`'s "`## Providers` key vocabulary").
      - Mark whichever entry the `active:` pointer names as current.

      **Pin — side-by-side listing:** the picker lists stock, Forge-shipped
      presets, and the human's own custom profiles together in ONE listing,
      grouped by kind, never as three separate screens or prompts.

      **Pin — extensibility guarantee:** this listing, the switch in (c), and
      the create-custom flow in (d) are all written generically over "the
      active container's domain sections" — keyed off whatever `## `
      headings a profile file actually has — never hardcoded to `##
      Autonomy`. The `## Providers` domain (`fg-a10902`) registers by
      shipping its own stock/preset/custom content under a `## Providers`
      heading; it adds a second domain group to step (a)'s SAME listing and
      composes with the SAME switch and create-custom logic below, with no
      rewrite of this step. `fg-c0109` (immediately above) is that
      registration.

      **Pin — no second picker for Providers.** The `## Providers` domain
      group above renders inside this SAME `AskUserQuestion` listing per the
      extensibility guarantee — `fg-c0109` builds no Providers-specific
      picker variant, screen, or command. Selecting a Providers stock,
      preset, or custom entry is the identical one-pointer-line switch (c)
      below already defines: `active: stock:<name>` for stock or preset,
      `active: custom:<name>` for custom — Providers profiles are addressed
      by the pointer exactly like Autonomy profiles, never a second pointer
      scheme.

      **Pin — the picker never blocks a pilot-gated selection.** A preset
      naming only `codex` in `enabled-providers` (all three minimum presets
      above) is fully selectable in the listing. The listing itself also
      never blocks selection of a profile that names `grok` or `antigravity`
      in `enabled-providers` or a `role-*` key — per `operator-profiles.md`'s
      "`enabled-providers`" section, naming a pilot-gated provider there is
      "accepted and stored, never itself the thing that clears the gate";
      enforcement is the pilot gate (`fg-c0104`/`fg-c0105` evidence review)
      and the trust/toggle floors at dispatch time (`operator-profiles.md`,
      "Interplay with the `providers` Feature toggle and the floor"), never
      a picker-level selection block. (FORM mode's own field-level disabled-
      option surfacing, step 2(d-form) below, is separate and unaffected —
      this pin covers the top-level listing in step 2(a) only.)

   b. **Select.** Present the listing as one `AskUserQuestion` call: one
      option per listed profile across every group (current marked), plus a
      "Customize <name>" option per profile per (d) below. Per
      `docs/conventions.md` ("Asking the user questions"), this is a single
      structured question, not a chain of separate prompts.

   c. **Switch.** On selecting an existing stock, preset, or custom profile,
      write EXACTLY the one pointer line in `.forge/forge.md`'s
      `## Operator profile` section — `active: stock:<name>` (stock and
      preset both address as `stock:<name>` per the pointer format,
      `operator-profiles.md` "Active-profile pointer") or `active:
      custom:<name>` — and touch nothing else in the file. No profile file
      under `.forge/profiles/` or in the plugin's stock/preset tree is read,
      written, or deleted by a switch.

      **Pin — one-pointer-line-only switch:** switching the active profile
      writes exactly the one `active:` pointer line and nothing else — no
      profile file is read, mutated, or deleted, which is what makes
      switching back to a previously-used custom profile restore its exact
      prior behavior (lossless in both directions, `operator-profiles.md`
      "Lossless switching contract").

   d. **Create-custom (choosing "Customize `<source>`").** `<source>` is
      whichever stock, preset, or custom profile the human picked to
      customize.
      - **Choose authoring mode.** One structured `AskUserQuestion`:
        **FORM mode** (field-by-field wizard — continue with this step's
        Delta capture below) or **VIBE mode** (örn-guided conversational
        interview — step **2(d-vibe)** below). Both modes converge on the
        identical Copy-on-write + Validate-before-finishing + Activate
        shape this step defines; only how the deltas are captured differs,
        and the resulting file is indistinguishable regardless of which
        mode wrote it. Editing an existing custom profile offers the same
        mode choice regardless of which mode originally created it
        (spec-e8a3, "Dual authoring UX" — mode-symmetric editing).
      - **Copy-on-write.** Create a new file `.forge/profiles/<new-name>.md`
        (ask the new name if not implied) with `## Meta` set to `kind:
        custom`, `name: <new-name>`, `base: <source>`, and a domain section
        per source domain containing only the keys the human changes — the
        source file itself (stock/preset in the plugin tree, or an existing
        custom file) is never opened for writing.

        **Pin — copy-on-write custom-creation:** customizing a stock or
        preset (or an existing custom profile) always creates a NEW named
        `.forge/profiles/<name>.md` file capturing only the deltas over its
        `base`; the source profile is never modified in place
        (`operator-profiles.md`, "Storage and immutability").
      - **Delta capture.** One `AskUserQuestion` card per Autonomy key the
        human wants to change (`pause-points`, `verification-panel`,
        `wave-size` — the closed vocabulary `operator-profiles.md`'s
        "`## Autonomy` key vocabulary" section defines), each preselected to
        `<source>`'s current resolved value for that key. A key the human
        leaves untouched is simply omitted from the new file's domain
        section — per the delta-merge rule it then inherits `base`'s value,
        including any later stock update to that key
        (`operator-profiles.md`, "Delta-merge rule"). When capturing a `##
        Providers` domain delta, the human first picks an authoring mode via
        one structured question — VIBE (örn-guided interview) or FORM
        (structured `AskUserQuestion` wizard, 2(d-form) below) — either mode
        may edit a profile the other created, both writing the identical
        schema-versioned format.
      - **Validate before finishing.** Run `tools/validate_config.py`'s
        `validate_profile()` against the new file before treating the flow
        as complete.

        **Pin — validator-before-finish:** the create-custom flow always
        runs `validate_profile()` on the new `.forge/profiles/<name>.md`
        before finishing; a validation failure is surfaced to the human (the
        specific error) and the flow does not report success or switch the
        active pointer to the new profile until it passes.
      - **Activate.** On a passing validation, offer (one more structured
        question) to switch `active:` to the new `custom:<new-name>` now,
        via the same (c) above — creating a custom profile never
        auto-activates it.

   **2(d-vibe). VIBE mode — örn-guided conversational authoring.** Entered
   from the "Choose authoring mode" bullet above (or directly, by picking
   VIBE, when editing an existing profile). örn runs a conversational
   interview instead of one `AskUserQuestion` card per key; this step
   covers ONLY how the interview proposes and captures values — it hands
   off to (d)'s own Copy-on-write target file and its unchanged Validate-
   before-finishing / Activate bullets above to finish.

   - **Normative sentence (downstream-indistinguishable).** VIBE mode
     writes the identical schema-versioned `## Providers` / `## Autonomy`
     profile format FORM mode writes — the picker (step 2a), kernel role/
     pause-point resolution (`skills/kernel/references/profile-
     wiring.md`), and `validate_profile()` see no difference between a
     profile VIBE mode produced and one FORM mode produced; nothing in the
     resulting file records which mode authored it.
   - **Interview shape.** örn asks in plain language, iterating until the
     human is satisfied, across three loose conversational beats (not
     rigid question cards — this is VIBE mode's alternative to FORM mode's
     cards):
     1. *Setup* — which domain(s) the human wants to touch (Autonomy
        pacing, Providers assignment, or both) and which existing profile
        is `<source>`, if not already fixed by step 2's picker.
     2. *Provider/role intent* — plain-language asks ("I want Codex to
        double-check my verifier", "keep spec review Claude-only") that
        örn translates into concrete key values.
     3. *Cost posture* — a plain-language budget stance ("keep this
        cheap", "I don't mind the frontier tier for judging") that maps to
        which tier-map key (mechanical vs. judgment) applies to an enabled
        provider's roles.
   - **Closed-vocabulary discipline (normative).** örn proposes values and
     the human steers, but every proposal is drawn from the closed enums
     `operator-profiles.md` already defines — örn never invents a key or a
     value outside them:
     - Autonomy: `pause-points` (subset of `plan, dispatch, integrate,
       none`), `verification-panel` (`full | summary | quiet`),
       `wave-size` (`unchanged | capped-1`) — `operator-profiles.md`,
       "`## Autonomy` key vocabulary".
     - Providers: `enabled-providers` (subset of `codex | grok |
       antigravity`, or `none`), the four `role-*` keys (`claude-only` or
       an enabled provider name), and the per-provider
       `<provider>-tier-mechanical` / `<provider>-tier-judgment` key pair
       — `operator-profiles.md`, "`## Providers` key vocabulary". Tier-map
       VALUES are never proposed by örn (they are implementation-pinned
       strings resolved elsewhere, per that same section) — örn proposes
       only which tier-map KEY applies to which role.

     If the human asks for something outside these enums — a key that
     doesn't exist, a value not in the closed list — örn says so plainly
     and re-proposes the nearest valid option rather than writing the
     requested value.
   - **Gate surfacing.**
     - *Pilot-gated providers.* If the human asks to enable or assign
       `grok` or `antigravity` while its pilot-clearance marker
       (`.forge/.trust-providers/<provider>.pilot-cleared.local`) is absent,
       örn explains the pilot gate in plain
       language (`operator-profiles.md`, "`enabled-providers`": both are
       pilot-gated behind `fg-c0104`/`fg-c0105`'s evidence review —
       "neither provider is dispatchable until a human has reviewed that
       evidence and cleared the gate") and refuses to write that provider
       into `enabled-providers` or any `role-*` key as part of the
       interview — the conversational flow does not offer a way around
       the gate; it names the gate and stops there for that provider.
     - *Missing trust confirmation.* If the human asks to enable a
       provider whose pilot gate has already cleared (currently `codex`,
       which carries no pilot gate) but this repo/machine has no
       `.forge/.trust-providers/<provider-id>.local` marker for it yet,
       örn points at step 5 ("Per-provider trust confirm") below rather
       than writing the provider in — the interview does not substitute
       for that confirmation.
     - *Dispatch-cap choice.* Same follow-up as FORM mode's role-worker
       card (2(d-form), below) — when örn's proposal turns `role-worker`
       from `claude-only` to a provider, örn surfaces the numeric-cap-vs-
       checkpoint choice explicitly (`max-provider-dispatches-per-session:
       <N>` vs. the shipped checkpoint-only default) before writing it,
       neither pre-selected as an unstated default.
   - **Finish.** Once the human is satisfied, the interview hands off to
     (d)'s own **Validate before finishing** and **Activate** bullets
     above unchanged — the same `validate_profile()` gate, the same
     activate-or-not question, the same failure handling (surfaced error,
     no success report, no pointer switch) as FORM mode.
   - **Editing.** Choosing VIBE mode to customize an already-existing
     profile (stock, preset, or an existing custom file picked as
     `<source>` in step 2a/2b) runs this exact same interview —
     mode-symmetric editing (spec-e8a3, "Dual authoring UX": "a profile
     authored in form mode is fully editable via vibe mode and vice
     versa"). örn's Setup beat opens by summarizing `<source>`'s current
     resolved values so the human decides what to change rather than
     re-stating everything from scratch.

   **2(d-form). FORM mode — `## Providers` field wizard (fg-c0108, spec-e8a3
   "Dual authoring UX").** Fires when the human picks FORM at the mode-choice
   hook in (d)'s Delta capture step above, for a `## Providers` domain delta
   — creating a new custom profile OR editing an existing one (`kind: stock`,
   `preset`, or `custom` alike; a profile authored in VIBE mode is fully
   editable in FORM mode and vice versa, per spec-e8a3's mode-symmetric edit
   AC). Boundary: this subsection only — the VIBE-mode interview (2(d-vibe))
   is a separate task's content and is not defined here.

   - **One card per field.** A structured `AskUserQuestion` wizard, ONE
     question card per `## Providers` field the human is customizing —
     `enabled-providers`, each `role-*` key, or a provider's
     `<provider>-tier-*` pair (`operator-profiles.md`, "`## Providers` key
     vocabulary"). Never one giant multi-field card and never a chained
     sequence of separate prompts outside that discipline — same
     `docs/conventions.md` ("Asking the user questions") rule step 2(d)'s
     Autonomy delta capture already follows.
   - **Every card cites the schema, never invents one.** Each card states:
     the field name; its closed options, drawn verbatim from
     `operator-profiles.md`'s `## Providers` or `## Autonomy` key
     vocabulary (`enabled-providers`/role keys: `codex | grok | antigravity`
     plus `claude-only` for role keys, `none` for `enabled-providers`;
     Autonomy keys when editing that domain: `pause-points`,
     `verification-panel`, `wave-size`'s own closed values) — a FORM-mode
     card never offers an option the cited schema does not define; the
     current value (the profile being edited already has one) or the
     schema-defined default (a field being added fresh) preselected; and a
     concrete, one-line description per option stating what that value
     does, not just its name.
   - **Refuses pilot-gated and un-trust-confirmed providers on the card
     itself.** `grok` and `antigravity` remain pilot-gated while their
     `.forge/.trust-providers/<provider>.pilot-cleared.local` marker is absent
     (`operator-profiles.md`, "`enabled-providers`" — `fg-c0104`/`fg-c0105`
     pilot evidence exists but a human has not cleared real dispatch) and
     any provider without a `.forge/.trust-providers/<provider-id>.local`
     marker is un-trust-confirmed (`docs/conventions/trust-and-security.md`,
     "Per-provider trust confirmation"). FORM mode never hides these options
     or silently drops them — each still appears on its card as a disabled
     option, with the refusal reason stated inline in that option's own
     description (e.g. "grok — disabled: pilot-gated behind `fg-c0104`,
     not yet human-cleared for dispatch" / "codex — disabled: not yet
     trust-confirmed for this repo on this machine, run `/forge:settings`
     provider setup first"). A disabled option is visible with its reason,
     never a hidden option.
   - **Deterministic.** Same source profile plus the same human field
     choices always produce the same set of cards in the same order and
     the same resulting file — FORM mode asks no open-ended question and
     makes no judgment call a VIBE-mode interview would; every card's
     option set is mechanically derived from the cited closed schema.
   - **Writes the identical schema-versioned format.** FORM mode's output
     file is byte-for-byte the same `## Meta` + domain-section container
     format (`operator-profiles.md`, "File shape") that VIBE mode writes —
     normatively, the two authoring modes are indistinguishable downstream
     by any consumer (picker, kernel role resolution,
     `tools/validate_config.py`), per spec-e8a3's "Dual authoring UX" AC.
     This subsection introduces no FORM-mode-specific file variant, header,
     or marker.
   - **Validates before finishing.** Same gate as (d)'s "Validate before
     finishing" bullet above — FORM mode runs `tools/validate_config.py`'s
     `validate_profile()` against the resulting file before reporting
     success or switching the active pointer; a validation failure is
     surfaced to the human and the flow does not complete until it passes.
     FORM mode adds no second validation path alongside `validate_profile()`.
   - **role-worker enablement surfaces the dispatch-cap choice
     (bm-provider-dispatch-cap-surfacing).** When the `role-worker` key's
     card value moves FROM `claude-only` TO an enabled provider — the R1
     automatic-default going live for the builder role — FORM mode fires ONE
     follow-up `AskUserQuestion` card in the same wizard pass, before the
     profile is written: the numeric hard cap and the checkpoint-only
     model presented side by side, neither pre-selected as an unstated
     default. **Numeric hard cap** — `max-provider-dispatches-per-session:
     <N>` — is the only actual stopping control; once this repo's session
     tally reaches `<N>`, further external-provider dispatch this session
     routes to a Claude `forge-worker` instead (`provider-judges.md`
     section 7.6). **Checkpoint-only (visibility)** —
     `max-provider-dispatches-per-session: none` plus
     `provider-dispatch-checkpoint-every: 10` (the shipped default) —
     means dispatch count is UNBOUNDED: the kernel posts a per-10
     checkpoint report and continues unless the human objects at that
     checkpoint, but the checkpoint itself never stops dispatch
     (`provider-judges.md` section 7.6's checkpoint-model amendment). A
     card that already has a numeric cap or an explicit checkpoint pair
     set shows that current value preselected instead of leaving neither
     selected; a role-worker card that stays `claude-only`, or moves FROM
     a provider back TO `claude-only`, never fires this follow-up.

3. **Offer edits — one structured question.** Per `docs/conventions.md`
   ("Asking the user questions"), put the edit decision to the user as ONE
   `AskUserQuestion` call: batch the related decisions (which toggles to flip,
   which values to change, which provider toggle to flip, plus a "Change
   operator profile" option that opens step 2 above) as individual questions
   in that single call — current value marked, e.g. "continuous-loop: on
   (current) / off". Include a "No changes" path. Never merge unrelated
   settings into one option list. A provider-toggle edit that would turn a
   provider ON is offered here like any other toggle flip, but its actual
   write is deferred to step 5's trust-confirmation flow below rather than
   applied directly by step 4 — flipping a provider toggle to `on` is never
   itself sufficient to enable dispatch.

4. **Validate, then apply the minimal diff.** BEFORE writing anything, check
   every proposed new value against `skills/kernel/references/settings-
   schema.md`'s Type/Allowed-values columns for that key (`tools/
   validate_config.py`'s parsing rules are that same schema's runtime
   enforcement — a value this step would write must be one `validate_config.py`
   itself would accept). A value failing that check is reported back to the
   human with the expected shape and not written.

   **Floor check.** If the proposed change would cross a floor
   `settings-schema.md` marks on that key (`trust-confirmation`,
   `human-set-cap`, `spec-approval-gate`, `providers-default-off` —
   `docs/conventions/config-and-features.md`, "Floor-protected settings"),
   refuse the write and name the floor plainly, e.g. "refused —
   `max-tasks-per-session` is a human-set-cap floor; lower it explicitly if
   you intend to, but it will never be raised as a side effect of another
   change" or "refused — a provider's forge.md toggle can be turned off
   freely, but turning it on never bypasses its trust-confirmation floor;
   see step 5." No settings edit ever overrides a floor, regardless of how
   the request is phrased.

   For each remaining changed setting, edit `.forge/forge.md` in place —
   write ONLY the changed lines, preserve everything else byte-for-byte
   (comments, unknown keys, section order, untouched sections) — never
   rewrite a section the human didn't ask to change. If the user opted to
   materialize a missing `## Features` section, write it from the config
   template with their chosen values, placed before `## Budgets`; if the
   user opted to materialize a missing `## Providers` section, write it from
   the config template (all known providers listed, each `off` unless the
   human just chose to enable one — subject to step 5's confirm), placed
   after `## Budgets` and before `## Queue`, matching the template's own
   section order. Confirm with a short before → after list, and — if the
   change affects how `/forge:start` behaves (`continuous-loop`, a budget
   key, `workflow-executor`, a provider toggle) — one line naming that
   effect on the next run; otherwise nothing else.

5. **Per-provider trust confirm (`providers` entry point).** This is the
   `/forge:providers` job folded into `/forge:settings` rather than a
   separate command (settings.md already owns the Features toggle flow this
   reuses end-to-end — a second command would just duplicate steps 1–4 for
   one toggle). Three cases:
   - **Turning `providers` on for the first time.** After step 4 writes
     `providers: on`, ensure `.forge/.trust-providers/` is in the repo's
     `.gitignore` — append the line idempotently (never duplicated) if it
     isn't already present, same idempotent-append style `forge:onboard`
     uses for `.forge/.trust-local`/`.forge/.provenance` — BEFORE offering
     provider setup, so no `.forge/.trust-providers/*.local` confirmation
     marker (see the bullet below) can ever be written into a repo whose
     `.gitignore` doesn't cover it yet. Then offer (structured question,
     same discipline as step 3 above) to walk provider setup now or later.
     This step only unlocks the Feature — it enables no provider by itself.
   - **Enabling a specific provider** (here, or from wherever a provider is
     first assigned to a role per spec-e8a3's `## Providers` section):
     require `providers: on` first (if it is `off`, stop and offer to turn
     it on via step 3/4 before continuing — never silently flip it as a
     side effect of a provider pick). Then, if
     `.forge/.trust-providers/<provider-id>.local` does not already exist
     (`docs/conventions/trust-and-security.md`, "Per-provider trust
     confirmation"), present the one-line risk verbatim as a structured
     CONFIRM/DECLINE question naming the provider:
     "dispatching sends repo content to another vendor". On CONFIRM, write
     the machine-local marker file (format in that section) AND write that
     provider's forge.md `## Providers` toggle to `on` (materializing the
     section per step 4 if it doesn't exist yet) in the same apply — a
     provider is never left trust-confirmed but toggled off, or toggled on
     but unconfirmed, as the result of this one flow. On DECLINE or no
     response, do not enable the provider, do not write the marker, and do
     not write its toggle to `on` — report plainly that it remains
     unconfirmed. An already-present marker for that provider is not
     re-prompted; if the toggle happens to already be `off` in that case
     (e.g. a human previously toggled a confirmed provider back off), this
     flow offers to flip it back to `on` via the same ordinary toggle edit
     step 3/4 already handles — no second confirmation is re-asked, per
     "Toggling off never clears TOFU."
     Confirmed once per provider per repo per machine. Pilot-gated
     providers (`grok`, `antigravity`): this flow
     still writes the trust marker and toggle on request (matching
     `operator-profiles.md`'s "accepted and stored" posture), but states
     plainly, before asking to confirm, that the provider remains
     undispatchable until its separate pilot gate clears — trust
     confirmation and toggle state are not what unlocks a pilot-gated
     provider.
   - **Clearing a pilot gate.** For `grok` or `antigravity`, show its
     evidence path (`docs/pilots/2026-07-19-grok-pilot.md` or
     `docs/pilots/2026-07-19-antigravity-smoke.md`) in a structured
     CLEAR/KEEP-CLOSED question and ask the human to review that evidence.
     ONLY on CLEAR may `/forge:settings` write
     `.forge/.trust-providers/<provider>.pilot-cleared.local`. The marker is
     machine-local, never committed, and covered by the same
     `.forge/.trust-providers/` gitignore entry as the TOFU markers. On
     KEEP-CLOSED or no response, do not write it; an absent marker means the
     pilot gate remains closed. A settings edit NEVER writes the marker
     without that flow, even if that edit enables the Feature, provider
     toggle, trust marker, or profile role.

**Custom profiles are git-tracked, not gitignored.** `.forge/profiles/*.md`
is ordinary project-space state (`docs/conventions/config-and-features.md`,
"Customization persistence contract — 2026-07-18 (fg-b0101)") and is
committed with the repo like any other `.forge/` file — do not add it, or
`.forge/profiles/`, to `.gitignore`. Only the machine-local TRUST MARKERS
this file's step 5 writes (`.forge/.trust-providers/*.local`, including
`<provider>.pilot-cleared.local`, alongside the
existing `.forge/.trust-local`/`.forge/.provenance`) are gitignored; a custom
profile file is not a trust marker and must never be confused with one.

Natural-language edits are also valid input when `natural-language-invocation`
is `on`: `$ARGUMENTS` like "turn off auto loops" maps to the matching key
(`continuous-loop: off`), confirm the interpretation in the same structured
question before writing. If `$ARGUMENTS` is empty, just do steps 1, 3, 4
(step 2 fires on an explicit profile-switch ask; step 5 only fires when
`providers` or a specific provider is actually being enabled, or when pilot
clearance is requested).
