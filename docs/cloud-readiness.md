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
| Neon Auth | Target management metadata confirms Neon-owned `better_auth` on the selected branch/database; schema has `neon_auth."user".id` UUID and `role` text. Auth `/ok` and Ed25519 JWKS return 200. Approved isolated signup/signin/token probe verified the real EdDSA signature, matching subject and 900-second lifetime. Actual issuer and audience both equal the Auth URL origin. The underlying managed build version is not exposed. |
| Current administrator role | Using the least-privilege runtime database connection, existing Authorization/NeonRoles denied the ordinary synthetic user, allowed temporary admin, then denied the same still-valid JWT immediately after provider-admin demotion. Final demo role is `user`, session signed out; existing administrator untouched. This is provider readiness, not deployed HTTP evidence. |
| Auth endpoint | `https://ep-wandering-art-b483xg29.neonauth.c-6.us-east-2.aws.neon.tech/neondb/auth`. Localhost allowed; trusted origins empty; password sign-in enabled. Discovery path returns 404. |
| Runtime database role | Created `videos_runtime`; verified fresh TLS login and current-role SELECT. Public schema CREATE, Auth writes/private email reads and migration-bookkeeping writes are denied. Five explicit migrations ran through the verified direct owner connection; exactly three application tables and four Yoyo bookkeeping tables now exist. Runtime DML is granted only on the three application tables. |
| Pooler compatibility | Target rejects startup `options`. The [transaction-local configuration fix](neon-pool-compatibility.md) now passes actual Neon pool acquisition, TLS, configured search path/timeouts, cancellation and reuse; no target application writes or migrations. |
| Google target | Existing project `videos-service`, number `749098550492`, ACTIVE, billing enabled. No billing or quota changes. Cloud Run, Artifact Registry, IAM, and Secret Manager APIs already enabled. |
| Registry / deployment | Existing Docker repository `videos`, `us-central1`. Verified AMD64 image published as `videos/videos-service:showcase-ccb6f66`, digest `sha256:f5ccffb6702f6998bb5ef931bcf0d6dd82a283ea120e1908dcf0d0c44a8b1f82`; no public registry IAM bindings. API revision `videos-api-00001-v2x` and worker job `videos-worker` are Ready with the pinned image. Existing authenticated deployer has project Owner; its identity is omitted. |
| Runtime identities | Existing `videos-api@videos-service.iam.gserviceaccount.com` and `videos-worker@videos-service.iam.gserviceaccount.com`. Six secret-scoped accessor grants added, then only these two project Editor members removed; unrelated default-compute Editor membership preserved. Readback confirms grants. |
| Secret metadata | `videos-database-url` version **2** holds the verified runtime DSN; prior owner version **1** is reversibly DISABLED. Pin runtime version 2. Owner reduced the existing R2 pair permissions in place; both secret version-1 entries now hold the privately verified object-access pair and remain enabled. Payloads were never printed. |
| R2 target | Distinct existing buckets `videos-raw` and `videos-processed`, WNAM/default jurisdiction. Authenticated HEAD, GET, create-only PUT, prefix list and narrow unsigned-probe deletion work. Private `r2.dev` remains disabled and both custom-domain lists empty. Owner explicitly selected and enabled only the processed development origin below. A public control GET returned 200 with matching bytes; Range returned 206. An existing private sentinel was verified with authenticated GET, but its key through the public origin returned 404 and the disabled raw URL returned 401, without sentinel bytes. |
| R2 upload protection | Both source/video and image signed PUT: first 200, replacement 412, original bytes unchanged. Missing/altered If-None-Match or altered Content-Type: 403. Two simultaneous PUTs: 200/412, stored bytes match one contender. URLs signed for 900 seconds. |
| R2 deletion guards | Existing and previously absent keys in both buckets were sealed to permanent zero-byte objects. Every late signed conditional PUT returned 412; HEAD/GET verified size 0, exact marker type and metadata, and `Cache-Control: no-store`. Thirteen markers retained after browser, public-origin and runtime-scope probes; inventory below. |
| Browser/CORS | Approved `http://localhost:8765` private PUT preflight returns 204, exact origin, Content-Type/If-None-Match allowed. Public GET-with-Range preflight returns 204 and advertises GET/HEAD. Unapproved-origin PUT and GET-with-Range preflights return 403 without allowing headers; preserved wildcard owner rules still allow simple GET. Actual in-app browser uploads of MP4 and valid 1280×720 JPEG each return 200 then 412 for replacement bytes; authenticated GET digests remain unchanged. Both signed keys then sealed and verified. |
| Configuration access | Earlier owner-authorized setup access returned 200 for REST metadata/domain/CORS and S3 GetBucketCors. Preserved owner GET rules (localhost:3000 and wildcard); appended narrow localhost:8765 upload/player rules and read them back. Zone-name metadata was empty. The owner subsequently reduced that credential in place; current runtime bucket-configuration reads correctly return 403. |

These include direct provider/SDK/HTTP observations and an actual browser direct-PUT
probe. They do not certify completed application deployment or CDN player playback. No scheduler, lifecycle rule, bucket-wide delete,
service-account key, or unrelated resource was created.

The [retained browser screenshot](evidence/r2-browser-put-2026-10-16.png) shows
actual localhost MP4/JPEG upload and overwrite statuses without signed URLs.

## Remaining access and verification gates

