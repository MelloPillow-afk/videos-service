# Videos service

The Python backend for the videos domain. The initial scaffold implements only
`GET /ping`, returning HTTP 200 with `{"status":"ok"}` without authentication or
a database query. Documentation endpoints are disabled, so `/ping` is the only
registered HTTP path.

Build the prototype from requirements first, then consolidate the contract as
the video operations are implemented. The files in `api-specs/` describe future video
operations; they are not implemented by this scaffold.

## Local development

Use Python 3.13 and [uv](https://docs.astral.sh/uv/). PostgreSQL runs through
Docker Compose; the API runs on the host through Uvicorn.

```sh
make install
cp .env.example .env
make db-up
make migrate
make run
```

Visit `http://127.0.0.1:8000/ping`. `make run` also works without PostgreSQL:
the connection pool fills in the background and `/ping` stays available.
Settings are read from `.env` and environment variables, with environment
variables taking precedence. `.env` is ignored by Git.

The pool defaults to 1–5 connections **per process**, with a 5-second acquisition
timeout, a 5-second connection timeout, and 5-second statement and lock timeouts.
The settings in `.env.example` control these defaults. Application shutdown
closes the pool. Repository connection contexts commit successful operations
and roll back operations that raise an exception.

`make db-down` stops the databases while keeping the dev database volume.
The test database uses temporary storage and runs separately on port 5433.

## Structure and layers

```text
src/
  app.py               # App factory and startup/shutdown lifecycle
  config.py            # pydantic-settings configuration
  handlers/            # HTTP input, service calls, response shaping
    ping.py
  schemas/             # Pydantic HTTP models
    ping.py
  services/            # Business operations and orchestration (empty initially)
  repositories/        # SQL, storage mapping, pooling, migration tooling
    database.py
    migrate.py
  domain/              # Shared domain models (empty initially)
migrations/            # Future Yoyo SQL migrations
tests/
  unit/                # Reachability and settings checks
  integration/         # Real PostgreSQL and migration checks
```

The [Service & Repository Layering Standard](https://app.notion.com/p/3c3f1f2d1b9280e19e06cf88d0ddcc02)
supplies the folder structure and layer responsibilities. This service uses its
own stack: FastAPI, Pydantic v2, pydantic-settings, psycopg 3, psycopg_pool, Yoyo,
Uvicorn, and uv. No framework-specific tooling from the reference carries over.

Handlers reach storage through services. Services own business decisions and
call repositories; repositories own SQL, database connections, and mapping
stored data to domain models. Domain models hold shared data definitions.
The app factory invokes the repository resource lifecycle. `/ping` needs no
business service or repository call. Add business models and operations when
implementing video features.

## Checks and CI

```sh
make check              # Contract checks, Ruff lint/format, strict Pyright
make test               # HTTP/configuration and existing contract-tool tests; no database needed
make test-db-up
make test-integration   # Real PostgreSQL transaction, timeout, and migration checks
make test-all           # Entire suite, with terminal and XML coverage reports
```

`TEST_DATABASE_URL` selects the test database, independently of `DATABASE_URL`.
Integration tests default to the Compose test database and create an isolated
schema per test. They exercise commits, rollbacks, statement timeouts, and
Yoyo migration apply/reapply/rollback with a test-only table. There are no video
tables or application migrations yet. `make migrate` initializes Yoyo's
bookkeeping in dev and will apply migrations added to `migrations/`;
`make migrations` lists their status. These are explicit commands, separate
from server startup.

[GitHub Actions](.github/workflows/ci.yml) runs on pull requests and pushes to
`main`. Two jobs run in parallel:

- **Quality:** contract validation, Ruff lint/format checks, and Pyright.
- **Tests:** initialize migrations against an ephemeral PostgreSQL 17 service,
  then run pytest, HTTP tests, database tests, and coverage together.

Each job installs the locked dependencies once and caches uv downloads. CI
uses one Python version and cancels superseded validation runs. Coverage is
reported without a percentage gate. Ruff and Pyright cover the scaffold and
its new tests; existing contract-validation code keeps its current tooling.

Production provisioning, deployment, and production migrations are deferred.
When those are added, run production migrations after validation passes as
part of the release workflow, using production environment configuration.
Development migrations remain manual through Make.

## API design targets

The planned video HTTP contract is [`api-specs/index.yaml`](api-specs/index.yaml).
It uses [OpenAPI 3.2.0](https://spec.openapis.org/oas/v3.2.0.html), with JSON Schema
null unions, reusable schemas and responses, bearer authentication, and examples
for all 12 operations. Paths are relative to the `/v1` server base path.
JSON fields, operation IDs, and component names use snake_case.

`api-specs/index.yaml` holds API metadata and references to the contract files. Paths
are grouped by resource, with collections, individual resources, and their HTTP
methods kept together. [`videos.yaml`](api-specs/paths/videos.yaml) contains video paths,
including uploads, playback, and retries. [`thumbnails.yaml`](api-specs/paths/thumbnails.yaml)
contains thumbnail paths. Reusable responses live in
`api-specs/responses/`; operation-specific responses stay in their path files. Examples
are kept beside the operations and responses that use them.

Schemas are grouped
by purpose inside `api-specs/schemas/`. Each schema has one example. A single video uses
[`videos/video.yaml`](api-specs/schemas/videos/video.yaml); a collection uses
[`videos/videos.yaml`](api-specs/schemas/videos/videos.yaml).

| Schema folder | Contents |
| --- | --- |
| `videos/` | Video resources, collections, metadata, status, updates, retries, and deletion. |
| `uploads/` | Video uploads, upload instructions, and completion or processing results. |
| `thumbnails/` | Thumbnail resources, image status, and custom thumbnail uploads. |
| `playback/` | Video playback links. |
| `shared/` | Timestamps and media URLs. |

Each query or path parameter has a definition in `api-specs/parameters/`. IDs, pagination,
and search schemas are written directly in those files for readability. Video
status filters reuse the status schemas in `api-specs/schemas/videos/`. Pass the collection's
`next_page_token` as the `cursor` query parameter to request the next page.
The common API error schema is defined in `api-specs/index.yaml`. Processing failure
details are defined directly in `api-specs/schemas/videos/video.yaml`.

## Validate the contract

Install [uv](https://docs.astral.sh/uv/) and use Python 3.13. From this
directory:

```sh
uv sync --locked
make lint-api
```

`uv.lock` fixes the resolved validation dependencies. `make lint-api` fails on
YAML syntax/style issues, duplicate YAML keys, OpenAPI structure and reference
errors, or examples that violate their schemas. It runs yamllint,
[openapi-spec-validator](https://openapi-spec-validator.readthedocs.io/en/latest/cli.html)
with the OpenAPI 3.2 schema, and a Python reference/example checker (including UUID,
timestamp, and URI formats). YAML lint covers every contract file. The checker resolves
references across local files without fetching remote documents. These checks validate
the contract; the consolidated
spec's REST API acceptance scenarios will validate runtime behavior during
implementation. The same command can run in CI when the repository is set up.

Without Make, run the commands individually:

```sh
uv run --locked yamllint api-specs
uv run --locked openapi-spec-validator --schema 3.2 api-specs/index.yaml
uv run --locked python scripts/check_examples.py
```

## Requirements and unresolved decisions

The source requirements are [`video-backend-spec.md`](../docs/video-backend-spec.md),
its [consolidated specification](../.scratch/video-backend/spec.md), and the
[approved API examples](../docs/pilgrims-progress-video-api-spec.md).
`AGENTS.md` records the prototype-first workflow for this service.

The contract keeps the existing handoff gaps visible:

- Viewer reads model authenticated and anonymous deployment alternatives.
  Anonymous access requires an explicit deployment choice. Before implementing
  authorization, select the identity provider, admin role mapping, and viewer
  policy; narrow the security requirements if viewer authentication is mandatory.
- Thumbnail format and size allowlists, dimensions, aspect ratio, and cropping
  policy await the missing approved thumbnail specification. JPEG examples do
  not establish the full allowlist. Source byte limits are configurable too.
- Finalize accepted-source protection and effective upload-size enforcement;
  decide state retention after failed source verification and the thumbnail
  response when custom removal reveals a failed generated fallback.
- Database layout, job dispatch/reconciliation, encoding, resource limits,
  retention, CDN configuration, and cache policy remain implementation decisions.

The general requirements reserve HTTP 422 for well-formed but unsupported or
invalid media. No supplied endpoint assigns that status specifically: custom
image rejection uses 400, and real MP4 validation occurs asynchronously. Resolve
the endpoint mapping before adding a 422 response; avoid inventing a synchronous
MP4 validation step.

Uploads go directly to R2; the API accepts no media bytes. Publishing and deletion
govern API discovery, while previously retrieved public CDN URLs may remain
accessible until cache expiration or purge.
