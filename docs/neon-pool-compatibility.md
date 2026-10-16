# Neon pooled-connection compatibility (MEL-7)

Verified 2026-10-16 against local PostgreSQL 17 and the supplied Neon PostgreSQL 18
pooled target. No target application migrations, schema changes, role changes, or
data mutations were performed. Connection URLs and credentials are omitted.

The original application passed statement/lock timeout and search path as libpq
startup `options`. The target pooler rejects that startup parameter. The pool now
connects normally and starts each borrowed transaction with `set_config(..., true)`
for those three settings. The local flag makes the values expire on commit or
rollback, before a transaction-mode backend can serve another borrower. The same
connection context still commits on success and rolls back on exceptions; callers
keep related work inside one context. No session initialization or pool reset
hook is used. Database-independent `/ping` is unchanged.

The real local regression failed before the fix because application search path
had become the session reset default. It now verifies configured schema and both
timeouts, unchanged session defaults, reuse after a committed local override, and
reuse after a canceled statement/rollback. A separate real contention case proves
lock waits fail with `LockNotAvailable` rather than waiting until the statement
timeout, then confirms the connection remains usable. Existing commit/rollback,
statement timeout, schema and application acceptance remain covered.

Validation on feature commit: all 206 tests passed with real local PostgreSQL and
media processing (31.02s). `make check` passed 46 contract examples, Ruff lint and
formatting, and strict Pyright with zero errors. No HTTP contract changed.

Read-only target probe results:

- Real application `Database` pool acquired a connection through the supplied
  Neon pooler; client libpq reported TLS in use and the server reported PG18.
- Transaction policy reported `public`, `250ms` statement timeout, and `250ms`
  lock timeout.
- `SELECT pg_sleep(1)` raised `QueryCanceled`; the following borrowed transaction
  reported the same expected policy and executed successfully.
- The target still had none of `videos`, `upload_attempts`, `jobs`, or Yoyo's
  `_yoyo_migration` table. This verifies connectivity and transaction settings,
  not application deployment or migration readiness.

The probe used only SELECT queries and transaction-local configuration. The
backend `pg_stat_ssl` view does not describe the client's connection to a pooler;
client libpq TLS state was checked instead. Neon Auth token/demotion checks,
least-required runtime privileges, explicit direct-connection production
migrations, R2/Cloud Run/CDN, and complete live acceptance remain separate gates.

References: [Neon transaction pooling](https://neon.com/docs/connect/connection-pooling),
[PostgreSQL transaction-local set_config](https://www.postgresql.org/docs/current/functions-admin.html).
