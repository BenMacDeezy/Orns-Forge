---
name: backend-scaling-architecture
description: Design or review backend scalability before demand becomes an outage — horizontal-first services, background work, load shedding, capacity planning, load tests, replicas, shards, and edge tiering. Triggers on scale, scalability, load test, rate limit, queue/background job, replica, shard, capacity, or "will this handle N users".
---

# Backend scaling architecture

Scale is not an architecture you install after launch. Keep the request path
simple, measure its limiting resource, and choose the cheapest change that
raises that limit before distributing state or data across more machines.

Scope: this skill owns topology, workload placement, admission control, and
capacity decisions. `backend-caching-and-performance` owns cache mechanics
and hot-path tuning; `database-schema-and-migrations` owns schema, indexes,
and query plans; `error-handling-and-resilience` owns retry/fallback
mechanics; `api-design-rest-graphql` owns endpoint contracts; and
`observability-logging-metrics-tracing` owns the evidence used to decide.

## 1. Measure the bottleneck before changing architecture

- **Do not scale a hypothesis.** Name the saturated resource with evidence:
  CPU, memory, database connections, a lock, disk I/O, network, dependency
  quota, or queue lag. A request rate alone is not a bottleneck.
- Establish the current and target workload, latency SLO, error budget, and
  headroom before proposing replicas, queues, or shards. “Handle 100k users”
  is incomplete without active concurrency, request mix, payload size, and
  peak-versus-average traffic.
- Use `observability-logging-metrics-tracing` to correlate RED/USE signals
  with traces, and `backend-caching-and-performance` to profile the proven
  hot path. Re-run the same measurement after a change.
- Apply the **one-big-instance-first rule**: if one larger instance satisfies
  the measured target with safe headroom, scale up first. It has fewer moving
  parts than a distributed fleet. Scale out when availability, isolation, or
  one machine's real limit requires it — not merely because horizontal scale
  sounds more mature.

## 2. Horizontal-first request services

- Make request handlers **stateless**: any healthy instance can serve the
  next request. Put sessions, uploads, coordination state, and durable work
  outside process memory in the appropriate shared store.
- Never require sticky sessions merely to preserve in-memory application
  state. Stickiness can be a temporary compatibility bridge, not the design;
  it skews load and makes replacement instances unsafe.
- Keep configuration in environment-driven config or the platform's managed
  configuration, not baked into an image or changed manually on one node.
  Validate required config at startup and keep secrets in the existing secret
  store rather than logs or source control.
- Make externally retriable handlers idempotent. For side-effecting writes,
  use an idempotency key or durable dedupe marker; see
  `api-design-rest-graphql` §5 for the HTTP contract.
- On shutdown, stop accepting new work, fail readiness, drain in-flight
  requests within a bounded grace period, then close listeners and clients.
  Treat SIGTERM/deployment termination as normal operating behavior, not an
  abrupt crash. A process that accepts work until it is killed creates
  avoidable retries and duplicate side effects during every rollout.

## 3. Put work in the right execution model

Choose by delivery and timing semantics, not by which tool is already in the
repository:

| Need | Choose | Rule |
|---|---|---|
| User needs a bounded answer now | Synchronous request work | Keep only work inside the request's latency budget. |
| Durable, independent work after a command | Job queue | Acknowledge the command, then process asynchronously. |
| A schedule with no per-event durability requirement | Cron/scheduled job | Make overlapping runs safe; record the last successful run. |
| Multiple consumers need an ordered stream of facts | Event stream | Publish immutable events; consumers maintain their own progress. |

- A queue is not a faster request handler. Use it for work that can complete
  later, survive process restarts, and be observed through queue lag.
- Write the state change and the “publish this job/event” intent atomically
  with an **outbox** record. A separate publisher relays that record after
  commit. Never commit business data and hope a best-effort publish succeeds
  afterward — that creates lost work on the crash boundary.
- Assume at-least-once delivery for queues and streams. Every consumer needs
  an idempotency key/event id plus a durable processed-result or dedupe path.
  “Exactly once” claims do not remove duplicate effects at the boundary.
- Retry transient failed jobs with capped exponential backoff and jitter; send
  exhausted or invalid jobs to a dead-letter queue with failure context and a
  named owner/replay path. `error-handling-and-resilience` owns the detailed
  retry and fallback mechanics; this skill decides that the work belongs off
  the request path and must not amplify overload.
- Do not use cron as a queue: it has weak per-item retry/visibility semantics.
  Do not use a stream as a cron replacement: a stream needs consumers and
  retained events, not just “run this nightly.”

## 4. Protect capacity before adding it

- Rate-limit at the earliest enforceable boundary. Use **per-user, per-token,
  or per-tenant** limits to prevent one caller from consuming a fair share;
  add a **global** limit to preserve the service when aggregate demand exceeds
  capacity. Keep auth/login and expensive endpoints on tighter, separate
  budgets.
- Use a **token bucket** when bounded bursts are acceptable: tokens refill at
  a steady rate and bucket capacity defines the burst. Use a **sliding
  window** when a strict recent-period count matters. Fixed windows are cheap
  but allow boundary bursts; choose them only knowingly.
- Return a prompt overload response (normally 429 or 503 with `Retry-After`)
  instead of letting every request occupy a scarce thread, connection, or
  queue slot. Preserve essential traffic with priority classes if the product
  has a real definition of essential.
