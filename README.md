# Videos service

The Python backend for a shared video library. The OpenAPI contract generates
13 routes: `/ping` and 12 video operations under `/v1`. Handwritten handlers and
PostgreSQL implement draft management, direct uploads, publication/discovery,
playback, custom thumbnails, and asynchronous deletion admission. FFmpeg workers
produce media independently of requests. Privileged requests verify Neon Auth
JWTs and the current provider-owned administrator role; viewers browse ready,
published videos anonymously. Documentation endpoints remain disabled.

Deletion admission immediately hides content and records cleanup work. Physical
cleanup remains pending the writer-protection decision and its evidence; a 202
response does not certify removal. The reproducible showcase (MEL-15), configured
cloud readiness (MEL-7), and live provider acceptance (MEL-16) are separate gates.

Regenerate from `api-specs/index.yaml` with the sibling Rust generator:

```sh
ag .
uv lock
uv sync
```

`src/app.py` calls `register_routers(app)` from `src.core.generated.routers` once.
Later contract changes renew its explicit router inclusions without handwritten
per-operation wiring.
Generated decorators contain runtime settings only; API documentation stays in
`api-specs/`.
Generation preserves configuration, lifecycle, domain/service/repository code,
and handwritten handlers. Keep `.api-code-generator.json` with renewable output;
do not edit files under generated packages.

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

Visit `http://127.0.0.1:8000/ping` for database-independent health. Video operations
use PostgreSQL; configure Neon Auth, R2, and job submission for provider-dependent
requests. Missing provider configuration fails closed. `DB_POOL_MIN_SIZE=0`
disables background pool filling but does not make video operations independent
of the database. The application lifecycle opens and closes its pool.
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
    generated/         # Renewable contract handlers
    ping.py            # Preserved old handler; no direct HTTP registration
  schemas/             # Pydantic HTTP models
    generated/         # Renewable wire models
    ping.py            # Preserved handwritten schema
  core/
    generated/         # Renewable router composition and override selection
  services/            # Business operations, media processing, orchestration
  repositories/        # SQL, data mapping, pooling, migration tooling
    database.py
    migrate.py
  domain/              # Shared persisted state, cursors, cleanup inventory
  providers/           # Neon identity, R2 objects, Cloud Run launch boundaries
  worker.py            # One persisted media job per invocation
  cleanup.py           # Read-only deletion inventory for operators
migrations/            # Explicit Yoyo application migrations
tests/
  unit/                # Reachability and settings checks
  integration/         # Real HTTP/PostgreSQL, media, and migration acceptance
