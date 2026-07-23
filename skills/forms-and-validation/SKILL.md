---
name: forms-and-validation
description: Build forms with schema-validated inputs and accessible error states — React Hook Form + Zod/Valibot, cross-platform (web + React Native) validation UX, and error-state accessibility. Use when building or reviewing any form, wiring a validation schema, adding client-side field validation, or handling form error messages. Triggers on form, input validation, react-hook-form, zod, valibot, schema validation, field error, form accessibility.
---
<!-- last-verified: 2026-07 -->

# Forms & schema validation

## 1. React Hook Form + Zod/Valibot — the current stack

As of 2026, the verified baseline is **react-hook-form v7 (7.80+)** with
**`@hookform/resolvers` v5**, backing **Zod v4** or **Valibot**.

- `@hookform/resolvers` v5 ships a dedicated `valibotResolver`
  (`@hookform/resolvers/valibot`) for Valibot schemas, plus a separate
  generic `standardSchemaResolver`
  (`@hookform/resolvers/standard-schema`) for any Standard-Schema-
  compliant library (Zod, Valibot, ArkType) when a library-specific
  resolver isn't wanted. **`zodResolver` itself only accepts Zod schemas
  and has no Standard Schema fallback** — never point a Valibot schema at
  it [verified against react-hook-form/resolvers source, 2026-07: the
  zod resolver type-guards on Zod v3/v4 only]. Confirm the resolver
  package version in `package.json` before assuming an import path
  exists; pin/verify against
  https://github.com/react-hook-form/resolvers/releases at build time.
- **One schema, one source of truth**: define the Zod/Valibot schema once
  and derive both the TypeScript type (`z.infer<typeof schema>`) and the
  runtime validator from it — don't hand-write a parallel TS `interface`
  that can drift from the schema.
- **Validate at the boundary twice**: client-side (RHF + resolver) for UX,
  server-side (the same or an equivalent schema) for correctness — client
  validation is a UX convenience, never a security control. A request can
  always bypass the client entirely.
- Prefer `mode: "onBlur"` or `"onTouched"` over `"onChange"` for the initial
  validation trigger — validating every keystroke before the user has
  finished a field produces premature error noise; re-validate on change
  only *after* a field has already been touched/errored once (RHF's default
  re-validation behavior does this correctly out of the box).

## 2. Cross-platform validation UX (web + React Native)

RHF's core (`useForm`, `register`/`Controller`, resolvers) is
framework-agnostic — the same schema and validation logic run under React
DOM and React Native. What changes across platforms is the *input* and
*error-surfacing* layer:

- **Web**: `register` binds directly to native `<input>` elements. Errors
  render as inline text tied to the field via `aria-describedby` (§3).
- **React Native**: there's no native `<input>` to `register` onto, so every
  field goes through **`Controller`** — RHF's escape hatch is used as the
  default here (`<Controller name="email" control={control} render={({field, fieldState}) => ...}/>`),
  wrapping `TextInput` and passing `field.onChange`/`field.value` through
  manually.
- **Debounce remote/async validation identically on both platforms**
  (e.g. a username-availability check) — RN's on-screen keyboard has no
  native `blur`-on-Enter behavior in the same way web forms do, so lean on
  `onBlur` mode plus a debounced async resolver rather than firing a network
  call on every keystroke on either platform.
- **Submit affordance differs**: web forms submit on Enter by default inside
  a `<form>`; RN has no implicit submit — wire the primary action button
  (or `returnKeyType="done"` + `onSubmitEditing`) explicitly, and disable it
  while `formState.isSubmitting` is true on both platforms to prevent
  double-submit.
- **Keyboard-aware layout on RN**: a validation error appearing below a
  focused field can be pushed off-screen by the keyboard — wrap forms in a
  `KeyboardAvoidingView`/scroll-into-view pattern so a newly-shown error is
  actually visible, not just present in the DOM/tree.

## 3. Error-state accessibility — tied to `accessibility-wcag-aria`

A validation error that's only a red border or a color change fails WCAG
2.2 **1.4.1** (color alone is not a valid state indicator — see
`accessibility-wcag-aria` §"Contrast minimums"). Every invalid field needs
all of the following, not just one:

