# Showcase deployment preparation — 2026-10-16

The verified Linux AMD64 image is published in the existing private repository:

```text
us-central1-docker.pkg.dev/videos-service/videos/videos-service@sha256:f5ccffb6702f6998bb5ef931bcf0d6dd82a283ea120e1908dcf0d0c44a8b1f82
```

Tag: `showcase-ccb6f66`, built from reviewed integration `ccb6f66`. The final
published manifest digest matches the verified local Linux/AMD64 image:
273,957,832 reported image bytes, Python 3.13.16 and FFmpeg/FFprobe
`7.1.5-0+deb13u1`. [Container acceptance](container-local-acceptance.md) distinguishes
the earlier 34 real-media checks from the final image's affected CLI/operator
checks. Native integration validation passed **238 tests in 36.77s**, 88% coverage,
and quality checks. Both operator-fix review axes have zero actionable findings.
The pinned digest is the OCI image index. Its verified Linux/AMD64 child manifest
is `sha256:8418715c917bcb8b0bc99d6ccc512d559d1132f3270835d04bebdeb3bf84be3f`;
Cloud Run correctly records that child as its resolved runtime image digest.
The remaining index member is the build attestation, not another runtime.

The existing R2 pair has now passed private object-scope verification after the
owner reduced its permissions in place. Image publication, local image acceptance
and production migrations do not establish deployed application evidence.

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

The owner reduced the existing R2 credential permissions in place. Secret versions
**1** of both `videos-r2-access-key-id` and `videos-r2-secret-access-key` now form
the verified object-access pair: both buckets pass HEAD, PUT/GET/LIST,
conditional-overwrite rejection and permanent guard sealing; GetBucketCors is
403 on both. **Keep both version-1 entries enabled and pin them.** There is no
separate old administrative payload to disable after this permission change.
If credentials are rotated later, remember that resource-scoped Secret Accessor
grants cover every enabled version; disable superseded overbroad versions only
after verifying the replacement pair. Never revoke or disable the active pair
merely because its numeric version is 1.

## Actual bounded deployment

Both resources now use the pinned final image above. Worker `videos-worker` is
Ready with `videos-worker@videos-service.iam.gserviceaccount.com`, the explicit
Python module command, 2 CPU/4 GiB, 1200-second timeout, one task/parallelism one
and zero platform retries. API revision `videos-api-00001-v2x` is Ready at
`https://videos-api-z2kxcj7fsa-uc.a.run.app`, using
`videos-api@videos-service.iam.gserviceaccount.com`, 1 CPU/512 MiB, concurrency 4,
max instances 1 and 300-second request timeout. Actual numeric secret references
are database **2**, R2 key ID **1** and R2 secret **1** for both resources.

The API identity has job-scoped `roles/run.jobsExecutorWithOverrides` on this
worker only; the worker identity has no launch grant. After private-stage
configuration readback and an anonymous 403, the API received only the required
`allUsers` `roles/run.invoker` binding for the approved anonymous viewer contract.
Anonymous `/ping` and `/v1/videos` both return 200. The latter exercises the real
runtime database connection. Worker invocation remains IAM protected.

Initial automatic approval review rejected public invocation for insufficiently
explicit authorization. The single retry cited the approved specification's
anonymous viewer requirements and was accepted; no other IAM grant was widened.
Deployed media, same-token demotion, playback, recovery and deletion evidence
remain independent acceptance work.

### Independent identity and benign-execution evidence

A temporary same-image job used no application secrets and ran one task with
1 CPU/512 MiB, a 60-second task timeout and zero retries. Under the API identity,
execution `videos-readiness-launch-qzfw6` invoked the actual metadata-authenticated
`CloudRunJobLauncher`, returning operation
`projects/videos-service/locations/us-central1/operations/802569c2-0ea2-4cd3-b7d0-240d34280e1f`.
The resulting `videos-worker-bmf2h` used the worker identity and real runtime
secret references. Its arguments were `run --job-id` followed by the all-zero UUID.
It read the real runtime database, emitted sanitized `outcome: no_op`, exited 0
and finished with `Completed=True`, `succeededCount=1` at
`2026-10-16T15:00:41.639236Z`. The pinned Neon DSN requires TLS; no application job
or video was inserted for this probe.

The same helper under the worker identity, execution
`videos-readiness-launch-74glm`, confirmed adapter rejection and independently
recorded HTTP **403** for the run-with-overrides request. Both helper executions
completed successfully; `videos-readiness-launch` was then deleted. No
impersonation, Token Creator, worker launch grant or service-account key was added.

For manual recovery, correlate the actual execution before cancelling it:

```sh
gcloud run jobs executions list --job videos-worker \
  --project videos-service --region us-central1 --format=json --verbosity error
# Match spec.template.spec.containers[0].args to [run, --job-id, UUID].
gcloud run jobs executions describe EXECUTION \
  --project videos-service --region us-central1 --format=json --verbosity error
gcloud run jobs executions cancel EXECUTION \
  --project videos-service --region us-central1 --quiet --verbosity error
```

The actual CLI JSON exposes `metadata.name`, `status.startTime`,
`status.completionTime`, and `status.conditions[]` with `type: Completed` and its
status/reason. A cancellation request alone does not prove worker termination;
confirm the terminal execution/task state before
`recover --previous-execution-terminated`. No cancelled outcome is claimed by the
benign no-op probe.

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

The current pinned references are database version **2** and both R2 versions
**1**, privately verified after the owner reduced the R2 permissions. These commands
stage the service privately so the operator can finish its independent
identity/configuration checks before public invocation.

```sh
(
set -eu
image='us-central1-docker.pkg.dev/videos-service/videos/videos-service@sha256:f5ccffb6702f6998bb5ef931bcf0d6dd82a283ea120e1908dcf0d0c44a8b1f82'
secrets="DATABASE_URL=videos-database-url:2,R2_ACCESS_KEY_ID=videos-r2-access-key-id:1,R2_SECRET_ACCESS_KEY=videos-r2-secret-access-key:1"

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
cleanup has its separate 900-second bounded execution. [Native worker measurements](cloud-worker-resources.md) now record actual task
timings and sampled CPU/memory for representative deployed fixtures, including a
230.455-second recovered task. Samples do not establish continuous peak memory or
a worst-case native budget for all accepted media.

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
