# Videos service ticket proposal

Status: approved and published — 2026-10-16

The user approved this eleven-ticket breakdown. It was published to the Video Content Service project in Linear as MEL-6 through MEL-16, with ready-for-agent labels and native blockers. Linked local copies and a ticket index are maintained alongside the canonical specification. Linear owns current execution status; this document records the approved breakdown. The specification and existing parent records remain unchanged.

## Working rules

- Each application ticket includes its HTTP or worker-facing behavior, persistence, validation, and meaningful acceptance checks. Use real application services and PostgreSQL, controlling external providers at their boundaries. No production authentication bypass is introduced for local tests.
- Ticket 01 owns initial shared schema and contract reconciliation. Later tickets own their feature behavior and any necessary feature migrations. Agree on typed storage/launch boundaries, job payloads, current-attempt checks, thumbnail projection, and responsibility for shared handler edits before parallel work. Keep this narrow: no generic queue framework.
- Peer features use seeded records and job inputs rather than waiting for the whole runtime sequence. A local completion claim requires actual local behavior, not an unimplemented provider stub presented as a cloud result.
- Each ticket records checks performed and material design choices. Cloud-dependent evidence stays separate from local acceptance. Missing access is reported as an explicit environment gate, never treated as a passing test.
- No cron jobs, scheduled reconciliation, automatic orphan cleanup, new client product, or fourth application table is introduced.

## 01 — An administrator can create and manage a persisted draft

**Blocked by:** None.

**Delivers:** An authenticated administrator creates a draft, retrieves it, and edits metadata; anonymous viewers cannot discover it. This is the first real HTTP-to-database slice.

**Acceptance:**

- Reconcile agreed scope, media limits, examples, access policy, and error behavior in the authoritative contract; validate, regenerate, and preserve handwritten/generated ownership boundaries.
- Establish the three-table migrations and minimal shared definitions for upload attempts, job kinds/current attempts, and independent thumbnail state. Initial table design supports the approved workflows without implementing all of them here.
- Validate bearer identity and look up the current administrator role for privileged requests. Verify identity and role expectations against provider documentation; use controlled signing keys and role fixtures locally. Live schema compatibility is proven in Ticket 11.
- Create returns 201, Location, CREATED/DRAFT, expected nulls, and timestamps. Detail and metadata changes persist; identity/role failures deny access. Demotion with the same valid token denies the next privileged request.
- Real app/PostgreSQL tests cover creation, reads, metadata edits, role freshness, anonymous hiding, and native request validation. Keep health database-independent.

## 02 — A configured cloud environment is ready for the showcase

**Blocked by:** None; external account access and any required owner actions are explicit prerequisites.

**Delivers:** A verified configuration and access checklist for Neon Auth/PostgreSQL, R2/CDN, and Google Cloud Run, ready for application deployment.

**Acceptance:**

- List exact account, billing, credential, project, region, origin, and permission inputs. Identify owner-only actions and perform agent-accessible setup when authorized. No secrets appear in the tracker or logs.
- Confirm the intended Neon Auth version, trusted token configuration, administrator assignment, and current-role schema in the target database/branch.
- Prepare private upload/source storage and appropriate public delivery storage/origin; demonstrate that private originals cannot be fetched from the public CDN. Establish browser upload CORS and required-header support.
- Establish runtime/job-launch permissions and a way to configure service/job identities and database access. Provider setup is verified independently of business handlers; deployment of the completed app belongs to Ticket 11.
- Record actual readiness and remaining access gaps. Code tickets continue locally if this ticket is blocked. Do not require cloud credentials in ordinary CI.

## 03 — An administrator can upload and confirm a source

**Blocked by:** 01.

**Delivers:** Source upload instructions and verified, idempotent confirmation, with durable video/thumbnail job records and direct launch requests.

**Acceptance:**

- Issue fifteen-minute MP4 upload instructions using a new persisted attempt and isolated object key; permit renewal only in CREATED/UPLOADING. Reject excessive declared size.
- Confirm current attempt, object existence, observed size, declared size, and the 100 MiB cap. Rejection preserves UPLOADING and creates no jobs; stale completion does not disturb the active attempt.
- Protect accepted bytes against overwrite by the same still-valid PUT URL, using conditional create-once writes or equivalent finalization. Verify local provider-request behavior here; real browser/R2 proof is mandatory in Ticket 11.
- Atomically accept one source and record independent video and thumbnail jobs. Duplicate/concurrent confirmation returns the existing job without duplicate work; recheck deletion/state before committing verified objects.
- Use the agreed launch boundary without waiting for transcoding. Record pending/launched/failed-to-launch states and expose sufficient information for manual recovery. Tests control the provider boundary; worker implementation is owned by Tickets 04 and 06.
- HTTP/database acceptance covers renewed attempts, duplicate requests, missing/oversized/mismatched objects, deletion races, admission-only size enforcement, and exclusion of upload secrets from normal resources.

