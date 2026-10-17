# Videos service

The Python backend for the videos domain. Its prepared OpenAPI contract generates
all 14 HTTP operations: `/ping` and the 13 video and job operations under `/v1`. Generated
handlers serve fixed, validated contract examples until a matching handwritten
async implementation is added. Video business behavior and processing remain to
be implemented. Documentation endpoints remain disabled. The application owns lifecycle and
documentation settings and may add handwritten routes or mounts.

Regenerate from `api-specs/index.yaml` with the sibling Rust generator:

```sh
cargo run --locked --manifest-path ../api-code-generator/Cargo.toml -- .
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

Visit `http://127.0.0.1:8000/ping` or `/v1/videos`. To run contract mocks without
background PostgreSQL connection attempts, use `DB_POOL_MIN_SIZE=0 make run`.
The preserved database lifecycle opens and closes its pool, while mock handlers
do not query it. The default pool still fills in the background when PostgreSQL
is configured.
Settings are read from `.env` and environment variables, with environment
variables taking precedence. `.env` is ignored by Git.

The pool defaults to 1–5 connections **per process**, with a 5-second acquisition
timeout, a 5-second connection timeout, and 5-second statement and lock timeouts.
The settings in `.env.example` control these defaults. Application shutdown
closes the pool. Repository connection contexts commit successful operations
and roll back operations that raise an exception.

`make db-down` stops the databases while keeping the dev database volume.
The test database uses temporary storage and runs separately on port 5433.

### Media worker

Completing an upload queues a video job and a thumbnail job; completing a custom
thumbnail upload queues a custom thumbnail job. `python -m src.workers.media <job_id>`
runs one job and exits: it downloads the upload from the raw bucket, checks it with
FFprobe, and publishes HLS renditions (360p, 720p, and 1080p, never upscaled) or a
thumbnail to the processed bucket. Thumbnails are published at five 16:9 sizes, from
`xs` (160 × 90) to `xl` (1280 × 720), listed in `src/libs/thumbnails.py`. A custom
thumbnail must be a JPEG, PNG, or WebP image within 1% of 16:9 and at least 1280 × 720;
the worker crops the difference and replaces the shown thumbnail only when it succeeds. A failed job records a readable message;
a failed video job also fails the video. Workers need FFmpeg and the API's settings.

With `API_ENV=prod`, the API starts each job as an execution of the Cloud Run job
`WORKER_JOB_NAME`; [docs/deployment.md](docs/deployment.md) sets it up. In dev, the API
runs `docker compose run --rm -T worker <job_id>` for each job, so worker logs appear in
the API's output. The worker container mounts `src/`, so code changes need no rebuild;
run `make worker-build` after dependency changes.

### Local storage

SeaweedFS stands in for R2, behind Caddy so upload and media URLs are `https://` like
R2's. With `.env` copied from `.env.example`:

```sh
make storage-up   # https://localhost:9443, buckets videos-raw and videos-processed
make local-ca     # copies Caddy's CA certificate to .local/caddy-root.crt
```

`R2_CA_BUNDLE` points the API at that certificate. For a browser to upload and play,
trust it once in the login keychain:

```sh
security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db .local/caddy-root.crt
```

`curl` needs `--cacert .local/caddy-root.crt`. The processed bucket allows anonymous
reads; the raw bucket accepts only signed requests.

The `Dockerfile` builds both images: `docker build --target api .` and
`docker build --target worker .`, which adds FFmpeg. Worker tests run real FFmpeg, so
install it locally (`brew install ffmpeg`).

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
  services/            # Business operations and orchestration (empty initially)
  repositories/        # SQL, storage mapping, pooling, migration tooling
    database.py
    migrate.py
  domain/              # Shared domain models (empty initially)
  clients/             # One module per external service: auth, R2, Cloud Run, FFmpeg
  libs/                # Pure helpers any layer may import
  workers/             # Job process entrypoints, like app.py for HTTP
    media.py           # python -m src.workers.media <job_id>
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
Repositories and services are plain module functions: handlers import services,
services import repositories, and only repositories touch the database.

`clients/` holds one module per external service, wrapping its API; services
import these directly. `libs/` holds pure helpers: they hold data and logic,
make no database or API calls, and import nothing from `services/`,
`repositories/`, `clients/`, or the entrypoints. Any layer may import them, the
repository included, so a fixed mapping every layer needs (language tags to
legacy locale codes, for example) belongs there. A helper that reads stored data
or config belongs in a service; one that wraps an external API belongs in
`clients/`. The
service uses one process-wide pool in `src/repositories/database.py`; the app
lifespan opens and closes it, and the app factory registers the generated
routers once. `/ping` and all fixed examples need no database
query. Add handwritten business models and operations when implementing features.
The generated and service-runtime dependency groups join the existing project
and dev dependencies in normal `uv sync` and a single `uv.lock`.

## Checks and CI

