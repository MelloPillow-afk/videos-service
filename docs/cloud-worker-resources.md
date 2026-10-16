# Native worker resource checkpoint — 2026-10-16

The deployed worker uses the reviewed AMD64 image, **2 CPU / 4 GiB / 1200s**,
one task per execution and **zero platform retries**. The following are actual
Cloud Run v2 **task** times; execution scheduling/provisioning time is excluded.
They are not FFmpeg-only CPU times.

| Execution | Work | Native task elapsed | Result |
| --- | --- | --- | --- |
| `videos-worker-bmf2h` | Independent zero-ID readiness probe | 10.031s | Success / `no_op` |
| `videos-worker-tvvvf` | First video job | 30.383s | Success |
| `videos-worker-wsh55` | Independent thumbnail job | 10.277s | Success |
| `videos-worker-82kdx` | Later independent thumbnail job | 16.365s | Success |
| `videos-worker-gltdb` | Interrupted video job | Not claimed | Task condition `CONDITION_FAILED`, reason `CANCELLED`; status code 1, “Cancelled by user.” |
| `videos-worker-krd85` | Same video job after explicit recovery | 230.455s | Success |

The recovered source fixture is exactly **300 seconds**, **1280×720**, **12 fps**,
with AAC audio, **25,070,681 bytes**.

Every task reports `retried=0`. The cancelled task omits `completionTime`; its
explicit cancelled condition/result is retained in the evidence rather than
inventing a duration. The recovered task completes within the configured budget.
Successful completion provides no OOM failure for these fixtures; it does not
establish a worst-case budget for every admitted five-minute/100 MiB source.

[Portable API/metric observations](evidence/cloud-worker-resources-2026-10-16.json)
contain sanitized task metadata and existing Cloud Monitoring samples. No new
monitoring role, API enablement or quota was needed. The worker-filtered
`container/memory/usage` distribution has a single-observation value of
**307,310,592 bytes (293.074 MiB)** at 15:08 UTC. The largest observed memory
utilization sample is **7.155%** of allocation; CPU utilization includes an
observed **103.163%** sample. These are reported samples, not continuous peaks,
per-execution maxima or a reason to infer additional available CPU.

Cloud Monitoring groups these distributions by job, without execution IDs;
concurrent tasks cannot be attributed individually. Multiple-observation means
are not maxima, and samples can persist after task completion. Metrics are
sampled every 60 seconds and may appear up to 120 seconds later according to the
[Google metric definitions](https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z).
Per-task start/completion/result fields follow the
[Cloud Run task API](https://docs.cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs.executions.tasks).
Full playback, state, cancellation/recovery and guarded deletion evidence belongs
to the separate live acceptance record.