## 04 — An accepted video becomes playable HLS

**Blocked by:** 01.

**Delivers:** A real worker takes a seeded accepted job and source, produces valid adaptive HLS, and makes readiness observable through administrator HTTP reads.

**Acceptance:**

- Execute worker logic locally with real FFmpeg/FFprobe and PostgreSQL. Provide a Cloud Run-compatible worker entry point using the shared job payload; the real cloud execution is verified in Ticket 11.
- Validate actual MP4 media and the 300-second duration ceiling. Corrupt, unsupported, and over-duration input fails with sanitized diagnostics and cannot become READY.
- Produce supported 360p/720p/1080p H.264/AAC renditions without upscaling; handle portrait and below-360p inputs. Record exact sizing, audio policy, encoding settings, and resource limits.
- Verify the master and referenced assets before conditionally marking the current job/video READY. Retain the source, keep publication DRAFT, and reject stale/deleting worker commits. Administrator polling observes real persisted outcomes.
- Use attempt-specific output namespaces and representative media tests for playable manifests, proportions, missing assets, invalid sources, and stale/deletion fencing. This ticket needs seeded accepted work, not Ticket 03's HTTP upload flow.

## 05 — Failed processing can recover without another upload

**Blocked by:** 04.

**Delivers:** Temporary worker failures receive bounded retries; administrators can explicitly retry failed processing when the retained source is valid.

**Acceptance:**

- Allow three total execution attempts per job for temporary failures, with increasing delays and observable counts. Permanent invalid-media failures are not automatically retried.
- Explicit retry requires FAILED with a retained valid source, creates a new job/output namespace, preserves DRAFT, and returns 202/QUEUED. Concurrent retries create only one current job.
- Unusable sources have no retry/replacement path; explain deletion and recreation. Preserve safe attempt history until video deletion.
- Provide an explicit manual recovery command/procedure for stranded launches, fenced against deleted/superseded jobs; add no cron or automatic reconciler.
- Acceptance covers temporary failure then success, exhaustion, invalid-source rejection, concurrent explicit retry, and safe manual launch recovery.

## 06 — Automatic thumbnails finish independently

**Blocked by:** 01.

**Delivers:** A seeded accepted thumbnail job generates a fallback image whose state is observable independently of video readiness.

**Acceptance:**

- Execute real thumbnail extraction locally and expose the shared Cloud Run-compatible worker entry point. Output a 1280 × 720 fitted/padded image with no crop.
- Keep generated state separate from custom state and resolve the active-thumbnail projection. Generated completion never overrides a valid custom image, including races.
- Apply the independent three-execution-attempt policy for temporary failures; permanent failure reports FAILED without blocking video readiness or publication.
- Current job/deletion checks prevent stale activation. Tests seed accepted sources/jobs, so this ticket does not wait for upload or HLS tickets.
- Verify dimensions, portrait padding, failure projection, retry exhaustion, custom priority, and independence from video processing through real image processing and observable API state.

## 07 — An administrator can select and remove a custom thumbnail

**Blocked by:** 01.

**Delivers:** Custom image upload, actual-content validation, activation, and removal work before or after video processing.

**Acceptance:**

- Issue new attempt-scoped fifteen-minute upload instructions; protect accepted image bytes from later overwrites. Use the agreed storage boundary, sharing provider helpers through coordinated integration with Ticket 03 rather than duplicating a storage architecture.
- Accept actual JPEG/PNG/WebP up to 5 MiB at exactly 1280 × 720. Reject type spoofing, corrupt/oversized/wrong-sized images, stale IDs, and deleting videos while preserving the active image.
- Activate valid custom media atomically. Accepted completion is idempotent and cannot restore removed/superseded assets.
- Idempotent removal restores a ready generated image; otherwise report PENDING/NONE/null or FAILED/NONE/null according to generation state. Generated fallback is retained.
- Real HTTP/PostgreSQL and decoded-image tests cover these outcomes using seeded generated states. Do not depend on Ticket 06 to arrange fallback outcomes or build a crop UI.

## 08 — Viewers can discover and play published videos

**Blocked by:** 01.

**Delivers:** Publication/unpublication, administrator previews, anonymous detail/list/playback, search, filters, and stable cursor pagination.

