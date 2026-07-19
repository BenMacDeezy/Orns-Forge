---
name: database-schema-and-migrations
description: Design a database schema, write or run a migration, add an index, or diagnose a slow query. Covers normalization/denormalization, indexing strategy, reading EXPLAIN output, zero-downtime expand-contract migrations, N+1 detection, and connection pooling. Triggers on schema design, migration, index, slow query, EXPLAIN, N+1, Postgres.
---

# Database schema & migrations

Data is the part of the system you cannot roll back with `git revert`. Design
for the write path you'll regret in a year, not just the query you need today.

## 1. Normalize by default; denormalize on evidence

Start normalized (3NF: no repeated groups, every non-key column depends on
the whole key, nothing but the key). Denormalize only when you have a
specific, measured reason:

- A read path is proven hot (via EXPLAIN or slow-query logs, §3) and the join
  cost is the bottleneck.
- The duplicated data is effectively immutable, or you've accepted an
  explicit sync strategy (trigger, event, batch job) for keeping copies
  consistent.
- Never denormalize speculatively "for performance" before measuring —
  that's premature optimization with a schema-migration cost attached.

## 2. Indexing strategy

- Index columns used in `WHERE`, `JOIN ON`, and `ORDER BY` — not every
  column "just in case." Every index costs write throughput and disk.
- **Composite index column order matters**: put the equality-filtered column
  first, range-filtered/sorted columns after. An index on `(a, b)` serves
  `WHERE a = ? AND b = ?` and `WHERE a = ? ORDER BY b`, but not efficiently
  for `WHERE b = ?` alone.
- **Covering indexes** (include all columns a query needs) let the planner
  answer straight from the index without touching the table — worth it for
  hot, narrow read paths.
- **When NOT to index**: low-cardinality columns (booleans, small enums)
  rarely help alone; tables with heavy write volume and few reads pay the
  index-maintenance cost for little benefit; don't index a column purely
  because it appears in a `SELECT` list.

## 3. Reading EXPLAIN output

Run `EXPLAIN ANALYZE` (Postgres) on any query you're not sure about before
guessing at a fix.

- **Seq Scan on a large table** where you expected an index scan — either
  the index is missing, the planner's cost estimate favors the scan anyway
  (small table, low selectivity), or a function/type mismatch on the
  filtered column prevents index use (e.g. filtering `date_col::text`
  instead of a native date comparison).
- **Misestimated row counts** (`rows=10` estimated vs `rows=100000` actual,
  or vice versa) mean stale statistics — `ANALYZE` the table — or a
  correlated filter the planner can't model, which may need a different
  index shape or a rewritten query.
- **Nested Loop over a large outer set** is usually the N+1 pattern showing
  up inside a single query plan — often fixable with a hash/merge join hint
  via better indexing, or by restructuring the query.
- Read cost top-down: the outermost node's total cost/time is what the
  caller waits for; drill into whichever child node contributes most of it.

## 4. Zero-downtime migrations: expand → migrate → contract

Never combine a schema change with the deploy that stops using the old
shape — that's the single most common cause of an outage during a
migration, because old code and new code run simultaneously across a
rolling deploy.

1. **Expand**: add the new column/table/index without touching the old one.
   Nullable or defaulted; old code keeps working untouched.
2. **Dual-write / backfill**: new code writes to both old and new shape;
   backfill existing rows into the new shape in batches (not one giant
   transaction — batch to avoid long locks and huge rollback segments).
3. **Switch reads**: once backfill is confirmed complete and dual-writes are
   live, cut reads over to the new shape. Verify in production before
   proceeding.
4. **Contract**: only after reads and writes are fully on the new shape, and
   you've let it bake, drop the old column/table and stop dual-writing.

**Rule: never rename or drop a column/table in the same deploy that stops
writing to it.** A rename is a drop-and-add from the old code's point of
view — do it as expand (add new name) → dual-write → switch reads → contract
(drop old name), same four steps, never collapsed into one migration.

Every migration in this repo's convention ships with either a rollback path
(a down-migration or a documented reverse script) or an explicit
**irreversible — requires backup** flag when one isn't possible (e.g. a
`DROP COLUMN` that discards data). Never ship a migration silently missing
both.

## 5. N+1 detection

The application-layer symptom of missing batching: one query to fetch a
list, then one additional query per item to fetch each item's related data.
Detect it by counting queries per request (most ORMs have a query-log or
counter) — a request whose query count scales with result-set size is N+1.
Fix with eager loading (`JOIN`/`include`/`preload`, per your ORM) or
batching (DataLoader-style, same pattern as the GraphQL resolver case in
`api-design-rest-graphql`).

## 6. Connection pooling basics

- Never open a new connection per request — pool and reuse. Connection
  setup (TCP + auth handshake) costs real latency and the database has a
  hard max-connections ceiling.
- Size the pool to the database's actual capacity divided across app
  instances, not to "however many the app wants" — an oversized pool just
  moves the bottleneck to the database running out of connections under
  load from multiple app instances simultaneously.
- Set a connection acquisition timeout — a pool waiting forever for a free
  connection turns a slow query into a cascading stall (see
  `error-handling-and-resilience`'s timeout rule; the pool is an outbound
  dependency like any other).

## Neon MCP (optional — check via ToolSearch before assuming it's present)

If a Neon MCP server is connected, prefer its tools for live schema work
over hand-written SQL exploration:

- `describe_table_schema` — inspect current shape before designing a change.
- `explain_sql_statement` — get EXPLAIN output directly instead of
  round-tripping through a psql session.
- `prepare_database_migration` / `complete_database_migration` — the
  sanctioned migration-execution path when available.
- `list_slow_queries` — starting point for §3 instead of guessing which
  query to investigate.

Phrase this as optional in any brief you write for a worker — never assume
the Neon MCP is present; fall back to raw SQL/migration files when it isn't.
