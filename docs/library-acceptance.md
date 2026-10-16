# Published library acceptance (MEL-13)

Local verification on 2026-10-16 uses the real FastAPI app, signed identities,
current-role reads, isolated PostgreSQL schemas, and seeded peer media states.
HLS generation is tested by the worker tickets; these tests verify API discovery.

`tests/integration/test_library.py` covers:

- Concurrent publication preserving the first publication timestamp; unpublication
  clearing it; metadata edits retaining readiness and publication state.
- Publication requiring READY independently of thumbnail state.
- Anonymous detail/list/playback restricted to READY + PUBLISHED; administrator
  draft preview; immediate loss of preview permission after role demotion.
- Anonymous discovery while the role directory is unavailable; fail-closed
  privileged requests; hidden/missing playback returning 404 and unready admin
  playback returning 409.
- Case-insensitive literal title search, administrator-only lifecycle/publication
  filters, native page-size validation, and descending creation-time/UUID order.
- Keyset continuation across equal timestamps and new inserts; invalid cursors
  and changes to original search, filters, page size, or visibility returning 400.
- Configured public delivery origin plus stored keys, URL encoding, custom-image
  priority/generated fallback, pending/failed placeholders, and populated safe
  processing errors. Private object keys are not resource fields.

The cursor carries a versioned position and query fingerprint in an opaque
encoding. It is a continuation position, not an access credential. Every request
reapplies the current authorization and visibility conditions. Pages reflect
current database state rather than a frozen snapshot; newly published or edited
videos can change membership between requests.

The handwritten generated-test arrangement seeds the contract's ready example;
single-page list expectations use a null continuation rather than the contract's
illustrative token. Renewable tests remain generator-owned.

Executed: `make lint-api` (45 examples), `ag` (13 operations / 23 HTTP cases),
Ruff, strict Pyright, and the complete local pytest suite (103 passing). The
suite includes the PostgreSQL-backed cases. No live CDN access or provider cloud
behavior is claimed. Publication controls discovery; public CDN links may remain
usable after unpublication until storage/cache expiry or removal.
