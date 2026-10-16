# Showcase cloud readiness (MEL-7)

Checked 2026-10-16. **Live readiness is incomplete.** This records setup inputs,
provider facts, and the evidence needed to finish MEL-7. It does not certify a
deployment or the live showcase. Local application tickets can proceed with real
PostgreSQL and FFmpeg and controlled external provider boundaries.

## Actual target evidence — 2026-10-16

Credentials were supplied privately and used without logging values. No secret
payload, signed URL, database password, or demonstration identity is recorded here.

| Check | Observed result |
| --- | --- |
| Neon target | Project `flat-dawn-07469526`, branch `br-polished-feather-b4mxbb1f`, endpoint `ep-wandering-art-b483xg29`; PostgreSQL 18, AWS `us-east-2`, database `neondb`. TLS connection succeeds. |
| Neon Auth | Managed Better Auth schema: `neon_auth."user".id` UUID, `role` text. One user and one exact admin membership counted without recording identity. Auth `/ok` returns 200; JWKS returns OKP/EdDSA/Ed25519. Target server version and actual token claims remain unverified. |
| Auth endpoint | `https://ep-wandering-art-b483xg29.neonauth.c-6.us-east-2.aws.neon.tech/neondb/auth`. Localhost allowed; trusted origins empty; password sign-in enabled. Discovery path returns 404. |
| Runtime database role | Created `videos_runtime`; verified fresh TLS login and current-role SELECT. Public schema CREATE and Auth role UPDATE are denied. No application tables or migration bookkeeping exist yet. |
| Pooler compatibility | Connection startup `options` is rejected by the target pooler. Ordinary connection and transaction-level read-only setup work; application compatibility is a separate tracked fix before deployment. |
| Google target | Existing project `videos-service`, number `749098550492`, ACTIVE, billing enabled. No billing or quota changes. Cloud Run, Artifact Registry, IAM, and Secret Manager APIs already enabled. |
| Registry / deployment | Existing Docker repository `videos`, `us-central1`. No Cloud Run services or jobs deployed. Existing authenticated deployer has project Owner; its identity is omitted. |
| Runtime identities | Existing `videos-api@videos-service.iam.gserviceaccount.com` and `videos-worker@videos-service.iam.gserviceaccount.com`. Six secret-scoped accessor grants added, then only these two project Editor members removed; unrelated default-compute Editor membership preserved. Readback confirms grants. |
| Secret metadata | Existing `videos-database-url`, `videos-r2-access-key-id`, `videos-r2-secret-access-key`, each version `1` ENABLED. Payloads were not printed or changed. Database secret must be checked/replaced with the separate runtime DSN at deployment. |
| R2 target | Distinct existing buckets `videos-raw` (private intent) and `videos-processed` (delivery intent). Authenticated HEAD, GET, create-only PUT, prefix list and narrow delete succeed through supplied S3 credentials. Bucket exposure is **not yet verified**. |
| R2 upload protection | Both source/video and image signed PUT: first 200, replacement 412, original bytes unchanged. Missing/altered If-None-Match or altered Content-Type: 403. Two simultaneous PUTs: 200/412, stored bytes match one contender. URLs signed for 900 seconds. |
| R2 deletion guards | Existing and previously absent keys in both buckets were sealed to permanent zero-byte objects. Every late signed conditional PUT returned 412; HEAD/GET verified size 0, exact marker type and metadata, and `Cache-Control: no-store`. Seven markers retained; inventory below. |
| Browser/CORS gate | OPTIONS for `http://localhost:8765` and an unapproved origin both return 403 without Access-Control-Allow-Origin. HTTP upload safety succeeds, but browser upload readiness is **blocked**, not passed. |
| Configuration access | Cloudflare bucket metadata/domain/CORS REST reads return 403, code 10000. S3 GetBucketCors returns 403 AccessDenied on both buckets. No bucket configuration changed. |

These are direct provider/SDK/HTTP observations, not a live browser session or a
completed application deployment. No scheduler, lifecycle rule, bucket-wide delete,
service-account key, or unrelated resource was created.

## Remaining access and verification gates

