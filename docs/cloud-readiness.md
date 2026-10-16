# Showcase cloud readiness (MEL-7)

Checked 2026-10-16. **Live readiness is incomplete.** This records setup inputs,
provider facts, and the evidence needed to finish MEL-7. It does not certify a
deployment or the live showcase. Local application tickets can proceed with real
PostgreSQL and FFmpeg and controlled external provider boundaries.

## Actual evidence

| Check | Observed result |
| --- | --- |
| Process configuration | No Neon, Cloudflare/R2, Google Cloud, or database credential variable names found. Values were not printed. |
| Main checkout environment files | `.env`, `.env.local`, `.env.production`, and `.env.production.local` absent. The ticket worktree also has no `.env`. |
| Provider tools | `gcloud`, `wrangler`, `neonctl`, and `psql` absent from PATH. Node/npm and Docker present. |
| Standard credential locations | `~/.config/gcloud`, `~/.config/neonctl`, `~/.config/.wrangler`, `~/.wrangler`, and `~/.aws/credentials` absent. Other credential stores were not searched. |
| Local artifacts | CORS examples parse as JSON. Read-only inspection SQL executes against local PostgreSQL 17; no `neon_auth` tables there, so this validates syntax only. `git diff --check` passes. |
| Remote configuration changes | None; no target account IDs, endpoints, existing billing confirmation, or usable credentials supplied. |
| Target verification | Neon schema/token/admin, R2 privacy/CORS/overwrite protection, and Cloud Run identities/launch all **unexecuted**. |

No provider setup can be verified from provider documentation alone. Keep MEL-7
open until the target checks below have dated, sanitized evidence.

## Required inputs and owner actions

Record non-secret IDs here when supplied. Deliver credentials through a local
ignored environment file or secret manager; never paste passwords, tokens,
signed upload URLs, or authorization headers into tickets, logs, or this file.

| Area | Exact inputs still missing | Access / owner action |
| --- | --- | --- |
| Neon account | Organization/account, project ID, branch ID, database name, provider region, existing plan/billing confirmation | Owner selects an existing showcase target; enables Auth on that branch if needed. Do not migrate a legacy provider implicitly. |
| Neon connection | TLS PostgreSQL runtime connection and separate migration connection; runtime database role; allowed network path from Cloud Run | Runtime role needs application DML and current-role reads; migration role needs application schema DDL. Neither role needs Auth user-write privileges. Owner supplies scoped access. |
| Neon identity | Auth provider/version, exact Auth base URL, trusted issuer, JWKS URL, audience, algorithm, token lifetime; demonstration user ID | Owner assigns first admin in Auth → Users → Make admin. API runtime must never assign itself admin. |
| Cloudflare account | Account ID, existing R2 activation/billing confirmation, bucket jurisdiction/location | Owner enables R2 if absent; purchasing/plan expansion is owner-only. |
| R2 storage | Two distinct bucket names: private uploads/source and public delivery; S3 endpoint for the selected jurisdiction | Scoped Object Read & Write credentials for these buckets; separate bucket-configuration permission only for setup. Owner can apply configuration instead of providing account-wide credentials. |
| CDN / browser | Cloudflare zone ID, delivery hostname/origin, DNS control, exact uploader/player origins including localhost ports | Owner connects delivery custom domain in the bucket's account and authorizes DNS/cache changes. Never connect the private bucket. |
| Google account | Project ID and number, region, existing billing-enabled confirmation, quota/resource budget | Owner enables Cloud Run, Artifact Registry, and Secret Manager APIs if needed. No billing-account linking or quota expansion performed automatically. |
| Deployment / runtime | Deployer principal, registry repository, API service name, worker job name(s), API and worker service-account emails, secret resource names and versions | Owner grants the scoped bindings below or provides a deployer that can apply them. No service-account key files are required. |

## Neon identity gate

