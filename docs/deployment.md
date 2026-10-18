# Deploying to Cloud Run with Cloudflare R2

The API runs as the Cloud Run **service** `videos-api`. Each media job runs as one
execution of the Cloud Run **job** `videos-worker`, which the API starts directly (no
queue). Migrations run as the job `videos-migrate`. All three come from the
`Dockerfile`: `api` (also used for migrations) and `worker` (adds FFmpeg).

Pushes to `main` deploy through GitHub Actions ([CI](../.github/workflows/ci.yml)); see
[Pipeline](#pipeline). The sections below record the one-time setup and the equivalent
manual commands. They assume:

```sh
PROJECT=videos-service
REGION=us-central1
IMAGES=$REGION-docker.pkg.dev/$PROJECT/videos
TAG=$(git rev-parse HEAD)
```

## Configuration

Plain settings live in [deploy/env.yaml](../deploy/env.yaml) and are reviewed like code.
Secrets live in Secret Manager:

| Secret | Holds | Read by |
|---|---|---|
| `videos-database-url` | Neon **direct** URL as `videos_runtime` (rows only) | `videos-api`, `videos-worker` |
| `videos-migrate-database-url` | Neon **direct** URL as `neondb_owner` (schema changes) | `videos-migrate` |
| `videos-r2-access-key-id`, `videos-r2-secret-access-key` | R2 API token | `videos-api`, `videos-worker` |

Both database URLs use Neon's direct host, not `-pooler`: the app sets session options
when it connects, and the pooler rejects them. See
[ADR 0001](adr/0001-direct-database-connections.md). `--max-instances=10` on the API keeps
the connection count well under Neon's direct-connection limit.

`videos_runtime` can't change the schema. Tables the owner creates grant it row access
automatically, through a one-time setting:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO videos_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE neondb_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO videos_runtime;
```

To store or rotate a secret, copy the value and run:

```sh
pbpaste | gcloud secrets versions add <secret> --data-file=- --project $PROJECT
```

## Cloudflare R2

1. Buckets: `videos-raw` (private uploads) and `videos-processed` (public media).
2. `videos-processed` is public through its `r2.dev` origin, which is `MEDIA_BASE_URL`.
3. The R2 API token has **Object Read & Write** on both buckets.
4. CORS. Browsers upload straight to `videos-raw` and play from `videos-processed`:
   - `videos-raw`: [r2-raw-cors.json](r2-raw-cors.json), with your client origins.
   - `videos-processed`: [r2-processed-cors.json](r2-processed-cors.json).

The API's own CORS origins are `CORS_ALLOWED_ORIGINS` in
[deploy/env.yaml](../deploy/env.yaml): the same frontend origin as `videos-raw`.

## Neon Auth sign-up

Reviewers sign in with accounts created in advance, so public sign-up stays off:

```sh
neon neon-auth config email-password update --disable-sign-up --project-id <id> --branch <branch>
```

Check both sides. With `AUTH_URL` the Auth URL (`AUTH_JWKS_URL` without
`/.well-known/jwks.json`) and `ORIGIN` a trusted domain, a sign-up attempt fails:

```sh
curl -i -X POST "$AUTH_URL/sign-up/email" -H "Origin: $ORIGIN" -H 'Content-Type: application/json' \
  -d '{"email": "new@example.com", "password": "not-an-account-1", "name": "New"}'
```

An account created in advance still signs in and reaches the admin API:

```sh
TOKEN=$(uv run --locked python scripts/get_token.py --email you@example.com --origin "$ORIGIN")
curl -i -H "Authorization: Bearer $TOKEN" https://videos-api-749098550492.us-central1.run.app/v1/admin/videos
```

## Service accounts

| Account | Runs | Can |
|---|---|---|
| `videos-api` | the API | read its secrets; start `videos-worker` executions with overrides |
| `videos-worker` | the worker | read its secrets |
| `videos-migrate` | migrations | read `videos-migrate-database-url` |
| `github-deployer` | GitHub Actions on `main` | push images; deploy and run Cloud Run services and jobs as the three accounts above |

`github-deployer` has no stored key. GitHub Actions gets it through Workload Identity
Federation, limited to this repository's `main` branch.
[deploy/setup-wif.sh](../deploy/setup-wif.sh) records how that was set up.

## Pipeline

[CI](../.github/workflows/ci.yml) runs on every pull request and every push to `main`:

1. **Checks**: lint, format, types, tests, and an `api` and `worker` image build.
   Pull requests stop here.
2. **Images**: on `main`, both images are pushed as `api:<sha>` and `worker:<sha>`.
3. **Find new migrations**: compares `migrations/` between the commit the API runs
   (its `commit-sha` label) and the pushed commit.
4. **Apply migrations**: only when step 3 finds changes. It waits for approval on the
   `production` GitHub environment, then runs `videos-migrate`. Migrations must keep
   the running code working: add first, remove in a later release.
5. **Deploy**: the worker job, then the API, both labelled `commit-sha=<sha>`, then a
   `/ping` check.

## Manual deploy

Build and push:

```sh
gcloud auth configure-docker $REGION-docker.pkg.dev
docker buildx build --platform linux/amd64 --target api -t $IMAGES/api:$TAG --push .
docker buildx build --platform linux/amd64 --target worker -t $IMAGES/worker:$TAG --push .
```

Migrations, when there are new ones:

```sh
gcloud run jobs deploy videos-migrate --image=$IMAGES/api:$TAG --region=$REGION \
  --service-account=videos-migrate@$PROJECT.iam.gserviceaccount.com \
  --command=python --args=-m,src.repositories.migrate,apply \
  --tasks=1 --max-retries=0 --task-timeout=10m \
  --env-vars-file=deploy/env.yaml \
  --set-secrets=DATABASE_URL=videos-migrate-database-url:latest \
  --labels=commit-sha=$TAG --execute-now --wait
```

The worker job runs one task with no Cloud Run retries (a failed job records its
message instead). Its timeout covers a 300-second source at three renditions:

```sh
SECRETS=DATABASE_URL=videos-database-url:latest,R2_ACCESS_KEY_ID=videos-r2-access-key-id:latest,R2_SECRET_ACCESS_KEY=videos-r2-secret-access-key:latest

gcloud run jobs deploy videos-worker --image=$IMAGES/worker:$TAG --region=$REGION \
  --service-account=videos-worker@$PROJECT.iam.gserviceaccount.com \
  --tasks=1 --max-retries=0 --task-timeout=30m --cpu=2 --memory=4Gi \
  --env-vars-file=deploy/env.yaml --set-secrets=$SECRETS --labels=commit-sha=$TAG

gcloud run deploy videos-api --image=$IMAGES/api:$TAG --region=$REGION \
  --service-account=videos-api@$PROJECT.iam.gserviceaccount.com \
  --max-instances=10 \
  --env-vars-file=deploy/env.yaml --set-secrets=$SECRETS --labels=commit-sha=$TAG
```

The API passes each worker execution its job ID as the container argument, which needs:

```sh
gcloud run jobs add-iam-policy-binding videos-worker --region=$REGION \
  --member=serviceAccount:videos-api@$PROJECT.iam.gserviceaccount.com \
  --role=roles/run.jobsExecutorWithOverrides
```

## Smoke test

[scripts/smoke.py](../scripts/smoke.py) runs one video through a deployed service:
upload, processing, thumbnail, publishing, and HLS playback. It then deletes the video.
It writes to production, so run it by hand rather than on every deploy:

```sh
TOKEN=$(uv run --locked python scripts/get_token.py --email you@example.com)
TOKEN=$TOKEN uv run --locked python scripts/smoke.py https://videos-api-749098550492.us-central1.run.app
```

## Rolling back

Cloud Run keeps earlier API revisions. Send traffic back to one:

```sh
gcloud run revisions list --service=videos-api --region=$REGION
gcloud run services update-traffic videos-api --region=$REGION --to-revisions=<revision>=100
```

For the worker, redeploy `videos-worker` with an earlier `worker:<sha>` image. A rollback
doesn't undo migrations.

## Recovering a stuck job

If the API stops between queuing a job and starting it, the job stays `QUEUED`. Start
it by hand:

```sh
gcloud run jobs execute videos-worker --region=$REGION --args=<job_id>
```

A worker killed mid-run (for example, out of memory) leaves its job `RUNNING`. Mark it
failed in the database, then delete and recreate the video.
