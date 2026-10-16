# Showcase deployment preparation — 2026-10-16

The verified Linux AMD64 image is published in the existing private repository:

```text
us-central1-docker.pkg.dev/videos-service/videos/videos-service@sha256:36a70c7ed98f4c983f9a29725cb50ed329e269a177911f2bbe759f11c0793064
```

Tag: `showcase-9b682d3`. The published manifest digest matches the actual locally
verified image. Integration `9b682d3` has identical runtime/build inputs to that
image; its later changes normalize generated test metadata and record reviews.
[Image and media evidence](container-local-acceptance.md) includes 34 representative
Linux checks and the final nine CLI checks. Final native validation passed all
228 tests, quality checks, the showcase, and deterministic generation.

This is a published checkpoint. The local operator `recover --gcloud-auth` change
is being verified separately; rebuild and publish its reviewed source before
calling an image final or deploying it. Update the pinned digest below at that
point. Service/job deployment remains gated on the scoped R2 pair.

Artifact Registry credential configuration added only the
`us-central1-docker.pkg.dev` gcloud helper; all unrelated Docker settings were
preserved. Registry and project IAM readback contain no `allUsers` or
`allAuthenticatedUsers` bindings. The target is project `videos-service`, region `us-central1`, existing
Docker repository `videos`. Publishing added an image to that repository.

## Current production state

The owner connection explicitly applied five migrations through the verified
**direct** Neon endpoint. Exactly `videos`, `upload_attempts`, and `jobs` plus four
Yoyo bookkeeping tables exist. The separate `videos_runtime` login has DML on
those three tables and column SELECT on Auth `id`/`role`. Checks deny schema CREATE,
Auth writes/private email reads, and migration-bookkeeping writes.

Secret `videos-database-url` version **2** now holds the runtime connection.
Owner-credential version **1** was reversibly disabled. Pin version 2 in both
runtime definitions; never use `latest` or the migration owner for runtime access.
The migration connection stays separate and private.

**Deployment gate:** R2 runtime credentials still need private verification. The
last observed versions of `videos-r2-access-key-id` and
`videos-r2-secret-access-key` were version 1, containing the administrative setup
pair. Both replacements must form a matching Object Read & Write pair scoped to
`videos-raw` and `videos-processed`, with bucket administration denied. Preserve
setup access for configuration; do not deploy it as the runtime pair.

No API service or worker job has been deployed at this checkpoint. Record their
actual revisions, secret versions, identities and executions when that gate clears.

## Exact runtime configuration

Prepared private environment files are
`/private/tmp/videos-showcase-secrets/api-env.yaml` and `worker-env.yaml`, mode 0600.
They contain settings only; secret payloads are separate Secret Manager references.
Recreate equivalent private YAML files for another machine using these inputs:

| Setting | API | Worker |
| --- | --- | --- |
| `DB_SCHEMA` | `public` | `public` |
| `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE` | `0` / `2` | `0` / `1` |
| `DB_CONNECT_TIMEOUT_SECONDS` / `DB_POOL_TIMEOUT_SECONDS` | `5` / `5` | `5` / `5` |
| `DB_STATEMENT_TIMEOUT_MS` | `5000` | `5000` |
| `R2_ENDPOINT_URL` | Supplied account's default-jurisdiction S3 endpoint | Same |
| `R2_PRIVATE_BUCKET` / `R2_PUBLIC_BUCKET` | `videos-raw` / `videos-processed` | Same |
| `SOURCE_MAX_BYTES` / `SOURCE_MAX_DURATION_SECONDS` | `104857600` / `300` | Same |
| `THUMBNAIL_MAX_BYTES` | `5242880` | Same |
| `AUTH_SCHEMA` | `neon_auth` | Not needed for execution |
| `AUTH_ISSUER` / `AUTH_AUDIENCE` | `https://ep-wandering-art-b483xg29.neonauth.c-6.us-east-2.aws.neon.tech` | Not needed |
| `AUTH_JWKS_URL` | `https://ep-wandering-art-b483xg29.neonauth.c-6.us-east-2.aws.neon.tech/neondb/auth/.well-known/jwks.json` | Not needed |
| `CDN_ORIGIN` | `https://pub-1296a4df37cd4d52aacd2941d8b36687.r2.dev` | Not needed |
| `CLOUD_RUN_JOB_RESOURCE` | `projects/videos-service/locations/us-central1/jobs/videos-worker` | Normal worker does not launch work |
| `MEDIA_THREADS` / `MEDIA_RETRY_DELAYS_SECONDS` | Defaults unused by ordinary HTTP | `2` / `[1,4]` |
| `CLEANUP_RUNTIME_SECONDS` / `CLEANUP_RETRY_DELAYS_SECONDS` | Defaults unused by ordinary HTTP | `900` / `[1,4,16,30]` |

YAML environment values must be strings. `DATABASE_URL`, `R2_ACCESS_KEY_ID` and
`R2_SECRET_ACCESS_KEY` are supplied exclusively by the pinned secret references.
The selected public `r2.dev` origin is the owner-approved rate-limited development
endpoint; custom-domain edge caching/access features are unavailable there.

Both buckets retain only their existing default seven-day incomplete-multipart
abort rule. No object-expiration action is configured, so those rules do not
remove permanent guards. The application uses single-object PUTs; no lifecycle
rule was added or changed.

## Guarded deployment commands

