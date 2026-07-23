---
name: mem-f4d2a9
description: Next.js App Router — notFound() (and other access-fallback throws) after an async fetch returns HTTP 200 instead of 404 when a parent Suspense/loading boundary commits the streamed response head first; run the existence check outside any loading boundary (route groups) so it bubbles before the shell flushes
type: gotcha
created: 2026-07-19T01:30:00Z
updated: 2026-07-19T01:30:00Z
superseded-by: null
schema-version: 1
agents: forge-debugger, forge-worker, forge-ui
---

Promoted from project fact nextjs-notfound-200-under-suspense (Next.js App Router). Applies to any Next.js App Router repo.

notFound() sets a 404 status ONLY when its error propagates out of the
render before the shell is committed (the catch around Fizz stream in
app-render.js). If the page suspends on an async fetch under a parent
Suspense boundary — its own loading.tsx or a shared ancestor
app/loading.tsx — Next streams the fallback, commits the head as 200,
and the later notFound() is absorbed by the segment access-fallback
boundary, never reaching the 404-setting catch. Reproduce/confirm with a
curl matrix (remove loading boundaries -> 404 returns).

Fix: the existence check must run OUTSIDE any Suspense boundary. Route
groups so the route has no ancestor loading.tsx; await the check at the
top of page.tsx; stream a skeleton for the FOUND case via an in-page
<Suspense> BELOW the notFound gate. Verify HTTP status with curl/fetch —
RTL renders the component and cannot observe the response status.
