---
name: ai-generated-media-pipeline
description: Turn AI-generated clips and stills into production web hero assets — generate via Higgsfield/Runway/Sora/Veo/Kling (video) and Nano Banana/Flux/Seedream (image), ideally through an MCP so the agent produces assets in-loop, then encode them web-ready (AV1/H.264, faststart, poster extraction, frame sequences) within a weight and licensing budget. Use when sourcing a hero video/background loop/scroll frame-sequence from AI tools, or preparing any generated media for the web. Feeds cinematic-hero-sections (which consumes the assets). Triggers on "Higgsfield", "Nano Banana", "AI hero video", "generate a background video", "Runway/Sora/Veo/Kling", "encode video for web", "ffmpeg hero", "loopable clip", "poster frame".
---
<!-- last-verified: 2026-07 -->

# AI-generated media pipeline

Two halves: **generate** the raw asset with an AI model, then **encode it
web-ready**. The models churn every few months; the durable value is the
encoding, budgeting, and licensing craft in §2–§4 — treat the tool names in §1
as current examples, not the skill.

## 1. Generate — prefer MCP so the agent works in-loop

Wire the generator as an **MCP server** where one exists, so an agent can produce
and iterate assets inside the build loop instead of round-tripping to a web UI.
Discover and vet options with `forge:scout` / `forge:equip`.

- **Higgsfield MCP** (cinematic image + video; proxies **Sora 2, Veo 3.1,
  Kling 3.0, Seedance** for video and **Flux, Seedream, Nano Banana Pro** for
  stills). Setup:
  `claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp`
  — browser OAuth, no API key. (MCP OAuth won't complete in headless/cron runs —
  authorize interactively first.)
- **Image/still generators**: **Nano Banana / Nano Banana Pro** (Google Gemini
  image — strong at consistent character/edits and matching an existing frame),
  Flux, Seedream, Midjourney.
- **Video generators** directly: Runway, Luma Dream Machine, Pika, plus the
  hosted models above.

**Prompt for the web, not for a demo reel:**
- Generate **at or above** the target display resolution — you can only
  downscale cleanly.
- For a **background loop**, design for seamlessness (first frame ≈ last frame,
  or request a loopable clip) and keep motion **subtle** — a busy hero fights the
  headline. Leave a calm region where DOM text will sit.
- Generate a **matching poster still** (Nano Banana) equal to the clip's first
  frame, so the `poster` and the video start are visually identical.

### Keyframe (first/last-frame) workflow — the default for hero & scroll

The controlled way to produce hero and scroll clips: **generate two stills — a
start frame and an end frame (Nano Banana, for a consistent subject) — then hand
both to the video model as keyframes and let it generate the motion between
them.** Luma, Kling, and Runway all support this image-to-video conditioning
(Luma up to 16 keyframes). It's preferred here because it gives **deterministic
endpoints**, which hero and scroll both need:

- **Seamless loop** → make the **end frame identical to the start frame**; the
  clip loops with no visible cut.
- **Scroll narrative** → the top-of-scroll and bottom-of-scroll states *are* your
  two keyframes; the model fills the middle.

Two caveats that trip people up:

- **You don't "set 30fps between two frames."** The model generates at its own
  native rate (often 24, sometimes 30) over a clip duration; conform to your
  delivery fps in **post** (FFmpeg). For **scroll-scrubbing, playback fps is
  irrelevant** — you map scroll position → frame index, so what matters is
  **frame *count***. Up-sample frames with `minterpolate`/RIFE if the scrub needs
  more.
- **Generative motion ≠ pure interpolation.** A video model *invents* real motion
  between the keyframes (what you want). Pure frame interpolation (RIFE/FILM/
  `minterpolate`) only morphs/crossfades — fine for smoothing or raising fps,
  useless for actual movement. And the more the two frames diverge, the more the
  model warps the middle: keep start/end compositionally related, or use
  single-image + motion-prompt for big camera moves.

## 2. Encode web-ready (the durable craft)

Raw generator output is almost never shippable — it's oversized, has audio you
don't want, and no fast-start. Run it through **FFmpeg** (or HandBrake):

- **Formats**: ship **AV1 (WebM)** for size where supported **+ H.264 (MP4)**
  as the universal fallback. Let `cinematic-hero-sections` list both `<source>`s.
- **Compress**: CRF or two-pass to a small target bitrate; **strip audio for a
  silent background** (`-an`); **`-movflags +faststart`** so the MP4 streams
  progressively instead of waiting for full download.
- **Right-size**: cap resolution to the display size (don't ship 4K for a 1080
  hero) and keep loops **short (3–8s)**.
- **Poster**: extract one frame (`ffmpeg -ss <t> -frames:v 1`) and compress to
  AVIF/WebP.
- **Frame sequences** (for scroll scrub): export frames, resize to display size,
  compress to AVIF/WebP, sequential names; keep the count bounded (memory).

Representative command:

```bash
ffmpeg -i raw.mp4 -an -vf "scale=1920:-2" -c:v libx264 -crf 24 \
       -movflags +faststart hero.h264.mp4
```

## 3. Weight budget

State and hold a budget: a background loop ≈ tens-of-KB poster + a
few-hundred-KB-to-~2MB clip; a frame sequence bounded by count × resized frame.
If the asset can't hit budget, it's the wrong effect — fall back to a poster +
CSS/WebGL per `cinematic-hero-sections`.

## 4. Rights, provenance, accessibility

- **Licensing is not automatic.** Commercial-use rights for AI-generated media
  vary per model's ToS — confirm before shipping, and never generate real
  people or trademarked brands. Route anything load-bearing through
  `third-party-tos-review` and `feature-legal-risk-checklist`.
- Preserve **provenance** (C2PA/metadata) where the model supplies it.
- Generated media is decorative: `aria-hidden`, and always ship the poster +
  reduced-motion path (handed to `cinematic-hero-sections`).

## Sources

Adapted from:
- https://higgsfield.ai/mcp
- https://ffmpeg.org/ffmpeg.html (encoding, faststart, frame extraction)
- https://web.dev/articles/video (web video delivery)
- https://c2pa.org/ (content provenance)
