---
name: api-design-rest-graphql
description: Design, add, or review an API endpoint — resource modeling, HTTP status discipline, error envelopes, versioning, pagination, idempotency, rate limiting, and GraphQL schema/resolver design. Use when designing/adding/reviewing a REST resource, a GraphQL schema or resolver, pagination, rate limiting, or a webhook contract.
---

# API design: REST & GraphQL

An API is a contract with every caller you'll never meet. Design the contract
before writing the handler — retrofitting pagination, versioning, or error
shape onto a shipped endpoint breaks every existing consumer.

## 1. Resource modeling (REST)

- Model **nouns**, not actions: `/orders`, not `/getOrders` or `/createOrder`.
  The HTTP verb carries the action.
- Collections are plural (`/users`), a single resource is the collection +
  identifier (`/users/42`). Nest only for true ownership (`/users/42/orders`),
  never to express a query — query params do that (`/orders?userId=42`).
- Keep resource shape stable across an endpoint's lifetime; add fields, don't
  repurpose them.

## 2. HTTP status discipline

| Code | Use for |
|---|---|
| 200 | Success with body |
| 201 | Created — return the resource + `Location` header |
| 202 | Accepted — async processing started |
| 204 | Success, no body (e.g. DELETE) |
| 400 | Malformed request (client's fault, fixable by changing the request) |
| 401 | No/invalid credentials |
| 403 | Authenticated but not authorized |
| 404 | Resource doesn't exist (or, deliberately, exists but hidden from this caller) |
| 409 | Conflict — state clash (duplicate create, version mismatch) |
| 422 | Semantically invalid (well-formed but violates business rules) |
| 429 | Rate limited — pair with `Retry-After` |
| 500 | Unhandled server fault — never leak internals in the body |
| 503 | Dependency down / overloaded — pair with `Retry-After` where known |

Never return 200 with an error payload — status codes are how callers branch
without parsing the body.

## 3. Error envelope + versioning

Every error response shares one shape, project-wide:

```json
{ "error": { "code": "ORDER_NOT_FOUND", "message": "human-readable", "details": {} } }
```

`code` is a stable machine-matchable string (callers branch on it, not on
`message` — message can change wording without breaking clients). Never leak
stack traces, SQL, or internal paths in `message`.

**Versioning**: pick one scheme and apply it uniformly — URI (`/v1/orders`,
simplest, most visible) or header-based (`Accept: application/vnd.api+json;version=1`,
cleaner URIs, harder to discover). Bump the major version only for breaking
changes; additive fields never require a version bump (§6).

## 4. Pagination: cursor vs offset

- **Offset** (`?limit=20&offset=40`): simple, supports jumping to a page
  number, but breaks under concurrent writes (items shift between pages,
  causing skips/dupes) and gets slower as offset grows (the DB still scans
  past the skipped rows). Fine for small, rarely-mutated, admin-facing lists.
- **Cursor** (`?limit=20&cursor=<opaque-token>`): stable under concurrent
  writes, consistent performance regardless of position, but no random page
  access — only next/prev. Default choice for any public, high-traffic, or
  frequently-mutated collection (feeds, activity logs, large tables).
- Encode the cursor opaquely (base64 of the sort key + tiebreaker id) — never
  let it leak an internal offset or become part of the contract.

## 5. Idempotency keys on non-idempotent writes

GET/PUT/DELETE are idempotent by definition; POST is not — a retried POST
(client timeout, network blip) can double-create. Require an
`Idempotency-Key` header on POSTs that cause a side effect the caller might
retry (payments, order creation, sends). Server stores `(key → result)` for
a bounded window; a retried request with the same key returns the original
result instead of repeating the effect. This is the mechanism
`error-handling-and-resilience`'s retry rule depends on — retries are only
safe once idempotency is real, not assumed.

## 6. Rate limiting

- **Token bucket** is the standard algorithm: bucket refills at a fixed rate,
  each request consumes a token, burst is bounded by bucket size — smoother
  than fixed-window counters, which allow a 2x burst at window boundaries.
- Return standard headers on every response, not just on 429s:
  `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- On limit exceeded: `429` + `Retry-After` (seconds or HTTP-date). Never
  silently drop or slow-walk the request instead.

## 7. Webhooks (server → external caller)

- Sign every payload (HMAC over the raw body) and document the header the
  receiver verifies it against — an unsigned webhook is spoofable.
- Deliveries are at-least-once: include an `event_id` so receivers can
  dedupe, and make the receiver-side handler idempotent (§5's discipline,
  now on the other side of the wire).
- Retry with backoff on non-2xx (see `error-handling-and-resilience`), cap
  attempts, and expose a way to inspect/replay failed deliveries.

## 8. GraphQL specifics

- **N+1 is the default failure mode**: a list query naively resolving each
  child field triggers one query per item. Fix with **DataLoader**-style
  batching — collect requested ids within a tick, issue one batched fetch,
  resolve individual promises from the batch result.
- **Depth and complexity limits** are mandatory on any public schema: an
  unbounded nested query (`friends { friends { friends { ... } } }`) is a
  denial-of-service vector. Enforce a max query depth and a cost/complexity
  budget per request, reject over-budget queries before execution.
- **Schema evolution is additive-only**: add new fields/types freely;
  **deprecate, don't remove** — mark with `@deprecated(reason: "...")` and
  keep serving the old field until consumers have migrated. Removing a field
  is a breaking change with no version escape hatch in GraphQL (there's one
  schema, not `/v1` and `/v2`).

## Contract-first checklist

Run this before implementing any new endpoint or resolver:

- [ ] Resource/operation named as a noun (REST) or fits existing schema types (GraphQL)
- [ ] Success + every realistic error path mapped to a status code / error code
- [ ] Error envelope matches the project-wide shape
- [ ] Pagination strategy chosen deliberately (cursor default; offset only if justified)
- [ ] Non-idempotent writes have an idempotency-key path
- [ ] Rate limit applies and returns standard headers
- [ ] Breaking vs additive change classified; version bumped only if breaking
- [ ] (GraphQL) new resolvers batch via DataLoader; depth/complexity budget still holds
- [ ] Auth/authz requirement stated explicitly, not assumed from routing
