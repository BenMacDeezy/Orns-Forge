---
name: mem-a3f2e8
description: Next.js next/script beforeInteractive is queue-deferred, not pre-paint — pre-paint work (no-FOUC theming) needs a raw synchronous inline <script> with a static string; prove with frame capture under CPU throttle, unit tests are blind to paint timing
type: gotcha
created: 2026-07-18T10:59:43Z
updated: 2026-07-18T10:59:43Z
superseded-by: null
schema-version: 1
agents: forge-ui, forge-ui-verifier
---

Promoted from project fact `nextjs-beforeinteractive-not-prepaint`
(observed in a Next.js App Router project).

next/script `strategy="beforeInteractive"` does NOT execute before first
paint: Next emits it as a `self.__next_s.push(...)` queue entry after
<body> opens, and the queue drains only when an async framework runtime
chunk finishes loading. Under CPU throttle >=2x the page fully paints
the default state first, then flips (reproduced 6/6 via CDP screencast).
A green unit-test suite is structurally blind to this failure class.

How to apply, in any Next.js repo:
- Anything that must run pre-paint (theme/density stamping) goes in a
  raw <script> element (no src/async/defer) rendered via
  dangerouslySetInnerHTML with a COMPILE-TIME-CONSTANT string — never
  interpolate request/cookie-derived data — inside an explicit <head>
  in the root layout. Parser-inserted classic scripts run synchronously
  before <body> parses; Next's injected meta/async-chunk tags ahead of
  it don't block the parser.
- Verify paint-timing claims empirically: production build, CPU
  throttle >=2x, frame-by-frame capture (CDP screencast) — never by
  unit tests or code reading.
