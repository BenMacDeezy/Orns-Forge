---
name: mem-e7b1a4
description: shadcn/ui default Button focus ring (focus-visible:ring-3 ring-ring/50) can render as transparent zero-spread box-shadow layers under Tailwind v4 + Turbopack — invisible keyboard focus (WCAG 2.4.7); verify focus rings PAINT via computed box-shadow/screenshot, never trust source classes or a hex-contrast test
type: gotcha
created: 2026-07-18T15:05:05Z
updated: 2026-07-18T15:05:05Z
superseded-by: null
schema-version: 1
agents: forge-ui, forge-ui-verifier
---

Promoted from project fact `tailwind-v4-button-ring-not-painting`
(observed under Next.js + Tailwind v4 + Turbopack).

The stock shadcn/ui `<Button>` focus-visible combo
`focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`
compiled to a valid box-shadow formula but painted fully transparent
(five zero-spread rgba(...,0) layers, border rgba(0,0,0,0)) — keyboard
focus invisible on high-traffic buttons. A 425-test suite AND a
token-hex contrast test both passed; only a live keyboard walk with a
getComputedStyle box-shadow dump + focused/unfocused screenshots caught
it.

Applies in any Tailwind-v4 / shadcn repo:
- Prefer an explicitly-painting focus pattern: `outline-none
  focus-visible:ring-2 focus-visible:ring-<accent> focus-visible:
  ring-offset-2 focus-visible:ring-offset-<background>`. The ring-offset
  is load-bearing when the control's own fill equals the ring color
  (accent button + accent ring) — it inserts a background-colored gap so
  the ring's contrast partner is the page, not the fill.
- Focus VISIBILITY is a rendered property: verify with computed
  box-shadow (must be non-transparent) and a screenshot, never from the
  source className or a color-token contrast test — those are structurally
  blind to a non-painting composite.