```

The [Service & Repository Layering Standard](https://app.notion.com/p/3c3f1f2d1b9280e19e06cf88d0ddcc02)
supplies the folder structure and layer responsibilities. This service uses its
own stack: FastAPI, Pydantic v2, pydantic-settings, psycopg 3, psycopg_pool, Yoyo,
Uvicorn, and uv. No framework-specific tooling from the reference carries over.

Handlers reach storage through services. Services own business decisions and
call repositories; repositories own SQL, database connections, and mapping
stored data to domain models. Domain models hold shared data definitions.
The app factory retains the repository resource lifecycle and registers the
generated routers once. `/ping` needs no database query. Renewable schemas and
routers adapt the authoritative contract; business services and repositories
remain handwritten.
The generated and service-runtime dependency groups join the existing project
and dev dependencies in normal `uv sync` and a single `uv.lock`.

## Checks and CI

```sh
make check              # Contract checks, Ruff lint/format, strict Pyright
make test               # HTTP/configuration and existing contract-tool tests; no database needed
make test-db-up
make test-integration   # Real PostgreSQL transaction, timeout, and migration checks
make test-all           # Entire suite, with terminal and XML coverage reports
```

The HTTP suite covers all 13 generated operations, exact paths, deterministic
example bodies, creation headers, native validation, and application-owned routes.
The [adoption acceptance record](docs/native-fastapi-acceptance.md) records the
executed checks. The generator's CLI-to-HTTP acceptance suite additionally checks handwritten
overrides, dependency injection, regeneration, and generation failures.

`TEST_DATABASE_URL` selects the test database, independently of `DATABASE_URL`.
Integration tests default to the Compose test database and create an isolated
schema per test. They exercise commits, rollbacks, statement timeouts, and
Yoyo migration apply/reapply/rollback with a test-only table. The application migration creates `videos`, `upload_attempts`, and `jobs`;
Yoyo bookkeeping is separate from those three application tables. `make migrate` initializes Yoyo's
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

Run production migrations explicitly after validation with the target environment
configuration; they never run automatically at server startup. Deployment and
provider readiness require their own target evidence. Development migrations
remain manual through Make.

The [showcase cloud readiness record](docs/cloud-readiness.md) lists required
Neon, R2/CDN, and Cloud Run inputs, setup permissions, and pending live evidence.
Local acceptance does not require cloud credentials.

The [local HLS worker acceptance record](docs/mel-9-acceptance.md) documents
encoding, media limits and resource defaults. Install FFmpeg and FFprobe for real
processing and the acceptance suite. Run accepted work with
`uv run --locked python -m src.worker run --job-id UUID`; the worker reads the
job and source from PostgreSQL and uses configured private/public R2 storage.

Feature evidence is recorded for [source acceptance](docs/mel-8-acceptance.md),
[HLS processing](docs/mel-9-acceptance.md),
[publication and discovery](docs/library-acceptance.md),
[custom thumbnails](docs/custom-thumbnail-acceptance.md), and
[partial deletion admission](docs/deletion-acceptance.md). These local records
do not replace the live cloud showcase.

## API design targets

The generated video HTTP contract is [`api-specs/index.yaml`](api-specs/index.yaml).
It uses [OpenAPI 3.2.0](https://spec.openapis.org/oas/v3.2.0.html), with JSON Schema
null unions, reusable schemas and responses, and security declarations for the
12 video operations. Video paths are relative to the `/v1` server base path.
The unauthenticated health operation overrides the server path to `/`, preserving
`GET /ping`. JSON fields and component names use snake_case; operation IDs use
Pythonic `module.function` names. Resource operations name their noun explicitly,
using singular names for one resource (`videos.get_video`) and plural names for
lists (`videos.list_videos`). Custom methods use colon suffixes with hyphenated
words, such as `/videos/{id}:upload-url` and
`/videos/{id}/thumbnails:complete-upload`, with operation IDs such as
`videos.upload_url` and `thumbnails.complete_upload`.
The plural `/videos/{id}/thumbnails` path still represents one active thumbnail;
deleting the custom thumbnail restores the generated fallback.

`api-specs/index.yaml` holds API metadata and references to the contract files. Paths
are grouped by resource, with collections, individual resources, and their HTTP
methods kept together. [`videos.yaml`](api-specs/paths/videos.yaml) contains video paths,
including uploads, playback, and retries. [`thumbnails.yaml`](api-specs/paths/thumbnails.yaml)
contains thumbnail paths. Reusable responses live in
`api-specs/responses/`; operation-specific responses stay in their path files. Examples
are kept in schemas, reusable responses, parameters, and shared request bodies.

Schemas are grouped
by purpose inside `api-specs/schemas/`. Each schema has one example. A single video uses
[`videos/video.yaml`](api-specs/schemas/videos/video.yaml); a collection uses
[`videos/videos.yaml`](api-specs/schemas/videos/videos.yaml).

| Schema folder | Contents |
| --- | --- |
| `health/` | API reachability response. |
| `videos/` | Video resources, collections, metadata, status, updates, retries, and deletion. |
| `uploads/` | Video uploads, upload instructions, and completion or processing results. |
| `thumbnails/` | Thumbnail resources, image status, and custom thumbnail uploads. |
| `playback/` | Video playback links. |
| `shared/` | Timestamps and media URLs. |

Each query or path parameter has a definition in `api-specs/parameters/`. IDs, pagination,
and search schemas are written directly in those files for readability. Video
status filters reuse the status schemas in `api-specs/schemas/videos/`. Pass the collection's
`next_page_token` as the `cursor` query parameter to request the next page.
The HTTP-exception schema is defined in `api-specs/index.yaml`; native
request-validation errors are documented in
`api-specs/responses/validation_error.yaml`. Processing failure details are defined
directly in `api-specs/schemas/videos/video.yaml`.

### Generator naming and examples

Generator input names are explicit:

| Field | Meaning | Example |
| --- | --- | --- |
| `operationId` | Handler module and async function. | `videos.get_video` |
| `x-python-module` | Generated schema module. | `videos` |
| `x-python-name` | Named Python schema type. | `Video` |

For example, `videos.get_video` targets `handlers/generated/videos.py` and
its `get_video` function. A handwritten override uses the same function name
in `handlers/videos.py`. A schema named `videos.Video` targets
`schemas/generated/videos.py`. These paths are relative to `src/`.
Reusable schemas carry both naming extensions, including scalar schemas and the
shared error schema. Nested inline properties do not need separate naming fields.

Schema examples supply inline mock values; response examples take precedence when
present. Required response headers need examples too. The creation response's
`Location` header references `parameters/response_location.yaml`, a Header Object
with an example and without the request-parameter `name` and `in` fields.
These declarations control the generated interface. The complete prepared
contract currently generates all 13 operations and their validated inline mocks.

### Handwritten implementations

Generated routers select a matching async function in `src/handlers/<module>.py`
before registering the route. A missing module or function serves the fixed
example. A broken import or incompatible signature fails application construction.
Use the generated function's contract argument names, types, defaults, and return
annotation. Compatible signature-preserving decorators and additional native
`Request`, `Response`, or `Depends` parameters are supported. FastAPI executes the
selected function's dependency graph, including dependencies that raise HTTP errors.
Security declarations document the contract. Handwritten administrator policy
verifies the signed identity and reads the current role for each privileged request.

Return the generated Pydantic model directly. For example, a creation handler
accepts `response: Response` and assigns `response.headers["Location"]` to the new
resource URL. Response models handle serialization and omit unset optional fields;
required nullable fields remain present. Required headers are checked by endpoint
acceptance tests. Omitting a header does not trigger a generated server error.
Reusable error responses describe behavior and do not create runtime error factories.

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

The [canonical showcase specification](../.scratch/video-backend/spec.md) defines
implementation scope. The retained [business API specification](docs/specs/pilgrims-progress-video-api-spec.md)
provides context; current OpenAPI controls HTTP shapes and supersedes older prose
examples. The [tracker configuration](../docs/agents/issue-tracker.md) identifies
the approved Linear tickets.
`AGENTS.md` records the essential contract and generated-output conventions.

The approved showcase scope is MP4 up to 100 MiB and 300 seconds by default,
three application tables, independent thumbnails, direct job launch, and manual
recovery. Viewer discovery is anonymous and restricted to READY/PUBLISHED media.
No periodic reconciliation, cron, or scheduled orphan cleanup is included.
The canonical implementation specification and current contract resolve the older
prose's media limits and authorization alternatives.

Neon Auth configuration uses `AUTH_ISSUER` (the origin of the Auth endpoint),
`AUTH_JWKS_URL` (the complete provider JWKS endpoint), and `AUTH_AUDIENCE` when
the deployed token uses an audience. Ed25519 signatures, issuer, required expiry,
issued-at time, and subject are checked. `AUTH_SCHEMA` defaults to `neon_auth`;
the provider-owned `"user"` table supplies current comma-separated roles.
Only exact `admin` membership permits management; JWT role claims are ignored.
Missing provider configuration or role lookup failures deny privileged access.
The application does not create or migrate provider tables. Deployed token
settings and schema compatibility remain a separate live-cloud acceptance gate.

Invalid path, query, and body values use FastAPI's native HTTP 422 JSON response,
with validation errors in `detail`. Deliberate application errors use standard
`HTTPException` responses such as `{"detail": "The video was not found."}`. HTTP
400 documents deliberate rejections such as unsupported media; request validation
does not use 400. Unexpected failures and invalid response bodies use the normal
production HTTP 500 text response, `Internal Server Error`.

Uploads go directly to R2; the API accepts no media bytes. Publishing and deletion
govern API discovery, while previously retrieved public CDN URLs may remain
accessible until cache expiration or purge.


## Generated HTTP integration tests

`ag` generates one test module per handler module under `tests/generated/`.
Tests use Arrange → Act → Assert, the real app lifespan and HTTP stack, and a fresh
PostgreSQL schema per case. `tests/conftest.py` configures the app from
`TEST_DATABASE_URL`; missing test infrastructure fails setup. The test database is
still started with `make test-db-up`, and `make test-integration` or normal `pytest`
runs the generated cases. `make test` continues to select non-integration tests.

Customize operation fixtures such as `arrange_videos_get_video(api_case, api_app)`
in `tests/conftest.py` as handlers are implemented. Arrange records and adjust
`api_case.path_params`, `.query`, `.headers`, `.body`, or `.expected_body` before the
request. Yield fixtures can inspect `.response`, assert stored effects, and clean up
in `finally`. No hook or fixture belongs inside `tests/generated`.

Schema examples are authoritative for success assertions. Parameter validation keeps
FastAPI's native 422 responses. The current generated suite has 23 cases; 202
operations are outside MVP coverage, and all gaps appear in
`tests/generated/coverage.json`. Service-specific business effects require handwritten
assertions. Persisted operations retain these generated HTTP cases through handwritten Arrange
fixtures. Handwritten business cases cover acceptance behavior beyond those
fixed examples, including asynchronous 202 operations.

## Source uploads and direct launch

Source upload instructions and confirmation now persist attempts and independent
VIDEO/THUMBNAIL jobs. Configure R2 and the Cloud Run Job resource from `.env.example`.
The R2 signer binds create-once PUT headers; originals and delivery outputs use
separate buckets. The Cloud Run service's runtime identity submits jobs directly.
Missing provider configuration returns unavailable instead of serving an upload
example. The [MEL-8 acceptance record](docs/mel-8-acceptance.md) describes local
provider checks and the separate live-cloud evidence gates.

Inspect `jobs.state`, `execution_reference`, and sanitized errors for recorded work.
An interrupted or uncertain launch requires manual inspection and explicit recovery;
repeating upload confirmation does not dispatch it again. No periodic dispatcher or
cleanup scheduler is included.
