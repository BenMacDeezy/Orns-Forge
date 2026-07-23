---
name: cinematic-hero-sections
description: Build video-background and scroll-scrubbed "cinematic" hero sections that stay fast — the hero is usually the LCP element and the first impression, so autoplay rules, poster-as-LCP, reduced-motion, mobile/data budgets, and canvas frame-sequence scrubbing are the craft. Use when building a hero with a background video loop, a scroll-driven video/image-sequence narrative (the "Apple product page" effect), or a full-bleed cinematic header. Pairs with gsap-scrolltrigger (scrub choreography) and ai-generated-media-pipeline (where the asset comes from). Triggers on "hero video", "background video", "scroll-scrubbed video", "cinematic hero", "video header", "frame sequence scroll", "scrollytelling hero".
---
<!-- last-verified: 2026-07 -->

# Cinematic hero sections

The hero is the **highest-stakes performance surface on the page**: it's almost
always the LCP element, it's the first paint the user judges you by, and a
naïve video hero is the single easiest way to ship a 10 MB, 4-second, INP-killing
first impression. Every rule here is about getting the cinematic effect *without*
paying for it in Core Web Vitals (cross-ref `core-web-vitals-for-ui`).

**First decide the effect is worth a video at all.** A short seamless loop, a
scroll-scrubbed sequence, a WebGL scene (`webgl-react-three-fiber`), and a static
poster with CSS motion are four very different weight classes. Don't reach for
video where a poster + CSS gradient/parallax reads the same at 1% of the bytes.

## 1. Background-video hero

```html
<div style="aspect-ratio: 16/9">            <!-- reserve space → no CLS -->
  <video autoplay muted loop playsinline preload="none"
         poster="/hero-poster.avif" aria-hidden="true">
    <source src="/hero.av1.webm" type="video/webm; codecs=av01" />
    <source src="/hero.h264.mp4"  type="video/mp4" />
  </video>
</div>
<h1>Real DOM headline over the video</h1>       <!-- not baked into the clip -->
```

- **`muted` + `playsinline` are mandatory** — mobile browsers block autoplay
  otherwise, and without `playsinline` iOS goes fullscreen. Never rely on audio.
- **The poster is the LCP element, not the video.** Ship an optimized
  `poster` (AVIF/WebP) so first paint is instant; let the video decode and start
  *after*. `preload="none"` (or `metadata`) keeps the clip off the critical path.
- **Offer AV1/WebM first, H.264 MP4 fallback** — AV1 is a fraction of the size
  where the audience/CDN supports it; MP4 guarantees playback everywhere.
- **`prefers-reduced-motion: reduce` → don't autoplay.** Show the poster still.
  Same for **Save-Data / slow connection** (`navigator.connection`), and
  strongly consider **poster-only on mobile** (battery + data + heat).
- **The headline/CTA is real DOM text over the media** — never burned into the
  clip. Add a scrim/overlay so text hits contrast (`accessibility-wcag-aria`)
  even on a bright frame. Decorative video gets `aria-hidden`.

## 2. Scroll-scrubbed hero (the "product page" effect)

Two techniques — know which you're using and why:

- **Drive `video.currentTime` from scroll progress** — simplest, but seeking is
  expensive and stutters unless the clip is encoded with **dense keyframes**
  (small GOP), and it's unreliable on mobile. Acceptable for a short, low-stakes
  scrub; not for a flagship.
- **Frame sequence on a `<canvas>` (recommended for flagship)** — export the
  clip to N compressed frames (AVIF/WebP), preload them, and draw the frame that
  matches scroll progress. This is the technique high-end product pages use: it's
  smooth, seekable instantly, and immune to codec seek cost. The tradeoff is
  **memory and preload** — frame count × frame size is real, so cap the count,
  resize frames to display resolution, and lazy-load/unload the set as the hero
  enters/leaves the viewport.

Choreograph progress with **GSAP ScrollTrigger** (pin + scrub) rather than a
hand-rolled scroll handler — see `gsap-scrolltrigger`. Under reduced motion,
**skip the scrub**: jump to one representative frame and let the section be
static.

## 3. Budgets & checklist

- **Weight**: a background loop should be tens-of-KB poster + a few-hundred-KB
  clip, not multi-MB. A frame sequence: bounded, resized, compressed.
- **CLS**: always reserve the media box with `aspect-ratio`.
- **LCP**: poster optimized and eagerly painted; video/sequence deferred.
- **INP**: don't decode/scrub on the main thread during interaction; lazy-init
  below-the-fold heroes.
- **Fallback**: everything must read with the media failed or blocked — poster +
  DOM text carry the meaning.

Where the clip/poster/frames actually come from (AI generation + web encoding)
is `ai-generated-media-pipeline`. Motion *taste* defers to
`motion-design-principles`.

## Sources

Adapted from:
- https://web.dev/articles/lcp (poster-as-LCP, deferring media)
- https://web.dev/articles/autoplay (muted/playsinline autoplay rules)
- https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/currentTime
- https://gsap.com/docs/v3/Plugins/ScrollTrigger/ (scrub/pin)
