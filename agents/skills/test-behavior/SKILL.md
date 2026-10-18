---
name: test-behavior
description: Behavior testing for videos-service. Use when writing, changing, or reviewing tests.
---

# Test behavior

A test claims what the service does for its users: HTTP callers, operators running
commands, and the systems it writes to. Assert what they observe: status, body,
headers, the error type callers branch on, rows written, requests sent outward.
For example, an expired token returns 401 with
`WWW-Authenticate: Bearer error="invalid_token"`.

Judge every test with two edits:

- **Break the behavior** (wrong value, skipped effect): the test goes red.
- **Restructure the internals**, keeping every observable result: the test stays green.

Derive expected values from `api-specs/` or the requirement, never from a run of the code.

## Entry points

- **HTTP:** `create_app()` through httpx `ASGITransport`, as in `tests/unit/test_auth.py`.
- **Commands:** a subprocess, the way the Makefile runs them, as in
  `tests/integration/test_migrate_command.py`.
- **Persistence:** real PostgreSQL through the fixtures in `tests/conftest.py`.

Fakes stand in only for what the service does not own: signing keys
(`tests/utilities/auth_provider.py`) and the clock.

## Exceptions

Test a function directly only when it is pure with many edge cases (a validator, a
parser), or for a failure path the entry points reach only at high cost. Code that no
entry point reaches gets deleted.

`# pragma: no cover` carries a comment naming why the line is unreachable.

Adapted from pstack's `principle-test-behavior-not-implementation`.
