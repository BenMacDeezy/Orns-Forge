---
name: core-web-vitals-for-ui
description: Build UI that passes Core Web Vitals — responsive interactions (INP), stable layout (CLS), and fast largest paint (LCP) as first-class implementation constraints, not an afterthought. Use when an interaction feels laggy, when content jumps as it loads, when reserving space for async data, or when a component must hit the field thresholds. Triggers on "Core Web Vitals", "INP", "CLS", "LCP", "layout shift", "janky/laggy interaction", "main thread".
---

<!-- last-verified: 2026-07 -->

# Core Web Vitals for UI

Three field metrics, measured at the **p75** of real users. Treat the thresholds
as build constraints, not a post-launch audit.

| Metric | Measures | Good (p75 field) |
|---|---|---|
| **LCP** | Largest contentful paint | **≤ 2.5s** |
| **INP** | Interaction to Next Paint | **≤ 200ms** |
| **CLS** | Cumulative Layout Shift | **≤ 0.1** |

**INP replaced FID in March 2024.** FID only measured input *delay*; INP measures
the full interaction — input to the next painted frame — so slow event handlers
and render work now count against you. Old "good FID" code can fail INP.

## 1. INP — keep interactions responsive

The main thread paints. Anything hogging it delays the next frame.

- **Break up long JS tasks and yield the main thread.** Split work over 50ms into
  chunks and yield between them (`await scheduler.yield()`, or a `setTimeout(0)` /
  `await new Promise(r => setTimeout(r))` boundary) so a queued click can be
  handled between chunks instead of after all the work finishes.
- **Batch DOM reads and writes; never interleave them.** Read all layout values
  first, then write all mutations. Alternating read → write → read → write forces
  the browser to recompute layout each cycle — **layout thrashing** — and each
  forced reflow blocks the frame.
- **Give immediate visual feedback during async waits.** On click, paint a
  spinner / disabled / pressed state *before* awaiting the network or heavy work.
  The interaction feels responsive because *something* rendered on the next frame,
  even though the result is still loading.

## 2. CLS — keep layout stable

Every unreserved late-arriving element shoves its neighbors and costs CLS.

- **Reserve space for async content.** Set explicit `width`/`height`, or an
  `aspect-ratio`, or a min-height skeleton for images, ads, embeds, and data that
  loads after first paint — so the box is the right size before content lands.
- **Don't insert content above existing content** unless it's a direct response to
  a user interaction. A banner or notice injected at the top non-interactively
  pushes everything down and shifts what the user was reading.
- **Watch font-swap reflow.** A late web font with different metrics re-lays-out
  text (`font-display` swap). Use `size-adjust` / the `f-mods`
  (`ascent-override`, etc.) or a metrically-matched fallback so the swap doesn't
  reflow the paragraph.

## 3. LCP — paint the main thing fast

- Identify the LCP element (usually the hero image or headline) and make sure it
  isn't waiting behind render-blocking CSS/JS, lazy-loading, or a late font.
- Prioritize it: preload the hero image, don't `loading="lazy"` the LCP image,
  and keep its container's space reserved (which also protects CLS).

## 4. Where this fits

CLS space-reservation pairs with `responsive-container-queries` sizing; INP
timing and any feedback animation defer to `motion-design-principles` for
duration and easing. Bake these in while building — retrofitting Web Vitals after
a component ships is far more expensive.

## Sources

Adapted from:
- https://web.dev/articles/inp
- https://web.dev/articles/defining-core-web-vitals-thresholds
- https://web.dev/articles/cls