| Area | Specific remaining input or action |
| --- | --- |
| Auth | Provider token/current-role/demotion readiness is verified with approved isolated identity changes. Deployed HTTP token handling and same-token demotion remain MEL-16 checks. The provider exposes `better_auth` integration metadata, not its underlying build version. |
| Database | Explicit direct-connection production migrations, three-table DML grants and runtime secret version 2 are complete. Verify deployed API/worker TLS connectivity using that pinned secret and the tested pooler-compatible configuration. |
| R2 configuration | Configuration access and private exposure readback are verified. Retain the approved narrow browser rules and all permanent markers; preserve existing owner GET rules unless the owner requests a change. CORS does not authorize access to private objects. Keep raw bucket public access disabled. |
| R2 runtime credentials | Owner reduced the existing pair's permissions in place. Both version-1 secret payloads match the privately verified runtime pair. Both buckets pass HEAD, object PUT/GET/LIST, conditional replacement 412 and permanent guard sealing; GetBucketCors now returns 403 on both. Keep both version-1 entries enabled and pinned. Provider tokens were not printed. |
| Public delivery / browser | Owner chose `https://pub-1296a4df37cd4d52aacd2941d8b36687.r2.dev`; processed-only exposure, public/private sentinel separation, Range, CORS and direct browser PUT are verified. This development endpoint is rate-limited and lacks custom-domain caching features. Actual deployed HLS player playback and any separately approved player origins remain MEL-16 checks; no new zone or DNS record was created. |
| Cloud Run | API and worker deployed with distinct identities, final digest, database secret 2 and R2 secrets 1. API job-scoped execution-with-overrides is bound; approved anonymous API invocation is enabled. Anonymous health and real database-backed list return 200. API-identity helper launch produced operation `802569c2-0ea2-4cd3-b7d0-240d34280e1f` and successful zero-ID worker execution `videos-worker-bmf2h` (`no_op`, exit 0). Worker-identity launch is denied with HTTP 403. Temporary helper job removed. Full business acceptance remains separately tracked. |
| Resource budget | Measure representative media against explicit job CPU/memory/timeout and API/connection concurrency settings; no quota expansion is implied. |

The [deployment preparation record](cloud-deployment.md) pins the published image,
records production migrations/runtime secret version 2, and stages the exact
identity/resource/environment commands. The final published image includes the
reviewed local operator-recovery boundary.
The R2 permission gate is resolved by the verified in-place scope reduction.
Both R2 version-1 secret entries stay enabled. Independent deployed launch
and denial checks now pass; full live application acceptance remains separate.

MEL-7 remains open. Local application work and ordinary CI need no cloud credentials.
Completed application deployment and end-to-end live evidence belong to MEL-16.

## Applied least-privilege setup

For each of the three existing secrets above, both dedicated runtime identities
now have resource-level `roles/secretmanager.secretAccessor`. Neither identity has
project Editor or a project-wide job execution grant. The existing deployer has
sufficient project-level ownership for deployment and service-account attachment;
no new deployer grant was necessary. Preserve unrelated project IAM members.
Lifecycle readback finds only the existing default seven-day incomplete multipart
abort rule on each bucket; no object-expiration action can erase guards. No rule
was added or changed.

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

Keep these initial seven zero-byte deletion guards indefinitely under the exact prefix
`readiness/mel-7/7dc4f9b8-8e22-4ef1-a8e1-2989db635f51/`:

| Bucket | Key suffixes |
| --- | --- |
| `videos-raw` | `source`, `image`, `concurrent`, `guard-existing`, `guard-absent` |
| `videos-processed` | `guard-existing`, `guard-absent` |

The browser proof additionally retained two guards in `videos-raw` under
`readiness/mel-7/browser-8701e1f9-f225-43e2-b3a9-2fc2f9cdb1fa/`, suffixes
`source` and `image`. These correspond to the actual MP4/JPEG browser uploads.

The public-origin probe retained two more under
`readiness/mel-7/public-origin-485a3288-336e-40df-b2a7-65afdc82b340/`:
`videos-raw/private-only` and `videos-processed/public-control`, where each suffix
is appended to that shared prefix in its respective bucket. Both were verified
zero-byte guards after successful positive/negative sentinel checks.

The in-place credential-scope verification retained two more guards at
`readiness/mel-7/runtime-scope-64aac371-666a-4b71-821f-2f886421ea84/object-control`,
one in each bucket. Both passed conditional-overwrite rejection and guard HEAD.

They have content type `application/x-pilgrims-deletion-guard`, metadata
`pilgrims-deletion-guard=1`, and `Cache-Control: no-store`. Never blanket-delete
these prefixes: removing a guard reopens its key to a delayed conditional writer.
Only the unsigned `delete-control` objects were removed, and subsequent HEAD
returned 404. No user media was read, overwritten, or deleted. GCP R2 secret discovery found
only the two existing R2-named resources, each with one enabled version: key ID
created `2026-10-16T13:51:29.048348Z`, secret created
`2026-10-16T13:51:42.313010Z`. The owner subsequently reduced those same credentials
to object-access scope in place. Actual object operations work and bucket
configuration reads now return 403; both version-1 entries remain enabled.

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
The owner selected the processed bucket’s `r2.dev` development URL for this
bounded showcase; it is now enabled. This differs from a production custom-domain
configuration: the development endpoint is rate-limited and lacks custom-domain
cache/access-management features. Private exposure stays disabled. If a custom
domain is configured later, connect it only to delivery and disable the alternate
development route when appropriate.
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

Account-owned token creation requires `Account API Tokens Write`; current setup
access cannot read token details or permission groups (403/code 9109). R2 derives
the S3 key ID from the token ID and its secret from SHA-256 of the token value.
These were compared privately only; no credential was copied into evidence.
[Account token creation](https://developers.cloudflare.com/api/resources/accounts/subresources/tokens/methods/create/).

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
launch with an unprivileged identity. The independent identity checks above are
now recorded in [deployment evidence](cloud-deployment.md). The
completed live end-to-end showcase has separate
acceptance evidence. No scheduler, periodic reconciliation, lifecycle cleanup
rule, or credential-dependent ordinary CI job is part of this setup.
