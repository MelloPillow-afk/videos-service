# 1. Direct database connections, not Neon's pooler

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

The API and worker connect to Neon Postgres through a small `psycopg_pool` pool
([src/repositories/database.py](../../src/repositories/database.py)). Each new connection
sets three session settings as startup options:

```text
-c statement_timeout=<DB_STATEMENT_TIMEOUT_MS>
-c lock_timeout=<DB_STATEMENT_TIMEOUT_MS>
-c search_path=<DB_SCHEMA>
```

The tests depend on these options too: each test gets its own isolated schema through
`DB_SCHEMA`.

Neon offers two ways to connect:

- **Pooled** (`-pooler` host): PgBouncer in transaction mode. Many clients share a few
  real Postgres connections. It **rejects startup options** (`unsupported startup
  parameter in options: statement_timeout`) and can't keep session settings between
  transactions.
- **Direct** (no `-pooler`): every client connection is a real Postgres connection, so
  startup options work. The compute caps how many there can be (about 100 on the
  smallest size).

The first production deploy used the pooled URL, so every connection failed and every
database request returned a 500.

## Decision

Production uses Neon's **direct** connection string for the runtime user
(`videos_runtime` in the `videos-database-url` secret), and `database.py` stays as it is.

To keep the connection count bounded, the API runs with `--max-instances=10` and
`DB_POOL_MAX_SIZE=2`. Each worker execution holds one connection.

## Options considered

### A. Direct connections, no code change (chosen)

- **For:** `database.py` keeps one job, creating the pool, and knows nothing about
  PgBouncer. Timeouts and `search_path` are set once per connection, so a request makes
  no extra round trips. Test schema isolation keeps working.
- **Against:** the total connection count grows with scale-out:
  `API instances × DB_POOL_MAX_SIZE + running workers`. At 10 × 2 + a few workers, that's
  far under the limit, but heavy scale-out would eventually reach it.

### B. Set the settings per transaction (the old `988df25` fix)

Each connection checkout first runs
`SELECT set_config('statement_timeout', …, true), …` so the settings last only for that
transaction, which the pooler allows.

- **For:** works pooled or direct, and supports very high concurrency.
- **Against:** **one extra round trip on every transaction.** Cloud Run (`us-central1`)
  and Neon (`us-east-2`) are in different regions, so each round trip costs about
  20–30 ms. `connection()` stops being a plain pass-through to the pool and has to know
  about pooler behaviour.

### C. Set the settings on the database role

`ALTER ROLE videos_runtime SET statement_timeout = …`, with no startup options.

- **For:** works through the pooler with no extra round trips.
- **Against:** the timeout values move out of app config into the database, where
  reviewers can't see them. Test schema isolation (`DB_SCHEMA`) still needs startup
  options, so the code would need one path for tests and another for production.

## Consequences

- Any change to `--max-instances` or `DB_POOL_MAX_SIZE` must keep the total under
  Neon's direct-connection limit for the compute size.
- Migrations already use a separate direct owner connection
  (`videos-migrate-database-url`), so they're unaffected.
- **Revisit** if the API needs more than about 10 instances, or if Neon reports
  connection-limit errors. B or C becomes worth its cost then, and moving Cloud Run into
  Neon's region would reduce B's round-trip cost.