The intended integration is managed Better Auth, not legacy Stack Auth. Neon's
current documentation reports Better Auth **1.7.6** server with 1.6 SDK-client
compatibility. This is a researched baseline, **not the target's verified version**.
Confirm the selected branch before enabling real administrative requests.
[Neon provider/version](https://neon.com/docs/auth/about),
[Auth management API](https://neon.com/docs/auth/guides/manage-auth-api).

Neon's JWT guide describes Ed25519/EdDSA access tokens with a 15-minute lifetime.
JWKS is `<auth-base>/.well-known/jwks.json`; the issuer is the Auth URL's **origin**,
excluding its database/auth path. Its example audience is that same origin.
Pin the actual trusted values supplied by the target, require valid identity and
lifetime claims, and validate the applicable audience. Do not derive trust from
an unverified incoming token or accept arbitrary algorithms.
[Neon JWT verification](https://neon.com/docs/auth/guides/plugins/jwt).

Run [the read-only schema inspection](cloud/neon-auth-inspect.sql) against the
target branch. It returns metadata, not user rows. After confirming the columns,
verify that the verified token subject maps to `neon_auth."user".id` and that
the runtime role can read the current role. Better Auth documents a text `role`
field with comma-separated membership; match the exact `admin` member, not a
substring. Check actual role encoding and ban fields in the target. The JWT's
`authenticated` role is not administrator authority. Missing rows, schema mismatch,
and lookup failures must not grant access. Do not create provider-owned tables in
application migrations. [Neon flow/schema](https://neon.com/docs/auth/authentication-flow),
[Better Auth role/schema](https://better-auth.com/docs/plugins/admin).

Record: branch/provider/version, column names and types, runtime SELECT permission,
admin assignment through provider controls, valid-token verification, and the
same still-valid token losing administrative access immediately after demotion.
Restore the demonstration role through provider controls afterward.
[Neon admin assignment](https://neon.com/docs/auth/guides/plugins/admin).

## R2 privacy, upload protection, and CORS gate

Use separate private and public buckets. Private holds temporary source/image
uploads and retained originals; disable both `r2.dev` and custom-domain exposure.
Only processed HLS and validated/generated thumbnails reach public delivery.
Connect the CDN hostname only to the delivery bucket; keep its development URL
disabled to avoid an additional delivery route.
[Public bucket controls](https://developers.cloudflare.com/r2/buckets/public-buckets/).

Browser PUTs use the S3 API endpoint, not the CDN hostname. Sign and return
`Content-Type` and `If-None-Match: *` as required upload headers, with a 900-second
expiry. Removing the condition must invalidate the signature. R2 documents atomic
conditional PUT and `412 PreconditionFailed` when a key already exists; actual
R2/browser proof is required before enabling accepted-source processing.
[Presigned URL rules](https://developers.cloudflare.com/r2/api/s3/presigned-urls/),
[Conditional PUT](https://developers.cloudflare.com/r2/api/s3/extensions/).

The [private upload](cloud/r2-upload-cors.example.json) and
[public delivery](cloud/r2-delivery-cors.example.json) files use **dashboard CORS
array syntax**. Replace the example origins with the exact approved origins.
They are not Wrangler's different `rules/allowed` file format. Upload CORS permits
PUT with Content-Type and If-None-Match; extend it for any additional headers the
actual signer requires. Delivery permits GET/HEAD and player Range requests.
[R2 CORS formats and headers](https://developers.cloudflare.com/r2/buckets/cors/).

Capture these live results, using a unique disposable test prefix:

1. Read back both buckets' public-access/domain configuration and CORS rules.
2. Upload a known private sentinel; prove authenticated HEAD/GET succeeds. Fetch
   that exact key anonymously through the CDN and any formerly enabled private
   public URL; require 403/404 with no sentinel bytes. A missing object alone
   does not prove privacy. Fetch a public control object successfully.
3. From each approved browser origin, preflight and PUT with **all** required
   headers. Verify response CORS headers, successful initial bytes, then a second
   PUT with different bytes returning 412 with the original object unchanged.
   Omitted/tampered conditional headers must fail signature validation. Include
   simultaneous PUTs: at most one succeeds. Repeat for custom-image uploads.
4. Check an unapproved Origin receives no allowing CORS response. Record status,
   sanitized headers, object digests and browser outcome; never the signed URL.
5. Delete disposable objects through authenticated access. Do not infer deletion
   completion while a still-valid PUT or in-flight writer can recreate a key.

URL expiry alone does not establish that an already started PUT has drained.
The deletion implementation must resolve its writer-fencing strategy before
claiming complete physical cleanup; live evidence must cover that strategy.

Runtime R2 credentials require bucket-scoped object operations, not account-wide
bucket administration. Confirm list/get/put/delete for cleanup as well as upload
signing. [R2 credential scope](https://developers.cloudflare.com/r2/api/tokens/).

## Cloud Run identity and direct-launch gate

Use distinct API and worker service identities. The API launches committed jobs
directly and records launch outcomes; only nonsensitive job IDs belong in execution
arguments. Database/R2 credentials come from secret references on the service/job.
Attach identities at deployment; use ADC in Cloud Run, not exported service-account
keys. [Service identity](https://docs.cloud.google.com/run/docs/securing/service-identity).

| Principal | Scoped grant / configuration |
| --- | --- |
| Deployer | Cloud Run Developer for service/job management, Artifact Registry Writer on the image repository, Service Account User (`iam.serviceAccounts.actAs`) on the two identities. A separate owner applies public-invocation and IAM bindings if deployer lacks those permissions. |
| API service account | Job-scoped `roles/run.jobsExecutorWithOverrides` when supplying per-execution job arguments/env; includes `run.jobs.run` and `run.jobs.runWithOverrides`. Add narrowly scoped execution read permissions only if diagnostics actually use them. |
| Worker service account | No job-launch permission unless implementation needs it; database/R2 access through its own secret references. |
| API / worker identities | `roles/secretmanager.secretAccessor` only on the individual secrets each consumes. |
| API ingress | Publicly reachable for anonymous viewers; application validates Neon bearer tokens for admin operations. Owner verifies organization policy permits public invocation. Jobs remain IAM protected. |

Invoker alone does not allow execution overrides. The deployer and execution
identity are separate permission checks.
[Job execution permissions](https://docs.cloud.google.com/iam/docs/roles-permissions/run),
[Attaching job identity](https://docs.cloud.google.com/run/docs/configuring/jobs/service-identity),
[Secret access](https://docs.cloud.google.com/run/docs/configuring/services/secrets),
[Public API ingress](https://docs.cloud.google.com/run/docs/authenticating/public).

Record one task per execution and explicit CPU, memory, timeout, and concurrency
settings after representative media measurements. Account for FFmpeg's local
working files in memory/disk capacity and Neon connections across API processes
and concurrent jobs. Do not let Cloud Run's default three **retries** silently
become four processing attempts: if the application worker owns the persisted
three-attempt loop, set platform `max-retries=0`. Cleanup has its separate recovery
policy; an interrupted execution remains visible for manual recovery.
[Platform retries](https://docs.cloud.google.com/run/docs/configuring/max-retries).

Independently of business handlers, verify deployed service/job identity names,
secret references (not payloads), and bindings; run a benign one-off probe using
the API identity and per-execution overrides; record the returned operation and
resulting execution names, worker identity, database TLS connectivity, and
terminal success. The verification/operator principal needs execution read and
log read permissions for this evidence; the runtime launcher does not need broad
viewer access merely to submit work. Test denied
launch with an unprivileged identity. These target checks remain pending. The
completed application deployment and live end-to-end showcase have separate
acceptance evidence. No scheduler, periodic reconciliation, lifecycle cleanup
rule, or credential-dependent ordinary CI job is part of this setup.
