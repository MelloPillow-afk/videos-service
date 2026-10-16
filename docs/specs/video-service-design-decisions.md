# Videos service design decisions

Accepted decisions from the design interview on 2026-10-16. This document supplements the business requirements; `api-specs/index.yaml` remains authoritative for HTTP behavior. Contract descriptions and the older business specification will be reconciled after the design interview.

Access and identity decisions are recorded in `../adr/0001-public-shared-video-library.md` and `../adr/0002-neon-auth-and-production-database.md`. Domain terminology lives in `../../GLOSSARY.md`.

## Interview showcase scope

This MVP is a working project to hand over to an interviewer and demonstrate systems-design thinking. Its scope favors a coherent end-to-end flow and explicit trade-offs without production-level recovery infrastructure. Scheduled cleanup jobs and cron-based maintenance are outside scope. There is no automatic 24-hour abandoned-upload cleanup or seven-day failed-output cleanup policy. Abandoned uploads and partial failed outputs may remain stored during the showcase; explicitly deleting a video still removes its associated media as described below.

Launch processing directly after accepting the upload, retaining the agreed worker execution retries. Periodic dispatch reconciliation is outside scope. A crash between recording accepted work and launching its worker may require manual recovery. This deliberately relaxes the original specification's automatic recovery guarantee; persisting a job record alone does not guarantee eventual dispatch. The manual recovery procedure remains to be specified during implementation.

## Rejected source confirmation

Requesting an upload URL returns instructions; the client uploads bytes directly to R2. The complete-upload endpoint verifies the uploaded object and durably records processing work only after verification succeeds.

A missing object, excessive size, or size mismatch returns the relevant error, leaves the video UPLOADING, and queues no processing work. The administrator may obtain a new upload URL and retry on the same video record. A stale upload ID leaves the current attempt unchanged.

## Invalid source discovered during processing

A corrupt or unsupported source leaves the video FAILED. Retry is available only for a retained valid source after a processing failure. The MVP recovery for an unusable source is to delete the failed video and create a new one; source replacement on the failed record is outside scope.

## Failed generated-thumbnail fallback

Removing a custom thumbnail when generated-thumbnail processing has failed returns the active thumbnail with status FAILED, source NONE, and url null. The client displays a placeholder. Thumbnail failure does not prevent playback or publication of an otherwise ready video; viewer playback still requires publication.

## Media limits and thumbnail validation

The maximum MP4 source size is configurable and defaults to 100 MiB (104,857,600 bytes) for the five-minute MVP, replacing the initially approved 2 GiB default. Upload-URL issuance rejects declared sizes above the limit; source confirmation also checks the actual object size. The MVP deliberately does not guarantee enforcement during transfer: oversized bytes may reach R2, but oversized sources are rejected at confirmation and never enter processing. Rejected objects may remain until explicit video deletion or manual cleanup. This relaxes the original requirement for effective size enforcement during direct upload. Protection of confirmed source objects from subsequent writes remains an implementation verification requirement.

Custom thumbnails accept JPEG, PNG, or WebP, with a maximum size of 5 MiB (5,242,880 bytes) and exact dimensions of 1280 by 720 pixels (16:9). The client crops before upload. The backend validates the actual image, rejects invalid files, and preserves the existing thumbnail on failure. These requirements were approved during this interview in place of the unavailable separate thumbnail specification.

An administrator may publish a READY video while its generated thumbnail is PENDING or FAILED. A valid custom thumbnail remains preferred when available; otherwise the client shows a placeholder until a valid image is available. Thumbnail readiness does not gate publication.

## Playback outputs and duration

Generate 360p, 720p, and 1080p HLS versions where source resolution supports them, preserving the source aspect ratio and avoiding upscaling. Sources below 360p receive one version at their original resolution. Exact rendition sizing for portrait and unusual source dimensions remains to be specified.

The MVP maximum source duration is five minutes (300 seconds), configurable. Processing inspects actual duration and marks longer videos FAILED with an administrator-readable explanation. This replaces the proposed two-hour default.

Automatic thumbnails use a 1280 by 720 canvas. Fit the extracted frame inside the canvas with padding as needed, preserving the whole image instead of automatically cropping it. Custom thumbnails continue to be cropped by the client before upload.

## Original source retention

Keep the confirmed original source for the lifetime of the video, including after successful processing. Delete it as part of video deletion. This retains the option to reprocess the original later.

## Processing retries

Each video-processing job allows three total execution attempts for temporary failures, with increasing delays. Corrupt or unsupported media fails without automatic retries. After execution attempts are exhausted, video processing becomes FAILED; an administrator may explicitly retry a retained valid source using a new processing job. Generated-thumbnail jobs independently use the same bounded retry policy and never hold up video readiness.

## Permanent deletion

Deletion has no trash or restore window in the MVP. Accepting deletion immediately sets DELETING and blocks API playback discovery and further mutations. Remove application records after media cleanup succeeds. Temporary cleanup failures leave the video DELETING and are retried with increasing delays; persistent failures must be surfaced operationally. Cleanup is not abandoned after the three-attempt processing-job limit.

## Persistence model

Use three application tables, with Neon Auth owning identities and administrator roles:

| Table | Responsibility |
| --- | --- |
| `videos` | Metadata, lifecycle and publication state, accepted source and playback keys, and separate generated/custom thumbnail state. |
| `upload_attempts` | Source and custom-thumbnail attempts, object keys, expected sizes, expiration, and acceptance state. |
| `jobs` | Video processing, thumbnail generation, and deletion work; job state, execution-attempt counts, and sanitized errors. |

Keep accepted completion idempotent and state transitions conditional. Workers may publish results only while their video and job are current and the video is not deleting. These correctness requirements remain in scope even without periodic reconciliation.

## Implementation verification and handoff

The design interview establishes behavior and scope; schema DDL and worker implementation details follow during specification and implementation. Verify Neon Auth token settings and the deployed current-role lookup schema. Verify conditional R2 writes protect accepted source and thumbnail objects from still-valid upload URLs. Specify rendition sizing for portrait sources, encoding settings, job-launch ordering, and manual recovery commands. Document these implementation choices and their acceptance checks in the build specification.

Before implementation, reconcile the OpenAPI descriptions and existing business specification with these accepted decisions, validate the contract, and regenerate affected output. The intended demonstration is create, direct upload, confirm, process, publish, and public playback, with independent thumbnails and explicit deletion. Include focused checks for stale uploads, duplicate completion, permission changes, invalid media, and deletion racing processing.
