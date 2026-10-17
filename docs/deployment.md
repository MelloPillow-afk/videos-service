# Deploying to Cloud Run with Cloudflare R2

The API runs as a Cloud Run **service**. Each media job runs as one execution of a Cloud
Run **job**, which the API starts directly (no queue). Both images come from the
`Dockerfile`. Commands below assume these shell variables:

```sh
PROJECT=your-project
REGION=us-central1
REPO=$REGION-docker.pkg.dev/$PROJECT/videos
TAG=$(git rev-parse --short HEAD)
```

## 1. Cloudflare R2

1. Buckets: `videos-raw` (private uploads) and `videos-processed` (public media).
2. Give `videos-processed` public access through a custom domain (or `r2.dev` for
   testing). That origin is `MEDIA_BASE_URL`, for example `https://media.example.com`.
3. Create an R2 API token with **Object Read & Write** on both buckets. Its access key
   ID and secret are `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY`; the S3 endpoint
   `https://<account-id>.r2.cloudflarestorage.com` is `R2_ENDPOINT_URL`.
4. CORS. Browsers upload straight to `videos-raw` and play from `videos-processed`:
   - `videos-raw`: [r2-raw-cors.json](r2-raw-cors.json), with your client origins.
   - `videos-processed`: [r2-processed-cors.json](r2-processed-cors.json).

## 2. Images

```sh
gcloud artifacts repositories create videos --repository-format=docker --location=$REGION
gcloud auth configure-docker $REGION-docker.pkg.dev
docker buildx build --platform linux/amd64 --target api -t $REPO/api:$TAG --push .
docker buildx build --platform linux/amd64 --target worker -t $REPO/worker:$TAG --push .
```

## 3. Secrets and service accounts

```sh
printf %s "$DATABASE_URL" | gcloud secrets create database-url --data-file=-
printf %s "$R2_ACCESS_KEY_ID" | gcloud secrets create r2-access-key-id --data-file=-
printf %s "$R2_SECRET_ACCESS_KEY" | gcloud secrets create r2-secret-access-key --data-file=-

gcloud iam service-accounts create videos-api
gcloud iam service-accounts create videos-worker
for account in videos-api videos-worker; do
  for secret in database-url r2-access-key-id r2-secret-access-key; do
    gcloud secrets add-iam-policy-binding $secret \
      --member=serviceAccount:$account@$PROJECT.iam.gserviceaccount.com \
      --role=roles/secretmanager.secretAccessor
  done
done
```

## 4. Worker job

One task, no Cloud Run retries (a failed job records its message instead), and a
timeout that covers a 300-second source at three renditions.

```sh
gcloud run jobs deploy videos-worker \
  --image=$REPO/worker:$TAG --region=$REGION \
  --service-account=videos-worker@$PROJECT.iam.gserviceaccount.com \
  --tasks=1 --max-retries=0 --task-timeout=30m --cpu=2 --memory=4Gi \
  --set-env-vars=R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com,AUTH_DISABLED=true \
  --set-secrets=DATABASE_URL=database-url:latest,R2_ACCESS_KEY_ID=r2-access-key-id:latest,R2_SECRET_ACCESS_KEY=r2-secret-access-key:latest
```

The worker serves no HTTP, so `AUTH_DISABLED=true` only skips token settings it never
uses. The API passes each execution its job ID as the container argument.

Let the API start executions with that argument:

```sh
gcloud run jobs add-iam-policy-binding videos-worker --region=$REGION \
  --member=serviceAccount:videos-api@$PROJECT.iam.gserviceaccount.com \
  --role=roles/run.jobsExecutorWithOverrides
```

## 5. API service

```sh
gcloud run deploy videos-api \
  --image=$REPO/api:$TAG --region=$REGION --allow-unauthenticated \
  --service-account=videos-api@$PROJECT.iam.gserviceaccount.com \
  --env-vars-file=api.env.yaml \
  --set-secrets=DATABASE_URL=database-url:latest,R2_ACCESS_KEY_ID=r2-access-key-id:latest,R2_SECRET_ACCESS_KEY=r2-secret-access-key:latest
```

`api.env.yaml` (not committed) holds the plain settings:

```yaml
API_ENV: prod
GCP_PROJECT: your-project
GCP_REGION: us-central1
WORKER_JOB_NAME: videos-worker
R2_ENDPOINT_URL: https://<account-id>.r2.cloudflarestorage.com
MEDIA_BASE_URL: https://media.example.com
AUTH_ISSUER: https://ep-example.neonauth.us-east-1.aws.neon.tech
AUTH_JWKS_URL: https://ep-example.neonauth.us-east-1.aws.neon.tech/neondb/auth/.well-known/jwks.json
AUTH_AUDIENCE: https://ep-example.neonauth.us-east-1.aws.neon.tech
```

Run migrations before routing traffic to a new revision:

```sh
gcloud run jobs deploy videos-migrate --image=$REPO/api:$TAG --region=$REGION \
  --service-account=videos-api@$PROJECT.iam.gserviceaccount.com \
  --command=python --args=-m,src.repositories.migrate,apply \
  --set-env-vars=AUTH_DISABLED=true --set-secrets=DATABASE_URL=database-url:latest \
  --execute-now --wait
```

## Recovering a stuck job

If the API stops between queuing a job and starting it, the job stays `QUEUED`. Start
it by hand:

```sh
gcloud run jobs execute videos-worker --region=$REGION --args=<job_id>
```

A worker killed mid-run (for example, out of memory) leaves its job `RUNNING`. Mark it
failed in the database, then delete and recreate the video.
