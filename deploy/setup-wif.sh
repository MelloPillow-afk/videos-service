#!/usr/bin/env bash
# One-time setup letting GitHub Actions on main deploy without a stored key.
#
# GitHub signs a short-lived OIDC token per run naming the repo and ref. Google's STS
# trades it for an hour-long credential as github-deployer, but only for this repo's
# main branch. Already run against videos-service; kept as the record of what exists.
set -euo pipefail

PROJECT=videos-service
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
REGION=us-central1
REPO=MelloPillow-afk/videos-service
# Numeric IDs survive renames; a name can be re-registered by someone else.
OWNER_ID=242214051
DEPLOYER=github-deployer@$PROJECT.iam.gserviceaccount.com

gcloud services enable sts.googleapis.com iamcredentials.googleapis.com --project $PROJECT

gcloud iam workload-identity-pools create github \
  --location=global --display-name="GitHub Actions" --project $PROJECT

# Rejects tokens from any other repo before any IAM binding is consulted.
gcloud iam workload-identity-pools providers create-oidc videos-service \
  --workload-identity-pool=github --location=global --project $PROJECT \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repo_ref=assertion.repository+'@'+assertion.ref" \
  --attribute-condition="assertion.repository_owner_id=='$OWNER_ID' && assertion.repository=='$REPO'"

gcloud iam service-accounts create github-deployer \
  --display-name="GitHub Actions deployer" --project $PROJECT

# Push images, deploy and execute Cloud Run services and jobs, and run them as the
# runtime accounts. No secret, database, or IAM-policy access.
gcloud artifacts repositories add-iam-policy-binding videos \
  --location=$REGION --project $PROJECT \
  --member=serviceAccount:$DEPLOYER --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding $PROJECT \
  --member=serviceAccount:$DEPLOYER --role=roles/run.developer --condition=None
for runtime in videos-api videos-worker videos-migrate; do
  gcloud iam service-accounts add-iam-policy-binding $runtime@$PROJECT.iam.gserviceaccount.com \
    --project $PROJECT --member=serviceAccount:$DEPLOYER --role=roles/iam.serviceAccountUser
done

# Only runs on main may become the deployer; pull request runs cannot.
gcloud iam service-accounts add-iam-policy-binding $DEPLOYER --project $PROJECT \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repo_ref/$REPO@refs/heads/main"