**Acceptance:**

- Publish only READY videos, independent of thumbnail state. Repeating publication preserves its timestamp; unpublishing clears it; metadata edits preserve processing state.
- Anonymous viewers see only ready, published, non-deleting resources. Administrators can inspect other states and preview ready drafts after current-role lookup. Viewer use of administrator-only filters is rejected.
- Serve playback URLs constructed from configured delivery origin and stored master keys. Store no fixed CDN URL and disclose no private source keys.
- Provide deterministic descending creation/id order, case-insensitive title search, bounded page size, and cursors bound to filter context. Preserve current response/error conventions.
- Test through HTTP/PostgreSQL using seeded READY/DRAFT/PUBLISHED and thumbnail states; actual HLS generation is not a prerequisite. CDN revocation is explicitly outside the guarantee.

## 09 — Deleting a video hides it and removes its media

**Blocked by:** 01.

**Delivers:** Permanent asynchronous deletion blocks discovery/mutations immediately and cleans associated media before removing application records.

**Acceptance:**

- Atomically accept deletion and record/launch cleanup work; repeat in-progress deletion returns 202, completed deletion returns 404. No restore window.
- Fence active workers and upload acceptance. Enumerate accepted/superseded upload objects, original, all playback attempts, and generated/custom thumbnail assets.
- Do not declare cleanup complete while unexpired PUT URLs or active workers can recreate objects; implement waiting/final-sweep or equivalent protection within explicit cleanup execution, without cron.
- Retry temporary cleanup failures with increasing delays; do not apply the three-attempt media budget as abandonment. Keep DELETING observable and provide manual relaunch after runtime exhaustion.
- Test seeded in-flight jobs/attempts, late writes, repeated deletion, object failures, blocked operations, and eventual cleanup through real API/database behavior with controlled provider responses. Integrate real peer workers in Ticket 10; production provider races are checked in Ticket 11.

## 10 — An interviewer can run the complete local demonstration

**Blocked by:** 03, 05, 06, 07, 08, 09. Ticket 04 is included transitively through 05.

**Delivers:** A reproducible local run connects real feature handlers and workers, demonstrates the full journey, and records acceptance evidence without requiring cloud credentials.

**Acceptance:**

- Assemble a narrow local launch/storage/identity harness that exercises actual app, repositories, PostgreSQL, workers, and real media; clearly label controlled external-provider behavior. Prefer existing fixtures and a local execution command, not a second production architecture.
- Reproduce create → direct-upload equivalent → confirm → process → READY → publish → HLS playback, independent generated/custom thumbnails, and explicit deletion. Include a role-demotion example and representative failure/recovery cases.
- Resolve shared-handler, schema, thumbnail-projection, job-launch, and lifecycle integration conflicts. Verify direct confirmation actually starts both independent workers and no operation remains served by an example mock unintentionally.
- Run contract/generation, quality/type, database-backed, and media checks. Each implementing feature already has its own tests; this ticket verifies composition and demonstration instructions.
- Record what was proved locally and what still requires live infrastructure. Explain admission versus transfer limits, database state versus dispatch recovery, and publication versus CDN authorization. Do not add a full frontend or player product.

## 11 — The deployed showcase passes live acceptance

**Blocked by:** 02, 10.

**Delivers:** The implemented service and workers run against actual Neon, R2/CDN, and Cloud Run, with a documented live demonstration an interviewer can inspect.

**Acceptance:**

- Build/deploy the API and worker images, apply explicit production migrations, configure trusted auth and least-required runtime/launch/storage access, and keep secrets out of evidence. No unrelated production deployment platform is added.
- Verify real token handling and immediate administrator demotion in the target Neon branch; browser CORS and direct signed uploads; attempt renewal and accepted-object overwrite protection.
- Prove independent Cloud Run processing/thumbnail jobs, valid HLS manifests and player playback through the CDN, publication visibility, and retained private originals. Exercise the selected media limits and failure paths.
- Verify explicit deletion, expired upload authorization/in-flight worker handling, and manual recovery instructions. Do not claim cache revocation or guaranteed automatic launch recovery.
- Capture commands, expected outcomes, actual results, and required reviewer inputs. Missing credentials/provider access leave this ticket incomplete while completed local tickets remain accurately reported.

## Publication

Published after user approval to [Video Content Service](https://linear.app/mellowpillow/project/video-content-service-8ec27d19a921). Ticket numbers 01 through 11 correspond respectively to MEL-6 through MEL-16. All eleven labels and fifteen native blocking links were read back and verified. This publication introduces no implementation work and does not close or alter a parent issue.
