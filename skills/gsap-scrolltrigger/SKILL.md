---
name: gsap-scrolltrigger
description: GSAP + ScrollTrigger for pinning, scrubbing, and sequenced scroll-driven timelines. Use when building scroll storytelling, pinning a section while content animates, scrubbing animation progress to scroll position, sequencing multi-property timelines, or animating SVG/motion-path. Triggers on "GSAP", "ScrollTrigger", "pin this section", "scrub animation to scroll", "scroll-driven timeline", "SVG path animation", "gsap.timeline".
---

<!-- last-verified: 2026-07 -->

# GSAP + ScrollTrigger

Defer duration/easing/stagger choices to `motion-design-principles` — this
skill is the scroll-driven implementation layer.

## 1. 2025: GSAP is 100% free

After the Webflow acquisition, **all of GSAP is free**, including
**ScrollTrigger, SplitText, and MorphSVG** — plugins that used to require a
paid Business/Club GreenSock license. The old "GSAP is great but the good
plugins are paywalled" objection no longer applies; don't route around
ScrollTrigger for licensing reasons.

## 2. Core API

```js
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);

// one-shot tween
gsap.to(".box", { x: 200, duration: 0.4, ease: "power2.out" });

// sequenced timeline — properties fire in order, can overlap with position params
gsap.timeline()
  .to(".a", { opacity: 1, duration: 0.3 })
  .to(".b", { x: 100, duration: 0.3 }, "<0.1"); // start 0.1s after previous starts
```

ScrollTrigger attaches to any tween or timeline via the `scrollTrigger`
option — it doesn't replace `gsap.to()`/`gsap.timeline()`, it drives them:

```js
gsap.to(".panel", {
  scrollTrigger: {
    trigger: ".panel",
    start: "top top",
    end: "+=1000",
    scrub: true,       // ties animation progress directly to scroll position
    pin: true,          // pins .panel in place while the scroll range plays out
    toggleActions: "play pause resume reverse", // enter/leave/enter-back/leave-back
  },
  x: 300,
});
```

- `scrub: true` (or a number of seconds of lag) makes the animation a
  *function of scroll position*, not an independent timed animation —
  scrolling back plays it backward.
- `pin: true` locks the trigger element in the viewport for the duration of
  the scroll range, so content inside it can animate while the page
  visually "stops."
- `toggleActions` controls play state for **non-scrubbed** triggers crossing
  the viewport boundary; irrelevant once `scrub` is set.

## 3. Where it's the right tool

- **Strong fit**: pinning sections, scroll-scrubbed progress (scrollytelling),
  multi-property sequenced timelines where several elements move on a
  coordinated schedule, SVG/motion-path animation (`MotionPathPlugin`), and
  any scroll storytelling that needs to work today across browsers.
- Treat it as the production-safe choice for scroll storytelling **until**
  native scroll-driven CSS (`animation-timeline: scroll()` /
  `view()`) has full cross-browser support — native CSS scroll-linking is
  lighter-weight but not yet reliable enough to depend on alone for
  production pinning/scrubbing.
- For plain React component transitions, gestures, or simple
  `whileInView` reveals, prefer `motion-react` — GSAP is heavier machinery
  than that job needs.

## 4. Accessibility

```js
gsap.matchMedia().add("(prefers-reduced-motion: reduce)", () => {
  // reduced-motion branch: swap scrub/pin/parallax for a simple opacity fade
  gsap.set(".panel", { opacity: 1, x: 0, y: 0 });
});
```

`gsap.matchMedia()` is GSAP's responsive/conditional API — use a
`(prefers-reduced-motion: reduce)` condition to define a substitution branch
(per `motion-design-principles`: swap, don't delete) instead of gating the
whole ScrollTrigger setup behind an `if` that leaves the reduced-motion user
with a broken/unstyled layout. It also cleans up its own ScrollTriggers when
the media query stops matching (e.g. viewport resize crosses a breakpoint),
which manual conditionals don't do for free.

## 5. Performance characteristics

- ScrollTrigger **precomputes trigger offsets** on load/refresh rather than
  polling scroll position every frame — cheaper than a hand-rolled
  `scroll` listener doing `getBoundingClientRect()` on every event.
- Call `ScrollTrigger.refresh()` after layout-affecting changes (images
  loading, dynamic content, font swaps) or offsets drift out of sync with
  actual element positions.
- Cost: **~23kb+ (gzipped, core + ScrollTrigger) and not tree-shakeable** —
  budget for the whole plugin, not just the pieces used. That's the
  trade-off for the timeline/scrub/pin feature set; a page needing only a
  couple of `whileInView` reveals doesn't need to pay it.

## Sources

Adapted from:
- https://gsap.com/docs/v3/Plugins/ScrollTrigger
- https://gsap.com/docs/v3/GSAP/gsap.matchMedia
- https://gsap.com/pricing
