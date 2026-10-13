# Videos service

The Python backend boundary for the videos domain. Development follows
contract-first architecture: change and validate the HTTP contract before
implementing behavior. The service framework and deployment code will be selected
during implementation.

The authoritative HTTP contract is [`api/index.yaml`](api/index.yaml).
It uses [OpenAPI 3.2.0](https://spec.openapis.org/oas/v3.2.0.html), with JSON Schema
null unions, reusable schemas and responses, bearer authentication, and examples
for all 12 operations. Paths are relative to the `/v1` server base path.
JSON fields, operation IDs, and component names use snake_case. Schemas are grouped
by purpose inside `api/schemas/`. Each schema has one example. A single video uses
[`videos/video.yaml`](api/schemas/videos/video.yaml); a collection uses
[`videos/videos.yaml`](api/schemas/videos/videos.yaml).

| Schema folder | Contents |
| --- | --- |
| `videos/` | Video resources, collections, metadata, status, updates, retries, and deletion. |
| `uploads/` | Video uploads, upload instructions, and completion or processing results. |
| `thumbnails/` | Thumbnail resources, image status, and custom thumbnail uploads. |
| `playback/` | Video playback links. |
| `shared/` | Timestamps and media URLs. |

Each query or path parameter has a definition in `api/parameters/`. IDs, pagination,
and search schemas are written directly in those files for readability. Video
status filters reuse the status schemas in `api/schemas/videos/`. Pass the collection's
`next_page_token` as the `cursor` query parameter to request the next page.
The common API error schema is defined in `api/index.yaml`. Processing failure
details are defined directly in `api/schemas/videos/video.yaml`.

## Validate the contract

Install [uv](https://docs.astral.sh/uv/) and use Python 3.12 or newer. From this
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
uv run --locked yamllint api
uv run --locked openapi-spec-validator --schema 3.2 api/index.yaml
uv run --locked python scripts/check_examples.py
```

## Requirements and unresolved decisions

The source requirements are [`video-backend-spec.md`](../docs/video-backend-spec.md),
its [consolidated specification](../.scratch/video-backend/spec.md), and the
[approved API examples](../docs/pilgrims-progress-video-api-spec.md).
`AGENTS.md` defines the contract-first workflow for this service.

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
