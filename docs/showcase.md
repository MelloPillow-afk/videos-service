# Run the local interview showcase (MEL-15)

From the service repository root, run:

```sh
make showcase
```

The command runs two composed acceptance journeys, prints twelve numbered PASS
records, and exits nonzero if an assertion or real media command fails. It needs
no cloud credentials, web frontend, scheduler, or separate demonstration backend.
A normal run takes a few seconds once dependencies and PostgreSQL are ready.

## One-time local setup

Use Python 3.13, uv, PostgreSQL 17 or newer, and FFmpeg **plus FFprobe** on PATH.
FFmpeg must provide libx264, AAC, HLS/MPEG-TS, scale and pad support. Install the
locked Python environment and start the existing isolated test database:

```sh
make install
make test-db-up
ffmpeg -version
ffprobe -version
make showcase
```

`make test-db-up` uses Docker Compose's test profile on `127.0.0.1:5433`;
Docker must be running. An existing PostgreSQL test instance also works: set
`TEST_DATABASE_URL` privately to that dedicated database. The default is the
local URL in `.env.example`. This command creates fresh UUID-named application
and simulated Auth schemas and drops them after each journey; do not point it
at a production database. It does not migrate the application development or
cloud database. Test migrations execute the actual checked-in migration SQL.
If connection setup fails, start the database and check the selected test URL;
if FFmpeg is missing or lacks a codec, install the media tools and rerun.

## What runs, and what is controlled

| Real implementation | Controlled external boundary |
| --- | --- |
| FastAPI routes, request binding, validation, responses and lifecycle through HTTPX ASGI | No listening HTTP server or network ingress is required. |
| PostgreSQL repositories, transactions, role lookup, migrations, job audit and claims | An isolated local provider-schema fixture supplies current administrator membership. |
| JWT signatures, trusted issuer/audience and expiry verification | Ephemeral Ed25519 identity signing keys; no real Neon account or JWKS call. |
| Source/image authorization and confirmation business rules; real image decoding | Existing `MemoryStorage` models conditional direct PUT, object reads, lists and permanent guards. The upload is a direct-storage equivalent, not a browser or real signed R2 request. |
| Independent VIDEO, THUMBNAIL and DELETION worker entrypoints, persisted fences and retries | The launch provider creates separate asyncio tasks immediately when the app submits a job. Controlled execution gates make independence observable. No test later calls a media worker manually. |
| Real MP4 fixture generation, FFprobe inspection, FFmpeg HLS/renditions, generated image and HLS decode | A controlled HTTP delivery transport serves only the real worker-produced public bytes. It does not prove Cloudflare caching, CORS or browser-player behavior. |
| Real temporary-failure classification, three-execution budget and operator recovery use case | Storage/launch outages are injected at provider boundaries; retry delays are recorded as 1 and 4 seconds while the test clock advances without wall-clock waiting. |

The harness lives in `tests/integration/test_showcase.py` and reuses the existing
app, migrations, signing keys, storage, fixture generation and job-submission
interfaces. It is a test harness, not another production runtime. A request
observer checks the actual selected endpoint for every route; all thirteen,
including `/ping`, use handwritten handlers rather than generated examples.

## Journey and expected evidence

The first journey:

1. Creates a draft and proves anonymous detail is hidden and early publication
   is rejected. Upload instructions authorize a conditional storage write;
   confirmation returns 202 and directly submits both independent worker tasks.
2. Lets VIDEO reach READY/DRAFT while THUMBNAIL is delayed at the controlled
   execution boundary. Administrator playback preview succeeds; anonymous
   playback remains hidden. The private original remains intact.
3. Uploads and verifies an actual 1280×720 JPEG before generation finishes.
   The later real generated image cannot replace CUSTOM. Removing CUSTOM
   restores the decoded 1280×720 generated fallback.
4. Publishes and checks anonymous detail, list and playback. Fetches the actual
   master, both 360p/720p variant playlists and every referenced segment through
   the controlled delivery HTTP boundary, then decodes HLS with FFmpeg.