```sh
make check              # Contract checks, Ruff lint/format, strict Pyright
make test               # HTTP/configuration and existing contract-tool tests; no database needed
make test-db-up
make test-integration   # Real PostgreSQL transaction, timeout, and migration checks
make coverage           # Entire suite; fails under 95%, lists files under 100%, writes htmlcov/
make dead-code          # Vulture scan for unused handwritten code (also runs in make lint)
```

The generated suite in `tests/generated` covers all 14 operations, their example
bodies, and native validation; handwritten tests cover authentication, configuration,
health, jobs, and migrations through HTTP, commands, and PostgreSQL.
The [adoption acceptance record](docs/native-fastapi-acceptance.md) records the
executed checks. The generator's CLI-to-HTTP acceptance suite additionally checks handwritten
overrides, dependency injection, regeneration, and generation failures.

`TEST_DATABASE_URL` selects the test database, independently of `DATABASE_URL`.
Integration tests default to the Compose test database and create an isolated
schema per test. They exercise jobs over HTTP, table constraints, statement
timeouts, `make migrate`, and Yoyo apply/reapply/rollback of the service
migrations. HTTP tests apply `migrations/` into their schema first.
Migrations are added incrementally, one per feature slice; `0001_jobs` creates the
`jobs` table, `0002_videos` the `videos` table, `0003_video_listing` the list indexes,
`0004_video_media` upload and media columns, and `0005_thumbnails` custom thumbnails. `make migrate` applies them in dev;
`make migrations` lists their status. These are explicit commands, separate
from server startup.

[GitHub Actions](.github/workflows/ci.yml) runs on pull requests and pushes to
`main`. Two jobs run in parallel:

- **Quality:** contract validation, dead-code scan, Ruff lint/format checks, and Pyright.
- **Tests:** initialize migrations against an ephemeral PostgreSQL 17 service,
  then run pytest, HTTP tests, database tests, and coverage together.

Each job installs the locked dependencies once and caches uv downloads. CI
uses one Python version and cancels superseded validation runs. Coverage of
handwritten code must stay at 95% or more; generated packages are omitted.
Ruff and Pyright cover the scaffold and its new tests; existing
contract-validation code keeps its current tooling.

Production provisioning, deployment, and production migrations are deferred.
When those are added, run production migrations after validation passes as
part of the release workflow, using production environment configuration.
Development migrations remain manual through Make.

## API design targets

