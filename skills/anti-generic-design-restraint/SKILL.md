---
name: anti-generic-design-restraint
description: The taste-and-judgment gate before committing to a visual direction — name and avoid the "AI-generated look", brainstorm-then-critique in two passes, and spend boldness in exactly one place. Use when starting a new UI, choosing a palette/type/layout direction, or sensing a design reads as templated/default. Defers all motion decisions to motion-design-principles. Triggers on "make this less generic", "design direction", "this looks AI-generated", "visual identity", "pick a palette/typeface".
---

<!-- last-verified: 2026-07 -->

# Anti-generic design restraint

The judgment layer that runs *before* you write CSS. Its job is to keep the design
from landing on the defaults every AI reaches for, and to make each visual choice a
choice made for *this* brief. Distinctiveness comes from restraint and specificity,
not from adding more.

**Precedence vs `frontend-design`:** `frontend-design` owns craft and visual
direction — palette, type, layout, the overall aesthetic call. This skill is
the narrower taste gate applied on top of that direction: it only vetoes
genericness, it doesn't choose the direction. On conflict, `frontend-design`'s
direction leads; this skill's role is to flag when that direction (or any
part of it) reads as the generic default and send it back for revision, not
to overrule it with a competing direction of its own.

## 1. Name the anti-patterns you're avoiding

The "AI-generated look" is a small set of recognizable tells. Watch for them:

- **Generic default combinations** — the palette/type/layout you'd produce for any
  similar prompt regardless of subject. The current clusters: warm cream
  background + high-contrast serif + terracotta accent; near-black + a single acid
  accent; broadsheet hairline rules with zero radius. All legitimate *sometimes*,
  but defaults, not decisions.
- **Overuse of gradients and glows** — decorative gradient accents, glowing
  borders, and soft shadows applied everywhere signal templated output.
- **Excess motion** — **extra animation contributes to the feeling that the design
  is AI-generated.** Restraint doctrine: fewer, more deliberate moments beat
  scattered effects. (Motion specifics are not yours — see §4.)

If a choice appears "regardless of subject," it's a default. Replace it with
something the brief's own world justifies.

## 2. Two-pass: brainstorm, then critique

Never commit to the first direction. Work in two passes before any code:

1. **Brainstorm** — sketch a compact direction: a 4–6 value named palette, 2+ type
   roles (a characterful display face used with restraint, a body face, a utility
   face if needed), a layout concept, and one *signature* element the design will
   be remembered by.
2. **Critique** — run the plan back against the brief. Ask: if I worked a similar
   prompt from scratch, would I arrive here anyway? Every part that reads as the
   generic default gets revised, and you say what you changed and why. Only a
   direction that survives its own critique gets built.

Spend boldness in **one place** — let the signature element be the memorable thing
and keep everything around it quiet. Chanel's rule: before you ship, remove one
accessory. Cut any decoration that doesn't serve the brief.

## 3. Establish a token scale, then reuse it

Don't generate ad-hoc hex values and spacing numbers as you go — that's how a
design drifts into inconsistency and default-soup. Define the scale once (color,
type, spacing, radius) and derive every subsequent value from it. This pairs with
`design-tokens-pipeline`: the direction you settle on here becomes the token set
the whole UI consumes. Reuse over reinvention on every screen.

## 4. Motion is not decided here

**Defer all motion decisions to `motion-design-principles`.** This skill decides
*whether the design earns motion at all* (restraint doctrine, §1), but every
question of duration, easing, stagger, spring-vs-bezier, and reduced-motion
behavior belongs to that skill. When a direction calls for an animated moment, hand
off — don't invent timings or curves here.

## 5. The quality floor, unannounced

A distinctive direction still ships the basics without fanfare: responsive to
mobile, visible keyboard focus, reduced motion respected, real copy (not lorem)
written from the user's side of the screen. Elegance is executing the chosen vision
well — match execution complexity to the vision's ambition.

## Sources

Adapted from:
- Anthropic `frontend-design` skill (installed as `frontend-design:frontend-design`)
