# Videos service

It's a FastAPI app on Python 3.13, backed by Postgres (Neon) and S3-compatible storage
(Cloudflare R2). Sign-in is handled by Neon Auth.

## How it fits together

- **The API** (`src/app.py`) handles HTTP. It never touches video bytes: it hands out
  signed upload URLs, and browsers upload directly to the `videos-raw` bucket.
- **Jobs**: when an upload completes, the API records a job and starts a **worker**
  for it (`python -m src.workers.media <job_id>`). Locally that's a Docker Compose
  container. In production it's a Cloud Run job execution.
- **The worker** checks the upload with FFprobe, renders HLS and thumbnails with
  FFmpeg, publishes them to the public `videos-processed` bucket, and records the
  outcome. Clients poll `GET /v1/jobs/{id}` to follow along.

## Getting started

You'll need [uv](https://docs.astral.sh/uv/), Docker, and FFmpeg
(`brew install ffmpeg`; the worker tests run it for real).

```sh
make install          # Python 3.13 and locked dependencies
cp .env.example .env  # local settings: fill in your Neon Auth origin
make db-up            # Postgres in Docker
make storage-up       # SeaweedFS + Caddy at https://localhost:9443, standing in for R2
make local-ca         # copy Caddy's certificate to .local/ so the API trusts it
make worker-build     # the worker image the API starts for each job
make migrate          # create the tables
make run              # http://127.0.0.1:8000
```

Check it's up with `curl http://127.0.0.1:8000/ping`. Admin routes need a bearer token:

```sh
TOKEN=$(uv run --locked python scripts/get_token.py --email you@example.com)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/v1/admin/videos
```

For a quick session without Neon, run `AUTH_DISABLED=true make run`, and any token is
accepted. Keep it out of `.env`, though: the tests read `.env` too, and the auth tests
expect auth to be on.

For a browser to upload to local storage and play the results, trust the local
certificate once:

```sh
security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db .local/caddy-root.crt
```

Locally, the worker container mounts `src/`, so code changes need no rebuild. Rebuild
with `make worker-build` only after dependency changes. Worker logs show up in the
API's output.

Settings come from `.env` and environment variables, and environment variables win.
Everything is defined, with defaults, in [src/config.py](src/config.py).

## Everyday commands

| Command | What it does |
|---|---|
| `make run` | Run the API with reload |
| `make check` | Lint the API contract, Ruff, format check, Pyright, the dead-code scan, and the layer contracts |
| `make format` | Format everything |
| `make test` | Fast tests, no database needed |
| `make test-db-up` | Start the throwaway test database (port 5433) |
| `make test-integration` | Tests against real Postgres |
| `make coverage` | Full suite with coverage; writes `htmlcov/` |
| `make migrate` / `make migrations` | Apply / list migrations |
| `make db-down` | Stop the databases (dev data is kept) |

A change is done when `make check` passes and `make coverage` keeps handwritten code at
95% or more. CI holds every pull request to the same bar.

## Project layout

```text
src/
  app.py           # app factory and lifespan
  config.py        # every setting, with defaults
  handlers/        # HTTP in, service calls, HTTP out
  services/        # business rules and orchestration
  repositories/    # SQL, connection pool, migrations runner
  domain/          # entities, enums, and domain errors only
  clients/         # one module per outside service: R2, Cloud Run, FFmpeg, auth
  libs/            # pure helpers any layer can use
  workers/         # job entrypoints, like app.py is for HTTP
  */generated/     # written by the code generator; don't edit
migrations/        # Yoyo SQL migrations, applied in order
api-specs/         # the OpenAPI contract
tests/             # unit, integration, and generated HTTP tests
deploy/            # production settings and one-time GCP setup
```

Imports point inward: handlers and workers call services, services call repositories and
clients, and everything shares the `domain` entities. [docs/architecture/layers.md](docs/architecture/layers.md)
has the principles and where new code goes; `make layers` checks the boundaries.

## The API contract

[`api-specs/index.yaml`](api-specs/index.yaml) (OpenAPI 3.2) is the source of truth for
every route and request and response shape. The sibling Rust generator turns it into
the routers, schemas and HTTP tests under each `generated/` package. Handwritten
handlers in `src/handlers/` override the generated ones.

After changing the contract:

```sh
make lint-api
# yeah.. ill add this later
uv lock && uv sync
```

## Deploying

Production runs on Google Cloud Run in the `videos-service` project. A push to `main`
runs the checks, builds the images, runs new migrations after you approve them, and
deploys. [docs/deployment.md](docs/deployment.md) covers the setup, manual deploys,
smoke testing, and rollbacks. Secrets live in Secret Manager, never in the repo.