5. Changes the current provider role to `user`; the **same still-valid JWT**
   immediately receives 403 for mutation. Public viewing still works. Restores
   the role in the local provider fixture.
6. Requests deletion, observes DELETING and immediate visibility/mutation fences,
   and lets the submitted cleanup task finish. Every stored object is a verified
   zero-byte guard, resource reads/repeated DELETE return 404, and a late
   create-only source write fails.
7. Confirms all thirteen actual HTTP routes selected handwritten endpoints.

The second journey:

8. Injects three delivery-write failures. Three real VIDEO executions exhaust
   their application budget with increasing recorded delays, FAILED status,
   sanitized error and cumulative attempt manifests.
9. Demonstrates generated THUMBNAIL success independently of VIDEO failure,
   with the validated retained private source available for recovery.
10. Calls HTTP `:retry`; a new job/namespace is QUEUED/DRAFT. A controlled launch
    outage leaves LAUNCH_FAILED/LAUNCH_UNCONFIRMED with zero executions. Database
    acceptance is observable even though dispatch did not succeed.
11. Invokes the actual operator recovery use case and submits that same current
    job. The launch boundary executes the real worker; READY/DRAFT and decoded
    HLS follow. No extra thumbnail job is created. The production command for
    this use case is described in [processing recovery](mel-10-acceptance.md).
12. Deletes the recovered video, guards failed-attempt keys as well as successful
    outputs and uploads, and observes eventual 404.

The printed `PLAYBACK COPY` absolute path points to a retained pytest temporary
client download. Open its `master.m3u8` in an existing HLS-capable player such as
VLC, or run `ffplay '<printed absolute path>'` if ffplay is installed. The automated
proof is real HLS decoding; an interactive player is optional local inspection.
This client-side copy can survive provider deletion, just as previously downloaded
or CDN-cached bytes can. It is not a live media origin. Pytest rotates temporary
artifacts on later runs; no media is added to Git.

## Limits and separate live acceptance

The source defaults are 100 MiB and 300 seconds; custom images accept JPEG, PNG
and WebP up to 5 MiB with exact 1280×720 dimensions. Feature acceptance exercises
actual limits, corruption, aspect ratio/no-upscale behavior, audio ending policy,
concurrency and late writers; the showcase composes representative small media.

Declared and observed upload-size checks are **admission**, not a transfer ceiling:
oversized objects can reach storage but cannot enter processing. Persisted work
and job claims protect state; direct launch is not durable dispatch. Interrupted
or uncertain submissions require operator inspection and explicit recovery.
A stuck RUNNING claim requires confirmation its previous execution terminated;
no elapsed lease, cron, periodic reconciliation or automatic orphan cleanup exists.

Publication controls API discovery, not CDN authorization. Cached or downloaded
public bytes can survive unpublication/deletion. Explicit deletion overwrites
media with permanent zero-byte guards before removing records; guard objects
remain indefinitely to reject late conditional writes. Never expire or blanket
remove those guards.

This command does not close MEL-7 or MEL-16. Real Neon sign-in/role demotion,
least-required runtime privileges, actual R2 privacy and browser CORS/signed PUTs,
Cloud Run images/identities/independent executions, CDN/player playback and live
guard deletion remain [separate cloud acceptance](cloud-readiness.md). No live
success is inferred from this controlled run.

## Executed local evidence — 2026-10-16

On integration base `29f2f1f` plus this showcase implementation:

- `make showcase`: both journeys passed, twelve PASS records, real 360p/720p HLS
  decoding and the displayed local client-copy path (1.52 seconds).
- `make check`: 46 OpenAPI examples validated; Ruff lint/format and strict Pyright
  passed with zero errors.
- `make test-all`: all 219 HTTP, PostgreSQL, migrations, real-media and unit cases
  passed in 35.53 seconds; aggregate application coverage 87%.

No HTTP contract shape changed. Renewable output was left intact; the final
integration regeneration check is tracked separately after concurrent local
packaging work. No cloud credential or live-provider result is implied here.
