# Pilgrims Progress — Video Service API Contract

**Version:** 1.0 (MVP)  
**Status:** Finalized API contract  
**Date:** 2026-10-13  
**Base path:** `/v1`  
**Infrastructure:** Google Cloud Run (API + Jobs), Neon PostgreSQL, Cloudflare R2 + CDN

## 1. Scope and decisions

This contract covers administrator video management, direct-to-R2 uploads, asynchronous HLS processing, polling, publication, playback, asynchronous deletion, and thumbnail management.

**Locked decisions**

- Video record creation and upload-URL issuance are **separate** operations.
- MVP source format is **MP4** (`video/mp4`); true media format is verified server-side during processing.
- Video bytes go **directly from the client to R2**, not through the API.
- Upload URLs expire, can be renewed before confirmation, and cannot authorize overwriting a confirmed source.
- `complete-upload` verifies the source object and durably queues processing; it never uploads file bytes or synchronously transcodes.
- Processing runs in Cloud Run Jobs, with durable job dispatch/reconciliation.
- Client polls `GET /videos/{id}` for processing state.
- Video publication is manual with a **separate, explicit `PUBLISHED` publication status**.
- HLS assets are delivered from Cloudflare CDN; playback URLs are assembled server-side from storage keys.
- Deletion is asynchronous; a deleting video must immediately become unavailable for playback.
- List pagination is cursor-based.
- Every confirmed video upload starts **independent** automatic-thumbnail generation. Valid custom thumbnails override generated thumbnails, but generated thumbnails are retained as fallback.

## 2. Conventions

- HTTPS only. All API JSON fields use `camelCase`; database columns may use `snake_case`.
- IDs are UUID strings. Dates are UTC ISO-8601 strings. Unavailable optional values are `null` unless otherwise specified.
- `Content-Type: application/json` for requests with JSON bodies. `Authorization: Bearer <token>` for authenticated operations.
- Mutations require **admin** authorization. Published-ready videos may be listed and viewed by regular viewers (or anonymously if the application elects to expose public content). CDN-level access control is **not** provided by this MVP contract.
- For viewers, unpublished/deleting/nonexistent video resources return `404` (avoid leaking unpublished resources). Admin reads may show all lifecycle states except resources fully removed.
- Path `{id}` is the UUID of a video. An invalid UUID returns `400 INVALID_VIDEO_ID`.
- Responses below illustrate complete shapes; clients must tolerate new optional fields.
- Upload presigned URLs and their headers are transient secrets: do not persist, log, or expose them in normal video GET responses.

### 2.1 Video state model

`status` (processing/lifecycle):

| Value | Meaning |
|---|---|
| `CREATED` | Video record exists; no verified upload |
| `UPLOADING` | Upload URL issued; upload not confirmed |
| `QUEUED` | Upload verified; processing request durably recorded |
| `PROCESSING` | Transcoding underway |
| `READY` | Valid HLS output published to R2; playable when published |
| `FAILED` | Video processing failed; eligible for retry if source remains valid |
| `DELETING` | Delete accepted; further mutation and playback prohibited |

`publicationStatus` (independent): `DRAFT` or `PUBLISHED`.

Rules:

1. Newly created videos start with `status=CREATED`, `publicationStatus=DRAFT`, `publishedAt=null`.
2. Only `READY` videos may transition to `PUBLISHED`.
3. Unpublishing transitions to `DRAFT` and sets `publishedAt=null` (the system does not retain publication history in this API).
4. A video is viewer-playable **only when** `status=READY AND publicationStatus=PUBLISHED`.
5. Retry is allowed for `FAILED` videos and returns to `QUEUED`; publication remains `DRAFT` for such videos in this MVP.
6. `DELETING` is terminal for client-facing operations; completed deletion results in `404`.

