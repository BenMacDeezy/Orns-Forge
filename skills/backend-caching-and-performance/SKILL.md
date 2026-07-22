---
name: backend-caching-and-performance
description: Diagnose or fix backend latency and throughput — profiling before optimizing, cache layer design, invalidation and stampede protection, query caching scope, pagination over unbounded loads, and connection pooling. The backend analog of core-web-vitals-for-ui. Triggers on slow endpoint, performance, caching, latency, optimize backend, load.
---

# Backend caching & performance

The backend analog of `core-web-vitals-for-ui`: latency and throughput are
build constraints, not a post-launch tuning pass. Measure before you touch
anything — a guessed optimization that isn't the actual bottleneck is wasted
work and new complexity for no gain.

## 1. Measure before optimizing

- **Profile, don't guess.** Use the language/runtime's profiler, DB
  `EXPLAIN ANALYZE` (`database-schema-and-migrations` §3), or request
  tracing (`observability-logging-metrics-tracing` §4) to find the actual
  hot path before changing code. "This looks slow" is a hypothesis, not a
  finding — confirm it with a number.
- Reproduce the slow case with realistic data volume and concurrency — a
  query that's fast against 100 local rows can be a seq scan against 10M
  production rows, and a handler that's fast single-threaded can contend
  under real concurrent load.
- After the fix, re-measure the same way you measured the problem. A fix
  that "should" help but wasn't re-verified isn't confirmed.

## 2. Cache layers

Three layers, cheapest/fastest to most shared, each trading locality for
scope:

- **In-process** (local memory, e.g. an LRU map): fastest, zero network
  hop, but not shared across instances — each process has its own copy,
  and it's lost on restart/deploy.
- **Distributed** (Redis/Memcached-class): shared across instances, survives
  individual process restarts, but adds a network hop and its own
  failure/latency mode — treat it as an outbound dependency needing a
  timeout and a fallback path (`error-handling-and-resilience` §4, §7).
- **HTTP** (CDN / reverse-proxy / browser cache via `Cache-Control`): the
  widest-scope, cheapest-per-request layer for cacheable responses — closest
  to the caller, offloads the most load from your backend, but only fits
  responses that are safe to share across requests/users (or explicitly
  keyed per-user with proper `Vary`).

Pick the layer(s) by scope needed, not by habit — reaching for Redis for
data only one process ever touches adds a network hop for nothing.

## 3. The two hard problems

**Invalidation** — how a cached value stops being served once it's stale:

- **TTL** (time-to-live): simplest, bounds staleness by a fixed window,
  costs nothing to implement, but is a guess — too short wastes the cache,
  too long serves stale data.
- **Event-driven**: invalidate explicitly when the underlying data changes
  (on write, publish an invalidation). Precise, but requires every write
  path to remember to invalidate — a missed path is a silent staleness bug.
- **Versioned keys**: bake a version/generation number into the cache key
  itself (`user:42:v7`); bumping the version orphans old entries without
  deleting them (they age out via normal eviction). Sidesteps
  race-on-delete entirely — no window where a delete and a concurrent read
  can disagree about whether the old entry still exists.

**Stampede protection** — many requests missing the cache simultaneously
(on expiry or a cold cache) and all hammering the origin at once:

- **Jittered TTL**: randomize each entry's TTL slightly so entries cached at
  the same time don't all expire in the same instant.
- **Single-flight**: when multiple concurrent requests miss the same key,
  let exactly one fetch the origin and populate the cache; the rest wait on
  that one in-flight fetch instead of each issuing their own origin call.

## 4. Query caching & memoization scope

Cache/memoize at the narrowest scope that's actually safe:

- **Per-request memoization** (a value computed once and reused within a
  single request) is nearly always safe — no cross-request staleness risk.
- **Cross-request caching** needs an explicit invalidation strategy (§3) —
  never cache a query result "because it's slow" without deciding how it
  gets invalidated when the underlying data changes.
- Never cache a value scoped to one user/tenant under a key that doesn't
  include their id — that's a data leak between users disguised as a
  performance win.

## 5. Pagination and streaming over unbounded loads

Never load an unbounded result set into memory — a query with no `LIMIT`
against a table that grows over time is a latency regression waiting to
happen as the table grows, and a memory-exhaustion risk on a large-enough
table today. Paginate (`api-design-rest-graphql` §4) any list endpoint, and
stream (row-by-row / chunked) rather than materializing-then-returning for
bulk exports or large aggregations.

## 6. Connection pooling reuse

Reuse pooled connections (DB, Redis, HTTP clients to other services) — see
`database-schema-and-migrations` §6 for sizing. The performance angle here:
un-pooled connections add handshake latency to every single call, which
compounds badly under load exactly when you can least afford it.

## 7. p95/p99 over averages

An average hides the experience of your worst-served users. A handler
averaging 80ms with a p99 of 4s means 1% of requests wait 4 full seconds —
invisible on an average-latency dashboard, very visible to the user who hit
it. Track and alert on p95/p99 (or higher, for very high-traffic endpoints),
not just mean latency, and treat a growing p99-to-average gap as a signal of
an emerging tail-latency problem (lock contention, GC pauses, a slow-path
branch) even while the average still looks fine.