- Apply backpressure: bound queues and concurrency, propagate “not ready” to
  producers, and reject/defer before memory grows without limit. An unbounded
  in-memory queue converts a short spike into an eventual OOM.
- Circuit breakers and timeouts are admission controls here: open a boundary
  when continued calls worsen saturation, and fail fast so capacity remains
  for healthy work. `error-handling-and-resilience` owns how a breaker,
  fallback, and retry are implemented; this skill owns the decision to shed
  traffic rather than scale a failing dependency.
- Treat timeout as a **budget**, not one copied constant. Split the caller's
  deadline across queueing, application work, and downstream calls; each
  child deadline must leave time for its caller to respond. Do not launch work
  that cannot finish before the request's remaining budget.

## 5. Find the knee of the curve with load tests

- Test realistic traffic mix, data size, and concurrency before the launch or
  capacity event. Name tools generically; a load-test runner such as k6 or
  Locust is useful only when its scenario matches production behavior.
- A **closed workload** holds a fixed number of virtual users: each sends the
  next request after receiving the last response. It models user think-time
  and hides overload by reducing offered load as latency rises.
- An **open workload** sends requests at an independent arrival rate. It
  exposes queueing and saturation under a target RPS, but needs a realistic
  arrival profile and a clear overload policy. Use both when their questions
  differ; never report one as universal capacity.
- Report p50, p95, p99, error rate, saturation, and throughput — never only
  averages. The knee is where added load causes tail latency or errors to
  rise sharply, not where a mean first looks inconvenient.
- Avoid **coordinated omission**: a client that waits for a slow response
  before issuing the next request under-samples the delays users experienced.
  Record scheduled versus actual start times or use an open-arrival test to
  expose the missing waits.
- Repeat the test with one changed variable at a time and retain the scenario,
  dataset shape, version, and results. A capacity number without its workload
  model cannot be safely reused.

## 6. Size shared limits, especially database connections

- Work from the database's usable `max_connections`, reserving capacity for
  administration, migrations, and other services. Do not set every instance
  pool to the database maximum.
- First approximation: total possible application connections is roughly
  `pool size × instance count` (or `threads × instances` when each thread can
  hold a connection). Keep that total below the usable database budget with
  headroom. Scaling application instances without lowering per-instance pools
  can exhaust the database before CPU reaches 20%.
- A pool is a concurrency limit, not a throughput dial. Size it from measured
  query latency and DB concurrency, set an acquisition timeout, and inspect
  waiting time. `database-schema-and-migrations` owns the pool fundamentals
  and query/index fixes; this skill owns fleet-wide allocation.

## 7. Tier data deliberately

- Put static assets and genuinely cacheable GET responses at a CDN/edge tier
  when sharing and invalidation semantics permit it. This is a topology
  decision that removes origin load; `backend-caching-and-performance` owns
  cache keys, TTLs, invalidation, and stampede protection.
- Add read replicas only after the primary is proven read-bound and the read
  path tolerates replica semantics. Replication lag means a write followed by
  a replica read can look missing or stale; route read-your-writes, auth,
  balances, and consistency-sensitive flows to the primary or a verified
  consistent path.
- Shard only when one well-indexed primary can no longer meet measured data,
  write, storage, or isolation needs after simpler options. Sharding is
  almost never an early optimization: it adds routing, cross-shard queries,
  rebalancing, backup, and operational failure modes.
- Before sharding, exhaust a better query/index, archival/retention,
  partitioning where supported, vertical capacity, replicas for safe reads,
  and workload separation. Choose a shard key only with an explicit plan for
  skew, hot tenants, and resharding.

## 8. Cheapest fix first

| Symptom | Cheapest fix first | Escalate only when measured |
|---|---|---|
| Slow query | Inspect `EXPLAIN`, correct query/index | Replica or shard |
| CPU-bound service | Profile and remove hot work; scale up | More instances |
| Database connection exhaustion | Bound/rebalance pools across instances | Larger DB or proxy layer |
| Brief traffic burst | Token bucket, queue bounded async work | Permanent fleet growth |
| Slow static/cacheable GETs | Edge/CDN tiering | More origin instances |
| Primary read saturation | Fix hot reads; cache/tier safe reads | Read replicas |
| Growing table/storage | Retention, archive, partition | Sharding |
| Dependency outage/overload | Shed, backpressure, fail fast | More callers/retries |

**Restraint rule:** do not introduce replicas, shards, a queue, or a new
service merely because growth is plausible. Record the measured bottleneck,
the rejected cheaper fix, the expected headroom, and the rollback/removal
path before adding distributed architecture.

## Before you ship — checklist

- [ ] Target workload, SLO, headroom, and measured bottleneck are written down
- [ ] A one-big-instance option was evaluated before horizontal complexity
- [ ] Request services are stateless, idempotent where retried, and drain safely
- [ ] Background work has durable intent, idempotent consumers, bounded retry, and DLQ ownership
- [ ] Limits, backpressure, and timeout budgets protect essential capacity
- [ ] Load test reports workload model, p95/p99, errors, saturation, and knee
- [ ] Fleet-wide connection totals fit the database budget with headroom
- [ ] Replica lag and edge-cache consistency are safe for each routed flow
- [ ] Any shard proposal documents why simpler options failed and how it rebalances