### 2.2 Standard video resource

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Introduction to Faith",
  "description": "An introductory lesson",
  "status": "READY",
  "publicationStatus": "DRAFT",
  "sizeBytes": 524288000,
  "durationSeconds": 1475.5,
  "thumbnail": {
    "status": "READY",
    "source": "GENERATED",
    "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg"
  },
  "publishedAt": null,
  "createdAt": "2026-10-13T14:00:00Z",
  "updatedAt": "2026-10-13T14:05:00Z"
}
```

`description`, `sizeBytes`, `durationSeconds`, `thumbnail.url`, and `publishedAt` can be `null`. `thumbnail.status` is `PENDING`, `READY`, or `FAILED`; `thumbnail.source` is `GENERATED`, `CUSTOM`, or `NONE`. The `thumbnail` object represents the active thumbnail, not the detailed state of each underlying asset. If the custom thumbnail is not ready, the generated asset can remain active. Source and HLS R2 **keys** are private implementation details and omitted from public responses. Thumbnail URLs are constructed by the API from keys and delivery configuration.

Admin-only processing diagnostics may be returned as an additional `processingError` field:

```json
{"processingError": {"code": "TRANSCODE_FAILED", "message": "Video processing failed."}}
```

### 2.3 Standard error response

```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "The video is not eligible for this operation."
  }
}
```

| HTTP | Meaning |
|---|---|
| `400` | Invalid request, query, UUID, or uploaded media |
| `401` | Authentication missing/invalid |
| `403` | Insufficient privileges |
| `404` | Video/upload not found, or unavailable to viewer |
| `409` | Resource state conflict / duplicate conflicting operation |
| `413` | File exceeds configured size limit |
| `422` | Well-formed but unsupported/invalid media contents |
| `429` | Rate limit exceeded |
| `500` | Unexpected server error |
| `503` | Dependency temporarily unavailable |

Error codes are stable; messages are intended for humans. No raw FFmpeg logs, credentials, internal R2 keys, or stack traces in API errors.

---

## 3. Endpoint index

| Method | Endpoint | Authorization | Purpose |
|---|---|---|---|
| `POST` | `/v1/videos` | Admin | Create video draft |
| `POST` | `/v1/videos/{id}/upload-url` | Admin | Issue/renew source upload URL |
| `POST` | `/v1/videos/{id}/complete-upload` | Admin | Verify source and queue jobs |
| `GET` | `/v1/videos/{id}` | Admin / eligible viewer | Read video and status |
| `GET` | `/v1/videos/{id}/playback` | Eligible viewer | Obtain HLS URL |
| `GET` | `/v1/videos` | Admin / viewer | Cursor-paginated video list |
| `PATCH` | `/v1/videos/{id}` | Admin | Update metadata / publication |
| `POST` | `/v1/videos/{id}/retry` | Admin | Retry failed transcoding |
| `DELETE` | `/v1/videos/{id}` | Admin | Schedule video deletion |
| `POST` | `/v1/videos/{id}/thumbnail/upload-url` | Admin | Issue custom thumbnail upload URL |
| `POST` | `/v1/videos/{id}/thumbnail/complete-upload` | Admin | Validate and activate custom thumbnail |
| `DELETE` | `/v1/videos/{id}/thumbnail` | Admin | Remove custom thumbnail; restore generated fallback |

No endpoint sends media bytes through Cloud Run. The two *upload-url* operations return signed R2 PUT instructions.

---

## 4. Video endpoints

### 4.1 Create video

**`POST /v1/videos`** — `201 Created`  
**Query parameters:** None  
**Body:**

```json
{
  "title": "Introduction to Faith",
  "description": "An introductory lesson"
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `title` | string | Yes | Trimmed, length 1–200 |
| `description` | string or null | No | Max 5,000 chars; absent means `null` |

**Response `201`:** Standard video resource with `status=CREATED`, `publicationStatus=DRAFT`, null media metadata, `thumbnail={"status":"PENDING","source":"NONE","url":null}`, and timestamps. Also set `Location: /v1/videos/{id}`.

**Behavior:** Insert video metadata only. No R2 URL and no background work.  
**Errors:** `400`, `401`, `403`.

### 4.2 Generate / renew source upload URL

**`POST /v1/videos/{id}/upload-url`** — `200 OK`  
**Path:** `id` required UUID  
**Query:** None  
**Body:**

```json
{
  "fileName": "introduction.mp4",
  "contentType": "video/mp4",
  "sizeBytes": 524288000
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `fileName` | string | Yes | Nonempty filename; informational only |
| `contentType` | string | Yes | Exactly `video/mp4` for MVP |
| `sizeBytes` | integer | Yes | Positive, at most configured max |

**Response `200`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "UPLOADING",
  "upload": {
    "uploadId": "04d1790f-f941-4ba6-8d97-0e6830ca4394",
    "method": "PUT",
    "url": "https://<presigned-r2-put-url>",
    "headers": {"Content-Type": "video/mp4"},
    "expiresAt": "2026-10-13T14:15:00Z"
  }
}
```

**Behavior:**

1. Only allowed in `CREATED` or `UPLOADING` while video is not deleting.
2. Create a **new upload attempt identifier and unique, immutable source object key**; invalidate the *logical* previous attempt in the database. Do not assume an earlier R2 presigned URL can be revoked; it may still write only to its old isolated key until expiration.
3. Store the current upload attempt ID, expected size, and key server-side. Issue signed PUT URL lasting **15 minutes**.
4. Set `status=UPLOADING` and return the signed URL and exact required headers. Client must send these headers when PUTting to R2.
5. Do not trust `fileName`, MIME type, or claimed size as proof of actual media contents.

**Errors:** `400 INVALID_FILE_TYPE` / invalid fields, `413 FILE_TOO_LARGE`, `404 VIDEO_NOT_FOUND`, `409 INVALID_STATUS_TRANSITION`.

**Important implementation invariant:** The current upload attempt must be persisted durably (e.g., `active_upload_id`, `source_key`, `expected_size_bytes`, and expiration on `videos`, or an upload-attempt table). Reissued upload URLs must not overwrite already confirmed originals. Configured upload-size enforcement must work for the chosen R2 upload mechanism; checking a declared size alone is not an enforcement mechanism.

### 4.3 Complete source upload

**`POST /v1/videos/{id}/complete-upload`** — `202 Accepted`  
**Path:** `id` required UUID  
**Query:** None  
**Body:**

```json
{"uploadId": "04d1790f-f941-4ba6-8d97-0e6830ca4394"}
```

**Response `202`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "QUEUED",
  "processingJobId": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
  "thumbnailStatus": "PENDING"
}
```

**Behavior:**

1. Compare `uploadId` with the active attempt and reject stale attempts (`409 STALE_UPLOAD_ATTEMPT`).
2. Perform R2 `HEAD` of that attempt's source object; reject missing objects (`404 UPLOAD_NOT_FOUND`).
3. Check observed size, allowed maximum, and expected size. Actual MP4 media streams/codecs are validated with FFprobe in background processing; invalid files fail safely and never become ready.
4. In a DB transaction, atomically transition from `UPLOADING` to `QUEUED` and create a `PENDING` transcoding job, plus a durable request for independent generated-thumbnail processing.
5. Dispatch jobs asynchronously with a retrying dispatcher/reconciler; do not wait for FFmpeg before returning.
6. **Idempotency:** Repeated completion of the *same accepted `uploadId`* returns `202` with the existing `processingJobId` and current video status; no duplicate jobs. A different/stale `uploadId` must not be accepted.

**Errors:** `400`, `404 UPLOAD_NOT_FOUND`, `409 STALE_UPLOAD_ATTEMPT` / `INVALID_STATUS_TRANSITION`, `413`.

### 4.4 Get video

**`GET /v1/videos/{id}`** — `200 OK`  
**Path:** `id` UUID  
**Query/body:** None

**Response `200`:** Standard video resource (Section 2.2); admin responses may include `processingError`. Intended for admin polling every ~5 seconds while `QUEUED` or `PROCESSING`; stop polling on `READY` or `FAILED`. Thumbnail generation may still be `PENDING` after the video is `READY`, and its status is independently observable via `thumbnail`.

**Errors:** `400`, `401`/`403` for protected access, `404`.

### 4.5 Get playback information

**`GET /v1/videos/{id}/playback`** — `200 OK`  
**Path:** `id` UUID  
**Query/body:** None

**Response `200`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "playback": {
    "type": "hls",
    "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/hls/v1/master.m3u8"
  }
}
```