The generated video HTTP contract is [`api-specs/index.yaml`](api-specs/index.yaml).
It uses [OpenAPI 3.2.0](https://spec.openapis.org/oas/v3.2.0.html), with JSON Schema
null unions, reusable schemas and responses, and security declarations for the
13 video and job operations. Video and job paths are relative to the `/v1` server base path.
The unauthenticated health operation overrides the server path to `/`, preserving
`GET /ping`. JSON fields and component names use snake_case; operation IDs use
Pythonic `module.function` names, with a leading folder for admin operations
(`admin.videos.create_video`). Resource operations name their noun explicitly,
using singular names for one resource (`videos.get_video`) and plural names for
lists (`videos.list_videos`). Custom methods use colon suffixes with hyphenated
words, such as `/videos/{id}:upload-url` and
`/videos/{id}/thumbnails:complete-upload`, with operation IDs such as
`videos.upload_url` and `thumbnails.complete_upload`.
The plural `/videos/{id}/thumbnails` path still represents one active thumbnail;
deleting the custom thumbnail restores the generated fallback.

Background processing is tracked as a top-level job resource, following Google's
long-running operation pattern (AIP-151). `:complete-upload` returns
`202` with the new `Job` and a `Location: /v1/jobs/{job_id}` header; clients poll
the public `GET /jobs/{job_id}` (`jobs.get_job`), which needs no token. A job has `id`, `status` (`QUEUED`,
`RUNNING`, `SUCCEEDED`, `FAILED`), `content_id`, and a `message` that is set only
when it fails. `content_id` is the ID of whatever resource the job
processes, so later resource jobs can reuse the schema. `Video.latest_job_id` finds the most recent
job without a list endpoint. Video `status` stays a coarse lifecycle state, and
generated thumbnails keep reporting through `Video.thumbnail.status`.

`api-specs/index.yaml` holds API metadata and references to the contract files. Paths
are grouped by resource, with collections, individual resources, and their HTTP
methods kept together. Path files follow operation-ID folders:
[`admin/videos.yaml`](api-specs/paths/admin/videos.yaml) contains admin video and
upload paths, [`admin/thumbnails.yaml`](api-specs/paths/admin/thumbnails.yaml) contains
admin thumbnail paths, [`videos.yaml`](api-specs/paths/videos.yaml) contains viewer
video and playback paths, and [`jobs.yaml`](api-specs/paths/jobs.yaml) contains job
paths. Reusable responses live in
`api-specs/responses/`; operation-specific responses stay in their path files. Examples
are kept in schemas, reusable responses, parameters, and shared request bodies.

Schemas are grouped
by purpose inside `api-specs/schemas/`. Each schema has one example. Viewers see the
catalog shape: [`videos/video.yaml`](api-specs/schemas/videos/video.yaml) and its collection
[`videos/videos.yaml`](api-specs/schemas/videos/videos.yaml). Admin-only schemas carry an
`admin_` file prefix and an `Admin` Python name, such as
[`videos/admin_video.yaml`](api-specs/schemas/videos/admin_video.yaml) (`AdminVideo`).

| Schema folder | Contents |
| --- | --- |
| `health/` | API reachability response. |
| `videos/` | Video resources, collections, metadata, status, updates, and deletion. |
| `uploads/` | Video uploads, upload instructions, and upload completion. |
| `jobs/` | Background processing jobs and their status. |
| `thumbnails/` | Thumbnail resources, image status, and custom thumbnail uploads. |
| `playback/` | Video playback links. |
| `shared/` | Timestamps, media URLs, and list pagination. |

Each query or path parameter has a definition in `api-specs/parameters/`. ID and pagination
schemas are written directly in those files for readability. The publication status filter
reuses its schema in `api-specs/schemas/videos/`. Lists have a fixed order: the admin list is
newest created first, the catalog newest published first. Pass the collection's
`next_page_token` as the `page_token` query parameter, with the same filters, to request the
next page; a token the list did not return gets HTTP 400.
The HTTP-exception schema is defined in `api-specs/index.yaml`; native
request-validation errors are documented in
`api-specs/responses/validation_error.yaml`. Processing failure details are the
job's `message` in `api-specs/schemas/jobs/job.yaml`.

### Generator naming and examples

Generator input names are explicit:

| Field | Meaning | Example |
| --- | --- | --- |
| `operationId` | Handler module and async function; leading segments are folders. | `admin.videos.get_video` |
| `x-python-module` | Generated schema module. | `videos` |
| `x-python-name` | Named Python schema type. | `Video` |

For example, `videos.get_video` targets `handlers/generated/videos.py` and
its `get_video` function. A handwritten override uses the same function name
in `handlers/videos.py`. Likewise, `admin.videos.get_video` targets
`handlers/generated/admin/videos.py`, with its override in `handlers/admin/videos.py`.
Python names stay flat, such as `AdminVideosGetVideoIdParameter`. A schema named `videos.Video` targets
`schemas/generated/videos.py`. These paths are relative to `src/`.
Reusable schemas carry both naming extensions, including scalar schemas and the
shared error schema. Nested inline properties do not need separate naming fields.

Schema examples supply inline mock values; response examples take precedence when
present. Required response headers need examples too. The creation response's
`Location` header references `parameters/response_location.yaml`, a Header Object
with an example and without the request-parameter `name` and `in` fields.
These declarations control the generated interface. The complete prepared
contract currently generates all 14 operations and their validated inline mocks.

### Handwritten implementations

Generated routers select a matching async function in `src/handlers/<module>.py`
(or `src/handlers/<folder>/<module>.py`)
before registering the route. A missing module or function serves the fixed
example. A broken import or incompatible signature fails application construction.
Use the generated function's contract argument names, types, defaults, and return
annotation. Compatible signature-preserving decorators and additional native
`Request`, `Response`, or `Depends` parameters are supported. FastAPI executes the
selected function's dependency graph, including dependencies that raise HTTP errors.
Security declarations document the contract; implementing authentication and
administrator policy remains handwritten work.

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

The source requirements are [`video-backend-spec.md`](../docs/video-backend-spec.md),
its [consolidated specification](../.scratch/video-backend/spec.md), and the
[approved API examples](../docs/pilgrims-progress-video-api-spec.md).
`AGENTS.md` records the essential contract and generated-output conventions.

The contract keeps the existing handoff gaps visible:

- Viewer reads model authenticated and anonymous deployment alternatives.
  Anonymous access requires an explicit deployment choice. Before implementing
  authorization, select the identity provider, admin role mapping, and viewer
  policy; narrow the security requirements if viewer authentication is mandatory.
- Thumbnails are rendered at fixed sizes; resizing on demand through an image
  proxy is a later option. Source and thumbnail byte limits are configurable.
- Finalize accepted-source protection and effective upload-size enforcement;
  decide state retention after failed source verification.
- Database layout, job dispatch/reconciliation, encoding, resource limits,
  retention, CDN configuration, and cache policy remain implementation decisions.

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
FastAPI's native 422 responses. The current generated suite has 38 cases; 202
operations are outside MVP coverage, and all gaps appear in
`tests/generated/coverage.json`. Service-specific business effects require handwritten
assertions. `jobs.get_job`, `videos.list_videos`, `playback.get_playback`, the admin video
create, list, get, update, and delete operations, and the source `upload-url` and
`complete-upload` operations, and the thumbnail operations, read PostgreSQL. Tests replace R2 and worker launches with the fakes in `tests/utilities/fakes.py`.
