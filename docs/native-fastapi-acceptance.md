# Native FastAPI adoption acceptance

Verified 2026-10-15 against the complete Videos OpenAPI contract.

`src/app.py` invokes `src.core.generated.routers.register_routers` once. The
handwritten database lifecycle, configuration, dependencies, and disabled
documentation settings remain in place. Generation retired the owned registry
and transport runtime and produced six routers plus explicit composition.

The HTTP suite in `tests/unit/test_generated_api.py` verifies all 13 operations
with their existing methods, exact resolved paths, complete deterministic
contract examples, success statuses, and creation `Location`. The collection
continues to use `/v1/videos` without a trailing slash. Root health remains
`/ping`. Resource-specific ready-draft examples take precedence over the shared
Video schema's created-draft example. Required nullable fields remain present
and absent optional `processing_error` remains omitted.

Native HTTP acceptance also verifies URL integer parsing and query filters,
bounds, enum and UUID validation, missing/invalid bodies, empty and unknown-only
updates, nullable description updates, and rejected null titles. Invalid requests
return native 422 `detail` lists. Application-owned routes survive lifespan
startup; deliberate HTTP exceptions return JSON `detail`, and unexpected errors
return production text 500 without exception details. OpenAPI retains tags and
documents native 400/422/500 bodies. The existing unreachable-database health
check confirms fixed mocks need no database query.

Checks run in the existing Python 3.13 environment, with a temporary `.venv`
symlink to that environment and `UV_CACHE_DIR=/private/tmp/pilgrims-uv-cache
UV_NO_SYNC=1`:

- `make check`: passed contract YAML, OpenAPI 3.2, 46 example checks, Ruff lint,
  Ruff formatting (40 files), and strict Pyright (zero errors).
- `make test`: passed all 34 nonintegration tests; 3 integration tests deselected.
- Repeated generator CLI invocation preserved exact bytes for generated output,
  ownership manifest, app, configuration, dependencies/lock, repositories, and
  handwritten ping. Obsolete runtime/registry remained absent.

No database infrastructure, migrations, or integration suite was run. Broader
handwritten override, dependency injection, and ownership-failure scenarios are
covered by the generator's CLI-to-HTTP acceptance suite.