**Behavior:** Require `status=READY` and `publicationStatus=PUBLISHED` for regular viewers. Admins may request previews of unpublished `READY` videos; this only controls *API discovery*, not CDN authorization. Build URL from the configured CDN domain and stored `master_key`. Client downloads the manifest, variant playlists, and segments directly from Cloudflare. Do not store a fixed public URL in the DB.

**Errors:** `404` for not-visible videos; `409 VIDEO_NOT_READY` for a visible-to-admin video that is not ready.

### 4.6 List videos

**`GET /v1/videos`** — `200 OK`  
**Body:** None

| Query param | Type | Required | Default / validation |
|---|---|---|---|
| `limit` | integer | No | `20`; range `1..100` |
| `cursor` | string | No | Opaque pagination cursor |
| `status` | enum | No | Admin only; `CREATED`, `UPLOADING`, `QUEUED`, `PROCESSING`, `READY`, `FAILED`, `DELETING` |
| `publicationStatus` | enum | No | Admin only; `DRAFT` or `PUBLISHED` |
| `search` | string | No | Trimmed, max 200 chars; case-insensitive title contains |

Example: `GET /v1/videos?limit=20&status=READY&publicationStatus=PUBLISHED&search=faith`

**Response `200`:**

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Introduction to Faith",
      "description": "An introductory lesson",
      "status": "READY",
      "publicationStatus": "PUBLISHED",
      "sizeBytes": 524288000,
      "durationSeconds": 1475.5,
      "thumbnail": {
        "status": "READY",
        "source": "CUSTOM",
        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"
      },
      "publishedAt": "2026-10-13T15:00:00Z",
      "createdAt": "2026-10-13T14:00:00Z",
      "updatedAt": "2026-10-13T15:00:00Z"
    }
  ],
  "pagination": {"nextCursor": null, "hasMore": false}
}
```

**Behavior:** Sort descending by `(created_at, id)` with a deterministic opaque cursor. The cursor includes/validates filter context, so it cannot accidentally continue a different query. Viewer results always filter to `READY`, `PUBLISHED`, non-deleting videos; viewer-supplied admin-only status filters are rejected with `400`. Admins can list all lifecycle states.

**Errors:** `400 INVALID_QUERY`, authentication/authorization errors as applicable.

### 4.7 Update metadata or publication

**`PATCH /v1/videos/{id}`** — `200 OK`  
**Path:** `id` UUID  
**Query:** None  
**Body:** One or more of:

```json
{
  "title": "Introduction to Christian Faith",
  "description": "Updated lesson description",
  "publicationStatus": "PUBLISHED"
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `title` | string | No | 1–200 chars after trimming |
| `description` | string or null | No | Max 5,000 chars |
| `publicationStatus` | enum | No | `DRAFT`, `PUBLISHED` |

**Response `200`:** Entire updated video resource.

**Behavior:** Partial update of supplied fields. Publishing requires `status=READY`; set `published_at=now()` on the first transition `DRAFT -> PUBLISHED`. Repeating `PUBLISHED` preserves the existing timestamp. Unpublishing sets `published_at=null`. Changes to title/description do not alter processing state. Reject all edits while `DELETING`.

**Errors:** `400`, `404`, `409 VIDEO_NOT_READY` / `INVALID_STATUS_TRANSITION`.

### 4.8 Retry video processing

**`POST /v1/videos/{id}/retry`** — `202 Accepted`  
**Path:** `id` UUID  
**Query/body:** None

**Response `202`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "QUEUED",
  "processingJobId": "ac9afc7e-d6d1-4b5d-b0f2-fdb591862ea5",
  "attempt": 2
}
```

**Behavior:** Only `FAILED` videos with a retained validated source may be retried. Create a fresh processing attempt with unique HLS output prefix and increment attempt count. Atomically change video to `QUEUED` and create durable job request. Reject concurrent duplicate retries with `409` rather than launching multiple jobs. Previous attempts remain for debugging. Automatically generated thumbnail processing is not coupled to a transcode retry; its own recovery is handled by worker reconciliation. Publication remains `DRAFT` in this MVP retry path.

**Errors:** `404`, `409 INVALID_STATUS_TRANSITION`, `503` if service unavailable before durable acceptance.

### 4.9 Delete video

**`DELETE /v1/videos/{id}`** — `202 Accepted`  
**Path:** `id` UUID  
**Query/body:** None

**Response `202`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "DELETING"
}
```