| Area | Specific remaining input or action |
| --- | --- |
| Auth | Dedicated demonstration login and permission for temporary provider-admin demotion/restoration; inspect real issuer/audience/subject/lifetime, verify admin access and immediate revocation using the same valid token. Confirm target Auth version. |
| Database | Explicitly apply application migrations with owner connection, grant DML on the exact three tables, update runtime secret reference, and verify API/worker TLS connectivity after the pooler compatibility fix. |
| R2 configuration | Correct Cloudflare API token with read/write configuration permissions for the two existing buckets, or owner-applied settings with readback. Verify private `r2.dev` and custom domains disabled; delivery development URL disabled. |
| CDN / browser | Actual public delivery hostname and DNS/cache authorization. Connect only delivery bucket; prove public control succeeds and an existing private sentinel cannot be fetched there. Apply/read back CORS for the approved narrow demo origin `http://localhost:8765` and any separately approved player origins. Repeat actual browser preflight/PUT/player checks. |
| Cloud Run | Deploy completed image to existing registry, attach the two identities and secret references, create the worker job, grant API job-scoped execution-with-overrides, then verify benign authorized and denied launches independently of business flows. No job currently exists to receive that scoped grant. |
| Resource budget | Measure representative media against explicit job CPU/memory/timeout and API/connection concurrency settings; no quota expansion is implied. |

MEL-7 remains open. Local application work and ordinary CI need no cloud credentials.
Completed application deployment and end-to-end live evidence belong to MEL-16.

## Applied least-privilege setup

For each of the three existing secrets above, both dedicated runtime identities
now have resource-level `roles/secretmanager.secretAccessor`. Neither identity has
project Editor or a project-wide job execution grant. The existing deployer has
sufficient project-level ownership for deployment and service-account attachment;
no new deployer grant was necessary. Preserve unrelated project IAM members.
When the worker job exists, bind `roles/run.jobsExecutorWithOverrides` to the API
identity on that job only. Its verified predefined permissions are
`run.jobs.run`, `run.jobs.runWithOverrides`, and `run.executions.cancel`.

Database owner setup uses the following non-secret SQL. Supply a generated password
privately through a secure parameterized administration path; never put it in SQL
history, evidence, or git. Create the role once; the owner then applies grants.

```sql
CREATE ROLE videos_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE neondb TO videos_runtime;
GRANT USAGE ON SCHEMA public, neon_auth TO videos_runtime;
GRANT SELECT (id, role) ON neon_auth."user" TO videos_runtime;
-- Run only after the explicit application migrations create these tables:
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.videos, public.upload_attempts, public.jobs TO videos_runtime;
```

Do not grant runtime access to Auth sessions, secrets, JWKS tables, Auth writes,
Yoyo bookkeeping, schema CREATE, or blanket future tables. Keep migration-owner and
runtime connections separate. Verify the login and column SELECT using the runtime
connection, and verify public CREATE and Auth role UPDATE are denied.

## Permanent probe marker inventory

Keep these seven zero-byte deletion guards indefinitely under the exact prefix
`readiness/mel-7/7dc4f9b8-8e22-4ef1-a8e1-2989db635f51/`:

| Bucket | Key suffixes |
| --- | --- |
| `videos-raw` | `source`, `image`, `concurrent`, `guard-existing`, `guard-absent` |
| `videos-processed` | `guard-existing`, `guard-absent` |

They have content type `application/x-pilgrims-deletion-guard`, metadata
`pilgrims-deletion-guard=1`, and `Cache-Control: no-store`. Never blanket-delete
this prefix: removing a guard reopens its key to a delayed conditional writer.
Only the unsigned `delete-control` objects were removed, and subsequent HEAD
returned 404. No user media was read, overwritten, or deleted.

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
5. Delete only unsigned disposable controls. Seal every signed/in-flight probe
   key with the approved permanent zero-byte guard, verify its marker, and retain
   it indefinitely; test a late conditional PUT returns 412.

URL expiry alone does not establish that an already started PUT has drained.
Deletion uses permanent zero-byte guards: overwrite existing media and reserve
known absent keys atomically, then verify exact marker HEAD metadata. Actual R2
proof above covers this mechanism; complete application cleanup and CDN cache
evidence remain separate live acceptance work.

Runtime R2 credentials require bucket-scoped object operations, not account-wide
bucket administration. Confirm list/get/create-only PUT and privileged guard sealing, as well as upload
signing. Production cleanup seals objects and retains markers; the ordinary
storage interface does not expose marker deletion. [R2 credential scope](https://developers.cloudflare.com/r2/api/tokens/).

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
