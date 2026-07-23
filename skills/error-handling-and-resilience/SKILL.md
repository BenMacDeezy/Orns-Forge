---
name: error-handling-and-resilience
description: Build error handling, retries, timeouts, and resilience patterns into a change — the constructive counterpart to silent-failure hunting during review. Use when adding error handling, a retry, a timeout, a circuit breaker, or any code that calls an external service, queue, or dependency that can fail. Triggers on error handling, retry, timeout, resilience, circuit breaker, exception, failure path, external call.
---

# Error handling & resilience

`pr-review-toolkit:silent-failure-hunter` catches swallowed errors at review
time. This skill is the constructive counterpart — build the failure paths
correctly the first time so there's nothing for that hunter to find.

## 1. Error taxonomy

Classify every error before deciding how to handle it — the right response
differs by kind:

- **Programmer error** (bug): null deref, type mismatch, violated invariant.
  Not retryable, not the user's fault. Fail loud (throw/crash the request),
  log with full context, fix the code — never paper over with a try/catch
  that swallows and continues.
- **Operational error**: network blip, timeout, dependency down, resource
  exhausted. Expected to happen in a running system. Retryable if the
  operation is idempotent (§3), otherwise surfaced as a clear failure.
- **User-facing error**: bad input, missing permission, business-rule
  violation (insufficient funds, duplicate resource). Not a bug — return a
  clear error to the caller (see `api-design-rest-graphql`'s error envelope
  and status codes), don't log it as a system fault.

## 2. No-swallow rules

- **Never catch-and-continue without handling.** An empty `catch {}` or a
  catch that only logs and moves on is a silent failure waiting to be
  discovered in production, not in review.
- **Rethrow with context**, don't rethrow bare. Wrap the original error with
  what you were doing when it happened (`"failed to charge order 4521: " +
  err`) — the raw stack trace alone rarely tells the next debugger what
  operation was in flight.
- If you genuinely intend to ignore an error (a best-effort cleanup, a
  non-critical metric emit), say so explicitly in the code — a comment
  naming *why* it's safe to ignore, not a bare empty catch that looks
  identical to a bug.

## 3. Retries: only on idempotent operations

Retrying a non-idempotent write (see `api-design-rest-graphql` §5 on
idempotency keys) can duplicate the effect — a retried "charge $50" without
an idempotency key can charge twice. Retry only:

- Reads (always safe).
- Writes that are idempotent by construction (PUT, DELETE) or protected by
  an idempotency key.
- Never retry blind on a POST without one.

When you do retry:

- **Exponential backoff** — delay doubles (or similar factor) each attempt,
  not a fixed interval; a fixed-interval retry storm from many clients
  synchronizes into a thundering herd against the recovering dependency.
- **Jitter** — randomize the backoff so concurrent retriers don't
  synchronize their attempts even with exponential backoff.
- **Cap** — a max attempt count or max total wait; unbounded retry is a
  silent infinite hang from the caller's perspective.

## 4. Timeouts on every outbound call

No outbound call — HTTP, DB query, queue publish, cache read — gets an
infinite/library-default timeout without a deliberate decision. An
unbounded call ties up a thread/connection/pool slot waiting on a dependency
that may never answer, and that stall cascades upward into every caller
waiting on you. Set an explicit timeout matched to the call's realistic
latency budget, not a generic global default copy-pasted everywhere.

## 5. Circuit breaker sketch

When a dependency is down, stop hammering it — fail fast and degrade
instead of queuing every request behind a timeout that's guaranteed to
fire.

- **Closed** (normal): requests flow through; failures are counted.
- **Open**: after failures cross a threshold in a window, stop calling the
  dependency entirely — fail immediately (or fall back, §7) for a cooldown
  period. This protects both your own threads/connections and the
  struggling dependency from added load while it recovers.
- **Half-open**: after cooldown, let a small number of probe requests
  through; if they succeed, close the circuit (resume normal traffic); if
  they fail, reopen and restart the cooldown.

Pair a circuit breaker with the timeout (§4) it wraps — a breaker around a
call with no timeout still lets one hung request tie up a thread before the
breaker even sees the failure.

## 6. Idempotency for at-least-once delivery

Queues, webhooks, and most retry mechanisms guarantee **at-least-once**
delivery, never exactly-once. Any handler on the receiving end of one of
these must be idempotent — processing the same message/event twice produces
the same end state as processing it once (dedupe by event id, upsert
instead of insert, check-then-skip on an already-applied marker). Design
this in up front; retrofitting idempotency after a duplicate-processing bug
in production is far more expensive.

## 7. Graceful degradation patterns

- **Feature-flag fallback**: wrap a risky/new dependency call behind a flag
  that can disable it independently of a deploy, falling back to prior
  behavior or a reduced feature set.
- **Stale-cache serve**: when a dependency backing a read is down, serve the
  last-known-good cached value (clearly labeled as possibly stale if
  user-visible) rather than a hard failure — appropriate for read paths
  where slightly-stale beats unavailable. Never do this for a write or a
  security-relevant check (auth, balance) where staleness is unsafe.
- Degrade the specific feature that depends on the failing thing — don't let
  one dependency's outage take down unrelated functionality that doesn't
  need it.

## Before you ship — checklist

- [ ] Every catch either handles the error or rethrows with context — none swallow silently
- [ ] Every outbound call has an explicit timeout
- [ ] Retries exist only on idempotent operations, with backoff + jitter + a cap
- [ ] A dependency-down path fails fast or degrades gracefully — it doesn't hang
- [ ] At-least-once handlers (queue consumers, webhook receivers) are idempotent
- [ ] User-facing errors return a clear message; internal errors don't leak stack traces/internals
- [ ] The failure path has been exercised (test or manual), not just the happy path