**Behavior:** Atomically set `status=DELETING` and create a durable cleanup request. Immediately block API playback, upload, mutation, and job scheduling. Cleanup worker cancels or fences active jobs, then deletes original source objects, all HLS attempts, and generated/custom thumbnails from R2. When complete, delete or archive related DB rows per retention policy. Repeated DELETE while `DELETING` returns `202`; after full deletion returns `404`. Note: previously retrieved public CDN URLs may remain cache-accessible until expiration/purge; immediate CDN revocation requires a separate access-control/cache-invalidation design.

**Errors:** `404`, `409` for conflicting operations not otherwise handled.

---

## 5. Thumbnail endpoints and behavior

Thumbnails are part of the approved MVP. **Every successfully confirmed video upload must trigger generated-thumbnail extraction independently of video transcoding.** Custom thumbnail uploads are permitted before either background task finishes. There is one active thumbnail: a valid custom thumbnail wins; otherwise the generated thumbnail is active. Generated thumbnails are kept as permanent fallback assets during the life of the video.

**Validation source of truth:** The separately approved *Video Thumbnail — MVP Technical Specification* defines exact dimensions, aspect ratio, size, formats, and cropping policy. This API contract intentionally does **not** invent numeric limits absent from that specification. Both frontend crop checks and backend validation apply; backend is authoritative.