- **Programmatic association**: `aria-invalid="true"` on the field, and
  `aria-describedby` pointing at the error message's `id` — this is what
  lets a screen reader announce the error when the field receives focus, not
  just when it's visually near the input.
- **Text, not just color**: an icon or explicit error copy alongside any red
  border/highlight — color-only state fails
  `accessibility-wcag-aria`'s "do not rely on color alone" rule directly.
- **Accessible name still holds**: the field's `<label for>` association
  (never `placeholder`-as-label — `accessibility-wcag-aria` §"Every control
  needs an accessible name") must remain intact when an error appears; don't
  let error-message injection replace or obscure the field's actual label.
- **Focus management on submit-time validation**: when a submit reveals new
  errors, move focus to the first invalid field (or an error summary that
  links to each field) rather than leaving focus wherever it was — a
  sighted user sees the red text; a keyboard/screen-reader user needs focus
  to move there to discover it at all. This is the same "focus moves to
  where the state changed" principle `accessibility-wcag-aria` applies to
  dialogs.
- **Live region for async/submit errors**: a schema error that appears after
  the user has already moved away from the field (e.g. a failed server
  round-trip) needs `role="alert"` or an `aria-live="polite"` region so it's
  announced even though focus isn't on that field — a silently-appearing
  error below a field nobody's looking at is invisible to a screen-reader
  user.
- **Contrast**: error text and error-state borders still need the 4.5:1
  (text) / 3:1 (UI component) minimums from `accessibility-wcag-aria`
  §"Contrast minimums" — a pale/light error red that reads fine visually
  to a sighted developer can fail contrast outright.
- React Native has no native `aria-*`/DOM, but the equivalent
  accessibility props exist and carry the same obligation:
  `accessibilityState={{ invalid: true }}` (or `accessible` +
  `accessibilityLabel` describing the error) on the field, and route the
  error text through `AccessibilityInfo.announceForAccessibility()` for the
  live-region-equivalent case — screen-reader users on mobile need the same
  signal web users get from `aria-live`.

## Before you ship — checklist

- [ ] Schema (Zod/Valibot) is the single source of truth for both the
      TypeScript type and the runtime validator — no hand-duplicated interface
- [ ] The same/equivalent validation runs server-side — client validation is
      UX only, never trusted as the security boundary
- [ ] Initial validation trigger is `onBlur`/`onTouched`, not raw `onChange`,
      to avoid premature per-keystroke error noise
- [ ] React Native fields go through `Controller`, not a `register` call
      that assumes a DOM `<input>`
- [ ] Submit button disables during `formState.isSubmitting` on both
      platforms to prevent double-submit
- [ ] Every invalid field has `aria-invalid` + `aria-describedby` (web) or
      `accessibilityState={{invalid:true}}` (RN) wired to the actual error text
- [ ] Error state is never color-only — text/icon accompanies every
      red-border/highlight cue
- [ ] Submit-time validation moves focus to the first error (or an error
      summary), not left wherever focus already was
- [ ] Async/late-arriving errors use `aria-live`/`role="alert"` (web) or
      `AccessibilityInfo.announceForAccessibility` (RN)
- [ ] Error text and error-state borders meet `accessibility-wcag-aria`'s
      contrast minimums (4.5:1 text, 3:1 UI)
- [ ] `@hookform/resolvers` version was checked against its own release
      notes, and the right resolver import is used per schema library —
      `zodResolver` for Zod only, `valibotResolver` for Valibot,
      `standardSchemaResolver` for the generic Standard Schema path

---
Adapted from:
- React Hook Form — https://tomodahinata.com/en/blog/react-hook-form (checked 2026-07)
- `@hookform/resolvers` — https://www.npmjs.com/package/@hookform/resolvers, https://github.com/react-hook-form/resolvers (checked 2026-07)
- `accessibility-wcag-aria` (this repo, `skills/accessibility-wcag-aria/SKILL.md`) — contrast minimums, accessible-name rule, focus-management pattern
- WAI-ARIA APG / WCAG 2.2 — https://www.w3.org/WAI/ARIA/apg/patterns/, https://www.w3.org/WAI/standards-guidelines/wcag/
