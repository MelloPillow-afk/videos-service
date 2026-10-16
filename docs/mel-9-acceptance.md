# MEL-9 — accepted source to playable HLS

Local worker acceptance on 2026-10-16 uses the real FastAPI application,
PostgreSQL, FFprobe, FFmpeg, and signed test identities. Storage is controlled at
its external boundary; production R2/Cloud Run/CDN evidence remains MEL-16.

`python -m src.worker run --job-id UUID` loads and atomically claims one persisted
VIDEO job. The shared launch payload contains only that UUID. Duplicate workers
cannot claim an already running/completed job. Each execution receives a unique
output namespace. The existing jobs table stores the claim token and cumulative
finite output-key manifest, committed before any output PUT. Ordinary output
writes are create-only. Every write phase and final READY transition rechecks the
current job/token and non-deleting video; encoding and provider calls hold no
transaction locks. These fences protect API state; final storage deletion still
requires the separately agreed writer-drain/guard policy.

Actual MP4 contents and finite positive duration are probed, and all selected
video/audio packets are decoded before encoding. Maximum source admission remains
100 MiB / 300 seconds. Invalid containers, corrupt packets, excessive duration,
and dimensions outside configured processing limits fail with safe errors.
Provider/runtime failures remain distinguishable from permanent source rejection.
The validated source remains private and is retained. READY remains DRAFT, and
thumbnail state is independent. Failure explanations are visible in administrator
HTTP detail; raw paths, source bytes, provider exceptions and FFmpeg stderr are
never returned.

The processing policy uses the first non-cover video and first audio stream.
Renditions use supported 360/720/1080 tiers by the shorter normalized display
axis, fitted inside 16:9 bounds (swapped for portrait); sources below360 receive
one source-sized rendition. Rotation and sample aspect ratio are normalized
without increasing either coded dimension; dimensions round down to even pixels
for 4:2:0, at most one pixel per axis. H.264/libx264, veryfast, CRF23, yuv420p,
30fps, and approximate peak video rates1/3/6Mbit/s use a2× VBV buffer. Audio is
AAC stereo48kHz128kbit/s when present; silent sources remain video-only. VOD HLS
uses4s MPEG-TS segments, aligned forced keyframes and a master with actual
rendition dimensions and conservative peak bandwidth.

Generated variants are fully decoded locally, their durations checked, and all
segments/manifests uploaded in that order with the master last. Every uploaded
object must be available with the expected length before current work can become
READY. Output keys remain cumulative across future retries so deletion can fence
older attempts too. Original source and publication state remain unchanged.

Initial resource defaults are2 FFmpeg threads, single-thread filter execution,
30s probing,300s source decoding,900s per rendition/verification process,60s per
provider operation, and a1GiB generated-output check. Source dimensions are capped
at8192 per axis and8,294,400 coded pixels. Sequential encoding bounds peak
resources. A starting Cloud Run allocation of2vCPU/4GiB, one task/parallelism1,
20min hard task timeout and provider retries0 needs representative cloud
measurement; these are local defaults, not live capacity or completion evidence.
Subprocess timeouts kill and reap FFmpeg; temporary media is removed on exit.
There is no periodic dispatcher, reconciliation, cleanup scheduler or provider
retry multiplier. MEL-10 owns automatic media retries and manual recovery.

Verification includes real generated fixtures for1080 landscape,720 portrait,
4:3 and below360 sources; genuine300s and300.1s media; AAC and video-only HLS;
rotation and non-square sample aspect; corrupt bytes and corrupt media packets
inside valid MP4 metadata; actual WebM despite an MP4 object key; missing stored
segments; duplicate workers; deletion during output; supersession after uploads;
and an encoder timeout. Assertions use administrator/anonymous HTTP reads,
persisted effects and decodable externally stored HLS. The first tracer failed
on the missing worker. Sanitized HTTP errors and temporary-timeout classification
each had a failing behavior test before implementation. Existing Yoyo rollback
acceptance now explicitly selects all migrations as this feature adds a second
migration dependency. CI installs FFmpeg/FFprobe for the real-media suite.

Before integration refresh, `make check` passed contract validation, 45 examples,
Ruff/format and strict Pyright; the full suite passed 102 tests (17 new
processing cases), with 78% overall measured coverage. Coverage includes shared
cloud adapters whose provider-request tests are owned by MEL-8.

Primary references used for the bounded implementation choices:

- [FFmpeg HLS muxer](https://www.ffmpeg.org/ffmpeg-formats.html#hls-2)
- [FFprobe metadata](https://ffmpeg.org/ffprobe.html)
- [FFmpeg scaling](https://ffmpeg.org/ffmpeg-filters.html#scale)
- [Cloud Run job launch API](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs/run)
- [R2 atomic conditional PUT](https://developers.cloudflare.com/r2/api/s3/extensions/#conditional-operations-in-putobject)
- [R2 ambiguous in-flight writes](https://developers.cloudflare.com/r2/reference/consistency/#negative-reads-and-in-flight-writes)