### 5.1 Get custom thumbnail upload URL

**`POST /v1/videos/{id}/thumbnail/upload-url`** — `200 OK`  
**Path:** `id` UUID  
**Query:** None  
**Body:**

```json
{
  "fileName": "faith-cover.jpg",
  "contentType": "image/jpeg",
  "sizeBytes": 183420
}
```

**Response `200`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "upload": {
    "uploadId": "50fd0382-794f-4c9b-9a12-60e92a89e008",
    "method": "PUT",
    "url": "https://<presigned-r2-thumbnail-put-url>",
    "headers": {"Content-Type": "image/jpeg"},
    "expiresAt": "2026-10-13T14:15:00Z"
  }
}
```

**Behavior:** Verify admin and video not deleting; validate declared metadata against configured thumbnail specs, then issue a 15-minute signed PUT URL to a new **unique temporary thumbnail key**, tracking the active custom-upload attempt. Do not replace the active thumbnail on URL issuance or an R2 PUT alone. The source video may be `CREATED`, `UPLOADING`, `QUEUED`, `PROCESSING`, `READY`, or `FAILED`.

**Errors:** `400 INVALID_THUMBNAIL_TYPE` / invalid metadata, `413`, `404`, `409`.

### 5.2 Confirm and activate custom thumbnail

**`POST /v1/videos/{id}/thumbnail/complete-upload`** — `200 OK`  
**Path:** `id` UUID  
**Query:** None  
**Body:**

```json
{"uploadId": "50fd0382-794f-4c9b-9a12-60e92a89e008"}
```

**Response `200`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "thumbnail": {
    "status": "READY",
    "source": "CUSTOM",
    "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"
  }
}
```

