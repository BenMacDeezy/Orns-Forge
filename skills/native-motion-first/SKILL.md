---
name: native-motion-first
description: Reach for platform animation APIs before reaching for a library — CSS transitions/keyframes, the Web Animations API, the View Transitions API, and scroll-driven animation-timeline. Use when animating UI state changes, page/state swaps, imperative play/pause/reverse sequences, or scroll-linked effects, and before adding an animation library (GSAP, Framer Motion/Motion, anime.js) to the dependency tree. Triggers — "animate this", "transition between states", "page transition", "scroll animation", "should I use GSAP", "reduce motion", "animation jank".
---

<!-- last-verified: 2026-07 -->

# Native motion first

Every animation library ships more than the browser already gives you for
free. Before adding one, check whether a native API covers the case — it
usually does, it ships zero bytes, and it composes with the platform's own
accessibility and performance handling instead of fighting it.

## Decision rule

Pick the narrowest API that covers the need, in this order:

1. **CSS transitions/keyframes** — simple state feedback (hover, focus,
   toggle, loading spinner, a class flipping a property). Declarative, no
   JS on the hot path, the browser owns the timing.
2. **Web Animations API (`el.animate()`)** — imperative control without a
   library: play/pause/reverse/seek, animations driven by runtime values,
   or composing several keyframe effects. Reach here when CSS can express
   the keyframes but the *triggering logic* needs JS control over
   playback, not when you need JS because CSS transitions feel awkward to
   write.
3. **View Transitions API** — animating a page or DOM-state swap as a
   single before/after crossfade-and-morph, not a property tween.
   `document.startViewTransition()` for same-document DOM swaps (SPA route
   change, list-to-detail, theme toggle); `@view-transition
   { navigation: auto }` for cross-document (MPA) navigations — Chromium 126+
   and Safari 18.2+ only. Firefox 144 (Oct 2025) shipped same-document view
   transitions but not cross-document; cross-document transitions still
   require a feature-detect and graceful fallback (instant swap for unsupported
   browsers). Don't reach for a "page transition library" before checking
   whether same-document transitions cover it.
4. **`animation-timeline: scroll()` / `view()`** — scroll-linked
   animation (progress bars, parallax, reveal-on-scroll, sticky-header
   shrink). Driven by the compositor from scroll position, not a scroll
   event handler — no `requestAnimationFrame` polling loop to write or
   debug.

If none of these can express the motion — physics-based gesture response,
designer-authored vector animation, complex orchestrated timelines across
many independent elements — that's the signal to bring in a library; see
`lottie-rive-vector-animation` and `spring-physics-and-list-animation` for
those cases specifically.

## Always animate transform and opacity

Whichever API you use, animate `transform` and `opacity` only. Both run on
the compositor thread: the browser can composite frames without touching
layout or paint, so the animation stays smooth even when the main thread is
busy. Animating `top`/`left`/`width`/`height` (or anything that isn't
transform/opacity) forces layout recalculation and repaint on every frame —
that's the single most common source of janky animation, independent of
which API triggered it. If you need to move an element, animate
`transform: translate()`; if you need to resize it, prefer `transform:
scale()` where the visual result allows it, or reach for `calc-size()`
below when you specifically need auto-sized layout to animate.

## Accessibility: View Transitions handle it for you

The View Transitions API is the one animation API that auto-suppresses
under `prefers-reduced-motion` — the browser reduces the transition to an
instant swap without any extra code. Every other API (CSS transitions/
keyframes, WAA, scroll-timeline) requires an explicit
`@media (prefers-reduced-motion: reduce)` rule or a JS check
(`matchMedia('(prefers-reduced-motion: reduce)').matches`) to disable or
shorten motion. Don't assume reduced-motion is handled just because the
animation "looks native" — verify which API is driving it.

## New CSS (2025-2026): entrance animation and animatable auto-sizing

- **`@starting-style` + `transition-behavior: allow-discrete`** — animate
  an element *in* from `display: none` (or `content-visibility: hidden`),
  e.g. a `<dialog>` or popover fading/scaling in on open instead of
  snapping to visible. Previously required a JS-driven double-rAF hack to
  fake a "before" state; this makes entrance transitions pure CSS.
- **`calc-size()` / `interpolate-size: allow-keywords`** — animate
  `height: auto` (or `width: auto`, `grid-template-rows`, etc.) without
  measuring the element in JS first. Accordions and expand/collapse
  panels no longer need a `scrollHeight` read-then-animate dance.

## Graceful degradation for scroll-driven CSS

Scroll-driven `animation-timeline` isn't universal yet. Feature-detect and
fall back rather than assuming support:

```css
@supports not (animation-timeline: scroll()) {
  /* GSAP ScrollTrigger fallback, or a rAF-driven scroll handler */
}
```

Write the native rule first, then the fallback inside the negated
`@supports` block — don't invert this and make the library the default
path with native CSS as an "enhancement," since that keeps the library on
the critical path for every browser instead of just the gap.

Adapted from: https://developer.chrome.com/blog/view-transitions
Adapted from: https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API
Adapted from: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_scroll-driven_animations
Adapted from: https://web.dev/articles/animations-guide
