# MEL-8 — source admission and confirmation

Local acceptance completed 2026-10-16. Live browser/R2 conditional-write proof and
Cloud Run runtime identity are separate MEL-16 gates; local results do not close
those cloud requirements.

OpenAPI now requires signed `If-None-Match: *` in source and custom upload
instructions. The contract and 45 examples were validated before `ag-generate`
regenerated 13 operations/23 cases. Handwritten source handlers live outside owned
packages; their generated Arrange hook uses controlled identity/clock/randomness.

Source authorizations persist isolated SOURCE attempts and fifteen-minute expiry.
Only CREATED/UPLOADING accepts a fresh attempt. Renewal supersedes the previous
attempt. Declared sizes above the configurable 100 MiB default fail with 413 before
signing. File names do not influence object keys.

Confirmation performs HEAD without holding database locks, checks observed
existence/size/type and current attempt identity, then locks and rechecks lifecycle
and identity before atomically accepting the source and recording separate VIDEO
and THUMBNAIL jobs. Rejection leaves UPLOADING. Duplicate or concurrent requests
return the same original processing job, including after later execution attempts;
DELETING always rejects confirmation. Upload expiry controls browser writes, not a
separate acceptance deadline for a still-current object already uploaded.

The R2 adapter signs Content-Type and If-None-Match. Its ordinary PUT interface
requires create-only writes. Separate configured private/public buckets prevent
originals sharing the delivery bucket. Signed URLs never appear in normal video
resources. No transfer ceiling is promised: rejected objects can remain stored
until explicit cleanup.

Jobs persist RECORDED before direct submission. Cloud Run v2 requests use the
runtime metadata identity and carry only the job ID; returned operation names
record LAUNCHED. Failed/ambiguous submissions record LAUNCH_FAILED with sanitized
LAUNCH_UNCONFIRMED diagnostics. Repeating confirmation does not implicitly relaunch
uncertain work. Manual recovery must inspect existing executions before relaunch.
Launch-state recording does not overwrite an already running or completed worker.
Worker claims/publication fencing remain independent of provider submission.

Acceptance uses HTTP through the real app, isolated PostgreSQL schemas, controlled
provider boundaries, and real signed JWT verification. Cases cover persisted
instructions and expiry, renewal/stale attempts, missing/oversized/mismatched
objects, concurrent completion, immutable accepted bytes, deletion during HEAD,
accepted-source renewal denial, launch failure persistence, and secret exclusion.
The actual Boto3 R2 signer is checked through HTTP for its signed-header set and
900-second expiry; its HEAD SDK boundary is controlled. The actual Cloud Run
adapter uses controlled metadata/run HTTP responses and submits independent IDs
without executing media inline. Media processing belongs to MEL-9/MEL-11.

Primary references checked:

- [R2 conditional PUT](https://developers.cloudflare.com/r2/api/s3/extensions/#conditional-operations-in-putobject)
- [Boto3 PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)
- [Cloud Run jobs.run](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs/run)