**Behavior:** Ensure upload ID matches current attempt; verify object, inspect actual image format, byte size, resolution, and aspect ratio per approved spec. Only after successful validation atomically replace `custom_thumbnail_key` (or equivalent). Existing valid active thumbnail remains untouched on any failure. If the generated thumbnail arrives later, retain it without overriding custom. Repeating this request for an already accepted upload ID returns the active result without reactivating superseded media. A stale attempt returns `409 STALE_UPLOAD_ATTEMPT`.

**Errors:** `400 INVALID_THUMBNAIL`, `404 THUMBNAIL_UPLOAD_NOT_FOUND`, `409`, `413`.

### 5.3 Remove custom thumbnail

**`DELETE /v1/videos/{id}/thumbnail`** — `200 OK`  
**Path:** `id` UUID  
**Query/body:** None

**Response `200`:**

```json
{
  "videoId": "550e8400-e29b-41d4-a716-446655440000",
  "thumbnail": {
    "status": "READY",
    "source": "GENERATED",
    "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg"
  }
}
```

**Behavior:** Clear the custom thumbnail pointer; resolve the active thumbnail to the generated fallback if available. If generation is not complete, return `{"status":"PENDING","source":"NONE","url":null}` instead. A missing custom thumbnail is a no-op, making delete idempotent. The generated key is **never** removed by this operation. Previously uploaded custom objects can be cleaned up asynchronously after pointer changes.

**Errors:** `404 VIDEO_NOT_FOUND`, `409` for deleting video.

### 5.4 Automatic generated thumbnail

No manual endpoint is required to trigger generation. `complete-upload` creates the durable generation work. The worker extracts a thumbnail with FFmpeg, writes a stable generated-thumbnail object, and stores its key. It does **not** block video processing or override an existing valid custom thumbnail. Failures remain observable via `thumbnail.status` and processing telemetry; generation can be retried independently.

---

## 6. End-to-end sequences

### 6.1 Upload + processing

1. Admin `POST /videos` -> `CREATED` + video UUID.
2. Admin `POST /videos/{id}/upload-url` -> `UPLOADING` + `uploadId` + presigned PUT.
3. Browser `PUT` bytes **directly to R2** with returned headers.
4. Browser `POST /videos/{id}/complete-upload` with `uploadId` -> `202 QUEUED`.
5. Dispatcher launches independent **HLS transcoding** and **generated thumbnail** jobs.
6. UI polls `GET /videos/{id}` every ~5 seconds; transcode eventually `READY` or `FAILED`. Thumbnail status may change independently.
7. Admin `PATCH /videos/{id}` with `publicationStatus=PUBLISHED` after `READY`.
8. Viewer `GET /videos/{id}/playback` receives CDN HLS master URL; HLS player downloads playlists and segments from CDN.

### 6.2 Custom thumbnail before processing finishes

1. At any time after video creation, admin calls `POST /videos/{id}/thumbnail/upload-url`.
2. Browser PUTs image bytes directly to R2.
3. Admin calls `POST /videos/{id}/thumbnail/complete-upload` with upload ID.
4. API validates actual image properties; valid custom becomes active, invalid custom leaves old thumbnail in place.
5. Generated-thumbnail job eventually writes fallback and **does not replace** active custom.
6. `DELETE /videos/{id}/thumbnail` restores generated fallback when present.

---

## 7. Implementation invariants and handoff checks

### Upload correctness

