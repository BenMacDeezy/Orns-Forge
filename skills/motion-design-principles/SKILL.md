---
name: motion-design-principles
description: The taste layer every other animation skill defers to — duration bands, easing, stagger, spring-vs-bezier, and when not to animate. Use when choosing a duration or easing curve, reviewing a transition for feel, deciding whether motion is warranted at all, or setting up prefers-reduced-motion behavior. Triggers on "animation duration", "easing curve", "this transition feels off/slow/janky", "stagger the list", "reduced motion", "should this animate".
---

<!-- last-verified: 2026-07 -->

# Motion design principles

The taste layer. `motion-react` and `gsap-scrolltrigger` implement animation
in code; this skill decides *whether*, *how long*, and *what curve* — defer to
it before reaching for either library.

## 1. Duration bands by function

Pick duration from what the motion is *for*, not from a house default:

| Function | Duration | Notes |
|---|---|---|
| Hover / focus feedback | <100ms | Near-instant; any lag reads as unresponsive |
| Button press, icon swap | 100–200ms | Small, local, high-frequency |
| State transition, modal open/close | 200–400ms | Enough to convey spatial change without stalling |
| Anything gating user action | 400–500ms hard ceiling | Past 500ms reads as delay, not motion |

Two dials adjust the band, not replace it:

- **Scale UP with distance/size travelled** — an element crossing the whole
  viewport earns more time than one nudging 4px.
- **Scale DOWN with exposure frequency** — anything the user sees dozens of
  times a session (list-item hover, tab switch) stays under ~150ms even if
  the "state transition" band would allow more. Frequency fatigue outweighs
  the base band.

## 2. Entrance/exit asymmetry

- **Exit ≈ 75% of enter duration.** Leaving should feel quicker than
  arriving — the user's attention has already moved on.
- **Ease-out (decelerate to rest) for entrances**; **ease-in (accelerate
  away) for exits.** An entrance that's still accelerating when it lands
  feels like it overshoots; an exit that lingers at full speed feels sluggish.
- **Anchor transform-origin to the trigger.** A menu opens from the button
  that opened it, a modal scales from its trigger point, not from the
  viewport center — the motion should look like it *came from* the thing the
  user interacted with.

## 3. Stagger orchestration

- List/grid entrances: **20–50ms per-item offset**, overlapping (each item's
  animation starts before the previous one finishes), never sequential
  (item N+1 waiting for item N to fully complete reads as slow no matter how
  short each individual animation is).
- **Cap the total sequence** for long lists — beyond ~8–10 visible items,
  either clamp the per-item offset down or stagger only the first screenful
  and let the rest appear together. An unbounded stagger on a 50-row table
  is a multi-second animation nobody asked for.

## 4. Spring vs bezier

- **Bezier curves** for one-shot, non-interruptible motion: the user
  triggers it, it plays to completion, done (modal open, page transition).
  Predictable, authorable, matches a fixed duration budget.
- **Spring physics** for gesture- or drag-driven motion: anything the user
  can interrupt mid-flight (drag-to-dismiss, swipe, resizable panels) needs
  a spring because it re-solves from the *current* velocity when interrupted
  — a bezier animation restarted mid-flight visibly stutters.
- Rule of thumb: if a human's finger/cursor can still be touching it while
  it animates, use a spring; if the trigger is a discrete event, use bezier.

## 5. When NOT to animate

- **Auto-triggered or ambient motion is an accessibility and vestibular
  risk** — carousels that autoplay, parallax that scrolls independent of
  user input, looping background motion. Default to off; require explicit
  user action to start it.
- **Never `transition: all`.** It animates properties nobody asked for
  (layout shifts, color-scheme swaps) and silently breaks the moment an
  unrelated property changes. Name the properties.
- **WCAG 2.2.2 (Pause, Stop, Hide)**: any motion that runs automatically for
  more than 5 seconds needs a visible pause/stop control. If you can't add
  one, don't let it auto-run that long.

## 6. prefers-reduced-motion is substitution, not deletion

Reduced motion means *swap the motion type*, not *turn animation off
entirely* — a state change with zero transition can be more disorienting
than a fast one.

- Swap scale/rotate/translate/parallax for **opacity or color** changes at
  **~100–150ms**. The state change is still perceptible; the vestibular
  trigger (motion, especially large-scale or spinning) is gone.
- **Implement "no-motion-first"**: write the reduced-motion styles as the
  base case, then layer the full-motion version under
  `@media (prefers-reduced-motion: no-preference)`. This is the inverse of
  the naive approach (full motion as base, `(prefers-reduced-motion: reduce)`
  as an override) — no-motion-first guarantees a user with the preference
  set never even briefly sees the motion you're overriding, and it keeps the
  reduced path from silently rotting when nobody remembers to update it.

## Sources

Adapted from:
- https://m3.material.io/styles/motion/easing-and-duration
- https://carbondesignsystem.com/elements/motion/overview
- https://atlassian.design/foundations/motion
- https://www.nngroup.com/articles/animation-duration
- https://web.dev/articles/prefers-reduced-motion
