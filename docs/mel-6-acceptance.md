# MEL-6 — persisted drafts and administrator identity

Local acceptance completed on 2026-10-16. This records the first application slice,
not full service or live-cloud acceptance.

The authoritative OpenAPI contract now states anonymous READY/PUBLISHED viewer
access, Neon Auth current-role authorization, five-minute/100 MiB sources,
independent thumbnails, and direct launch/manual recovery. Oversized examples
were corrected. `make lint-api` validated the contract and 45 examples before
`ag` regenerated 13 operations and 23 HTTP cases. The `ag-generate` skill was
used; generated ownership remains intact.

The first HTTP tracer failed because creation returned the fixed example title;
creation/detail then passed against PostgreSQL. The next tracer showed anonymous
creation returning 201 before policy was added. Metadata editing similarly failed
against the fixed example before persistence was implemented. The final suite
exercises the real app lifespan, services, PostgreSQL repositories, and migrations.
Only external signing keys and time/randomness are controlled at their boundaries.

Verification:

- `make check`: OpenAPI, 45 examples, Ruff, format checks, strict Pyright pass.
- `uv run --locked pytest --cov --cov-report=term-missing`: 85 passed, 86% total
  measured application coverage. Includes 19 new draft/identity HTTP cases.
- Yoyo applies and reapplies the actual three-table migration, then rolls it back.
- Generated create/detail/update cases use handwritten Arrange hooks, controlled
  clock/IDs, signed identities, and real persistence. No owned output was patched.

The HTTP cases verify creation/Location/nulls/UTC timestamps, subsequent detail,
metadata edits and clearing description, native request validation, anonymous
hiding, current-role membership, same-token demotion, signature/expiry/issuer/
audience rejection, and closed authorization on role-store failure. `/ping` stays
database-independent.

The application tables are `videos`, `upload_attempts`, and `jobs`. Partial unique
indexes select one current upload or job per video/kind; accepted timestamps remain
for audit after superseding/removal. Services own transaction scopes. Provider
identities/roles are never application-migrated.

Neon primary documentation checked:

- [Authentication flow](https://neon.com/docs/auth/authentication-flow): verified
  subject maps to the provider-owned user ID; identity data resides in `neon_auth`.
- [JWT](https://neon.com/docs/auth/guides/plugins/jwt): Ed25519, provider JWKS,
  issuer equal to the Auth URL origin, and configured applicable audience.
- [Admin](https://neon.com/docs/auth/guides/plugins/admin) and
  [Better Auth roles](https://better-auth.com/docs/plugins/admin#roles): current
  role authorization uses exact `admin` membership in comma-separated text.

Local fixtures provide a minimal provider-owned user directory in a separate
schema. The deployed Managed Better Auth version, actual schema privileges,
issuer/JWKS/audience and live role demotion must still be verified in MEL-16.
Those facts are not proven by local fixtures. Cloud readiness evidence is tracked
separately in the MEL-7 documentation.