- Both source-video and custom-thumbnail uploads are **attempt-scoped**. Attempt IDs and temporary/object keys must be persisted, and completions must match the current active attempt.
- R2 presigned PUT URLs are not revocable on demand; isolate each upload attempt to avoid stale URLs overwriting active assets.
- A successful browser PUT is not a database confirmation; confirmation requires the backend's verification endpoint.
- Background media validation must reject malformed or unsupported files before publishing assets. Source dimensions are obtained via FFprobe; they need not be persisted solely for HLS delivery.

### Concurrency and durability

- State transitions use database conditions/locking so concurrent complete, retry, publish, and delete operations cannot create conflicting outcomes.
- Processing work and thumbnail work are durably recorded before returning `202`; dispatcher failures must be recoverable.
- Cloud Run Job retries must use unique output prefixes and may publish keys only if their attempt remains current.
- Video becomes `READY` only after valid master playlist and referenced outputs are confirmed present. Thumbnail generation never holds up `READY`.
- Delete must fence or reconcile in-flight jobs before their output can become visible.

### Delivery and authorization

- R2 source objects and temporary upload objects remain private.
- CDN hostname comes from server configuration; the DB stores object **keys**, not presigned URLs or full delivery URLs.
- Publishing changes API visibility, **not** CDN permissions. Public HLS delivery must be explicitly accepted as an MVP tradeoff if video viewing is supposed to be restricted.
- Use appropriate manifest/segment MIME types, CDN caching, R2 upload CORS, and player-compatible HLS manifests.

### Minimum acceptance tests

1. Create -> upload URL -> R2 PUT -> confirm -> processing -> READY -> publish -> playback succeeds.
2. Duplicate `complete-upload` requests create only one transcoding attempt.
3. Old upload URL/attempt cannot replace the active source after URL renewal.
4. Invalid upload is rejected and cannot become `READY`.
5. Processing crash is recorded and `retry` creates one new attempt.
6. Publishing before `READY` is rejected with `409`.
7. Unpublished video is not discoverable/playable through viewer APIs.
8. Cursor pagination has deterministic ordering and does not duplicate/skips records on static data.
9. Thumbnail generation and video transcoding proceed independently.
10. Custom thumbnail validates on backend; failed upload doesn't replace current active image.
11. Custom thumbnail wins even if generated thumbnail completes later; deleting custom restores generated fallback.
12. Deletion immediately blocks API access and eventually removes video and thumbnail objects.

## 8. Schema implications (for database specification)

This API requires durable storage for the following concepts, even if the database remains small:

- `videos`: id, metadata, lifecycle `status`, `publication_status`, `published_at`, source and master keys, `size_bytes`, `duration_seconds`, timestamps; active upload attempt details and verification metadata; thumbnail active/custom/generated keys and state (or separate image metadata).
- `video_processing_jobs`: id, video_id, status, attempt, output_prefix, errors, timestamps, Cloud Run execution reference, durable dispatch status.
- Durable independent **thumbnail-generation work** and **deletion cleanup** work (can use a general background-work/outbox table or explicitly documented jobs table design).

**Important:** The original two-table sketch is not, by itself, sufficient to implement reliable upload-attempt fencing, independent thumbnail work, and asynchronous cleanup unless those concepts are added as columns/records. Finalize the SQL schema in the database-design handoff to satisfy these requirements.

## 9. Configuration values to define before deployment

The following are configuration knobs rather than hardcoded API values:

- Maximum MP4 upload size (bytes); signed-upload enforcement strategy.
- Approved thumbnail formats, dimensions, aspect ratio, and maximum bytes (use locked thumbnail specification).
- CDN media hostname and R2 bucket/key prefixes.
- Upload presigned URL lifetime (contract default: 900 seconds).
- Poll interval suggestion (UI default: ~5 seconds).
- Cloud Run Jobs limits, retry counts, dispatcher schedule, and cleanup retention.
- Identity provider/admin role rules; whether viewer read APIs require authentication.
- CORS allowed origins, rate limits, log retention, and CDN-cache purge policy.

**End of contract.**
