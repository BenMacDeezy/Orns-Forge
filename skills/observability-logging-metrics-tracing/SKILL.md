---
name: observability-logging-metrics-tracing
description: Add or review logging, metrics, or tracing so production behavior is diagnosable — structured logs, correlation IDs, RED/USE metrics, and OpenTelemetry spans. Use when instrumenting code, debugging a production issue, or wiring monitoring. Triggers on logging, metrics, tracing, observability, instrument, debug production, monitoring.
---

# Observability: logging, metrics, tracing

You cannot debug what you cannot see. Instrument while building — bolting on
observability after an incident means the incident that would have proven it
useful already happened without it.

## 1. Structured logging

- Emit **JSON** (or another machine-parseable structure), not free-text
  interpolated strings — `logger.info("order failed", { orderId, reason })`,
  not `logger.info("order " + orderId + " failed: " + reason)`. Structured
  fields are queryable/filterable; interpolated strings force regex
  archaeology later.
- Use **levels** deliberately: `debug` (dev-only detail), `info` (normal
  operational events worth keeping), `warn` (recoverable but noteworthy),
  `error` (something failed and needs attention). Don't log everything at
  `info` — that just trains everyone to ignore the log stream.
- **Never log secrets or PII**: passwords, API keys, tokens, full card
  numbers, SSNs, raw auth headers. Redact or omit before the log call, not
  after — a leaked secret in a log aggregator is a breach regardless of
  intent. When in doubt, log an id you can look up, not the sensitive value
  itself.

## 2. Correlation / request IDs

Generate a correlation (request) id at the system's edge — the first
service that receives an external request — and propagate it through every
downstream call: HTTP headers to other services, message metadata onto
queue publishes, into every log line for that request's lifetime. Without
it, reconstructing what happened for one failed request across multiple
services means grepping timestamps and hoping nothing else interleaved.
This is the same id that ties log lines to a trace (§4).

## 3. RED metrics (services) + USE (resources)

- **RED**, per service/endpoint: **R**ate (requests/sec), **E**rrors
  (error rate or count), **D**uration (latency — track distribution, not
  just average; see p95/p99 in `backend-caching-and-performance`). This
  triad answers "is this service healthy" at a glance.
- **USE**, per resource (CPU, memory, connection pool, disk, queue):
  **U**tilization (% busy), **S**aturation (queue depth / work waiting),
  **E**rrors (resource-level errors — OOM kills, disk errors). This
  triad answers "is this resource the bottleneck."
- Both frameworks exist so you know *which* dashboard to check first:
  RED for "is the service degraded," USE for "which resource is why."

## 4. OpenTelemetry spans for cross-service flows

A single request touching multiple services/hops needs a **trace**: a tree
of **spans**, each representing one unit of work (a handler, an outbound
call, a DB query), linked by the correlation id (§2) and parent/child
relationships. Use OpenTelemetry's SDK/conventions for your language rather
than a bespoke tracing format — the point of the standard is that traces
compose across services owned by different teams/tools without a custom
adapter per pair. Name spans after the operation, not the code path
(`"charge-payment"`, not `"PaymentService.process"` — the latter breaks the
moment you rename the class).

## 5. What to instrument — and what not to

Instrument:

- **Every external call** — HTTP to another service, DB query, cache
  read/write, queue publish/consume. Each is a potential latency/failure
  source and a span/metric boundary.
- **Every retry** — count and log it distinctly from the original attempt,
  so a retry storm is visible as a rate spike, not hidden inside a single
  "succeeded eventually" log line.
- **Cache hit/miss** — a silently degrading hit rate is one of the earliest
  signals of a capacity or invalidation problem (`backend-caching-and-performance`).
- **Queue hops** — enqueue and dequeue timestamps, so end-to-end queue
  latency is measurable, not inferred.

Do NOT instrument:

- **Per-loop-iteration noise** — a log line or span inside a tight loop over
  many items multiplies volume without adding diagnostic value; instrument
  the loop's start/end and aggregate counts instead.
- Anything that would log a secret/PII (§1) "just for debugging" — use a
  redacted id and look it up in a system that isn't the log stream.

## 6. Sentry (optional — check via ToolSearch before assuming it's present)

If a Sentry MCP server is connected, wire error capture so unhandled
exceptions (and explicitly captured operational errors from
`error-handling-and-resilience`) report with **release** and **environment**
tags set — without them, a Sentry issue can't be bisected to the deploy
that introduced it or filtered to prod-only. Tag correlation/request ids
(§2) as Sentry context so a captured error can be cross-referenced with logs
and traces for the same request. Treat this as optional: never assume a
Sentry MCP or SDK is present in a project that hasn't configured one — check
first, and degrade to plain structured error logging when it isn't there.
