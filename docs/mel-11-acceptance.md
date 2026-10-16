# MEL-11 — independent generated thumbnails

Local acceptance completed 2026-10-16. Live Cloud Run/R2 evidence remains a
separate MEL-16 gate. This ticket changes no HTTP shapes or generated packages.

The initial HTTP tracer observed PENDING after executing a seeded THUMBNAIL job.
It passed after shared worker dispatch called the independent thumbnail process.
The job loads its accepted source from PostgreSQL and reads private storage through
the same bounded provider boundary as video work. It validates/decodes real media
with FFprobe/FFmpeg, extracts the first decoded video frame, scales using displayed
aspect ratio (including SAR and rotation), and fits it on a black 1280 × 720 canvas.
Using the first frame also supports a valid single-frame MP4. Fit dimensions round
down to even pixels for JPEG encoding; there is no cropping. The resulting JPEG
is probed and decoded before storage, then its stored size and bytes are verified.

The shared Cloud Run entry point remains `python -m src.worker run --job-id UUID`.
It resolves the persisted job kind. VIDEO and THUMBNAIL use independent execution
budgets: three total attempts for transient failures, increasing delays of one and
four seconds by default, and one attempt for a permanently invalid source. Runtime
settings control delays and FFmpeg/provider bounds. Job attempt history records
outcomes; a duplicate invocation cannot steal the current claim during backoff.

Thumbnail processing never changes video lifecycle, publication, playback,
processing errors, or source_validated. Generated completion updates only its own
status/key and the current job. Active selection remains custom-first; generated
completion cannot erase a custom image selected concurrently. Failed generation
without a valid custom image projects FAILED/NONE/null, while a custom image stays
active. READY videos can publish while generation is pending or failed.

Every attempt records its finite output-key manifest before a create-only PUT.
Namespaces include execution attempt and claim token. Parent-video/current-job/
claim-token checks fence registration, writes, and final activation; final updates
lock parent video before job. A deleted or superseded job cannot activate its image.
Recorded manifests retain partial outputs for explicit deletion. These database
fences do not claim to cancel a remote in-flight write; production deletion guards
and their live proof are handled separately.

Acceptance uses HTTP through the real app and PostgreSQL, controlled object-storage
and clock/sleep boundaries, and real image processing. Seeded sources/jobs avoid
runtime-order dependencies on upload/HLS tickets. Eighteen cases cover:

- Independent completion while video is QUEUED, PROCESSING, FAILED, or READY.
- Decoded JPEG dimensions and actual black/content pixels for portrait, landscape,
  anamorphic, rotated, and single-frame sources.
- Transient write failures with three actual extraction attempts, isolated outputs,
  manifested keys and increasing controlled delays.
- Permanent failure once, transient exhaustion, and rejection of unverified stored
  image bytes; video readiness/publication remain available.
- Custom activation racing generated PUT, preserved generated fallback, and failure
  preserving custom choice, source validity, and existing video errors.
- Deletion/superseding during PUT and duplicate execution while a claim is active.

Verification before final integration merge: `make check` passes contract/example
validation, Ruff/format and strict Pyright. `uv run --locked pytest -q` passes
156 tests, including the shared retry foundation and all real FFmpeg cases.

The extraction and worker policy follow the approved canonical specification and
[FFmpeg scale/pad documentation](https://ffmpeg.org/ffmpeg-filters.html#scale).
Resource sizing and live provider behavior still require deployed evidence.