Execute only after confirming the matching scoped R2 pair and recording its exact
**numeric** versions in `R2_KEY_VERSION` and `R2_SECRET_VERSION`. Current version 1
is unsuitable. These commands stage the service privately so the operator can
finish its independent identity/configuration checks before public invocation. The commands currently reference the published checkpoint;
replace its digest with the reviewed operator-recovery image before execution.

```sh
(
set -eu
: "${R2_KEY_VERSION:?Set the verified object-scoped key-ID version}"
: "${R2_SECRET_VERSION:?Set the verified matching object-secret version}"
test "$R2_KEY_VERSION" -gt 1
test "$R2_SECRET_VERSION" -gt 1
image='us-central1-docker.pkg.dev/videos-service/videos/videos-service@sha256:36a70c7ed98f4c983f9a29725cb50ed329e269a177911f2bbe759f11c0793064'
secrets="DATABASE_URL=videos-database-url:2,R2_ACCESS_KEY_ID=videos-r2-access-key-id:$R2_KEY_VERSION,R2_SECRET_ACCESS_KEY=videos-r2-secret-access-key:$R2_SECRET_VERSION"

gcloud run jobs deploy videos-worker --project videos-service --region us-central1 \
  --image "$image" \
  --service-account videos-worker@videos-service.iam.gserviceaccount.com \
  --command /app/.venv/bin/python,-m,src.worker \
  --args run,--job-id,00000000-0000-0000-0000-000000000000 \
  --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 1200s \
  --cpu 2 --memory 4Gi \
  --env-vars-file /private/tmp/videos-showcase-secrets/worker-env.yaml \
  --set-secrets "$secrets" --quiet --verbosity error

gcloud run jobs add-iam-policy-binding videos-worker \
  --project videos-service --region us-central1 \
  --member serviceAccount:videos-api@videos-service.iam.gserviceaccount.com \
  --role roles/run.jobsExecutorWithOverrides --quiet --verbosity error

gcloud run deploy videos-api --project videos-service --region us-central1 \
  --image "$image" \
  --service-account videos-api@videos-service.iam.gserviceaccount.com \
  --port 8080 --cpu 1 --memory 512Mi --concurrency 4 \
  --min-instances 0 --max-instances 1 --timeout 300s \
  --env-vars-file /private/tmp/videos-showcase-secrets/api-env.yaml \
  --set-secrets "$secrets" --no-allow-unauthenticated --quiet --verbosity error
)
```

Creating the worker does not execute it. Its placeholder all-zero job ID is a
benign no-claim default if explicitly executed; ordinary launches override the
arguments with the real committed job ID. Keep the module invocation in the
**command** array: launcher argument overrides must not remove `-m src.worker`.
The worker identity receives no job-launch grant. Existing resource-scoped secret
accessor grants cover both runtime identities; do not restore project Editor.

After inspecting the deployed revision/settings and arranging live acceptance,
public viewing requires the API's invoker binding:

```sh
gcloud run services add-iam-policy-binding videos-api \
  --project videos-service --region us-central1 \
  --member allUsers --role roles/run.invoker --quiet --verbosity error
```

Application admin operations still require verified Neon identity/current role;
jobs remain IAM protected. Confirm organization policy permits public invocation.
Use metadata/ADC service identity; service-account keys are unnecessary.

## Execution policy and remaining proof

Worker allocation is the initial explicit **2 CPU / 4 GiB / 1200 seconds**, one task,
parallelism one and **zero platform retries**. The launcher also sends a 1200-second
override. Application media retries own the persisted three-attempt budget;
cleanup has its separate 900-second bounded execution. Representative local
fixtures do not establish worst-case native Cloud Run memory or duration. Record
actual native measurements before describing that allocation as sufficient for
all accepted media.

One task/parallelism one does not cap separate simultaneous job executions. For
the bounded demonstration, admit one source upload at a time and wait for both
independent media jobs before the next upload; allow an additional cleanup
execution when demonstrating in-flight fencing. API max-instances one and per-
process pools above bound each process, not a global fleet connection count.

Verify deployment metadata and secret versions without reading payloads. Then
record API-identity launch with arguments, operation/execution reference, worker
identity, TLS database connectivity, terminal outcome and persisted state; also
verify denied launch. Explicit CLI `recover` needs a launch-capable API/operator
identity context. On a local operator machine with the intended gcloud account
authenticated and `run.jobs.runWithOverrides` granted on this job, use:

```sh
uv run --locked python -m src.worker recover --job-id UUID --gcloud-auth
```

Add `--previous-execution-terminated` only after verifying termination of a
stranded RUNNING execution. `--gcloud-auth` captures the installed CLI token
without logging it and is valid only for recovery. Without it, the launcher
continues to use runtime metadata identity, with no local-account fallback.
Running recovery under the normal worker identity does not grant launch access.

Live MEL-16 still requires deployed HTTP token/demotion, independent real media
jobs, HLS player playback through public delivery, retained originals, manual
recovery, guarded deletion and native termination/resource evidence. No scheduler,
periodic reconciliation, automatic migration or lifecycle cleanup is introduced.

References: [Cloud Run job service identity](https://docs.cloud.google.com/run/docs/configuring/jobs/service-identity),
[Cloud Run runtime contract](https://docs.cloud.google.com/run/docs/container-contract),
[Secret references](https://docs.cloud.google.com/run/docs/configuring/services/secrets).
