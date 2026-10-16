# MEL-10 — processing retries and manual recovery

Temporary media failures allow three total executions per persisted job. The
same claim owner runs them with increasing delays (1 second then 4 seconds by default), using
new claim tokens and isolated output prefixes each time. Configure two finite,
nonnegative, increasing values with `MEDIA_RETRY_DELAYS_SECONDS=[1,4]`.
Configure Cloud Run provider retries to zero to avoid multiplying the budget.

The job remains RUNNING between execution attempts, so a duplicate worker
cannot steal a delayed retry. Counts increment when an execution starts.
`jobs.execution_history` retains safe start/failure/success/interruption events;
`jobs.output_keys` accumulates every attempt's complete manifest before any
create-only write. No separate application table, queue platform, cron,
periodic reconciliation or abandoned-object cleanup is added.

Permanent invalid media fails once. Runtime/provider failures preserve a
previously validated source. Exhaustion becomes FAILED; an administrator can
POST `/v1/videos/{id}:retry` only with a retained validated source still available.
One transaction supersedes the previous VIDEO job, records a new job/namespace,
and returns QUEUED/DRAFT before direct submission. Concurrent requests produce
one accepted retry and one 409. Old job diagnostics/output manifests remain.
Thumbnail jobs are unaffected. The response's `attempt` is the VIDEO job number
(first explicit retry is 2); execution-attempt counts are tracked within each job.
Unusable sources require deletion and recreation.

## Operator procedure

Use the service's normal database/provider environment and explicit migrations.
Inspect a specific persisted job and its video; do not infer launch success from
the existence of a job row. Useful fields are job ID/kind/current flag, state,
execution count/reference, error code/message, execution history and output keys.
Ordinary API resources contain no upload authorization or private source keys.

RECORDED, LAUNCH_FAILED and LAUNCHED work can be explicitly relaunched while
current and eligible. No media is processed inline by this command:

```sh
uv run --locked python -m src.worker recover --job-id JOB_UUID --gcloud-auth
```

On a local operator machine, `--gcloud-auth` explicitly uses the installed
`gcloud` CLI's current login with `auth print-access-token --quiet`. Authenticate
the intended operator account first and give it `run.jobs.runWithOverrides` on
the configured job. Token output and CLI diagnostics are captured without logging;
a ten-second credential timeout kills and reaps the process. This opt-in exists
only for `recover`; the runtime image does not install gcloud. Without the flag,
recovery continues to use a launch-capable runtime metadata identity. There is no
automatic fallback to a local account, and API/worker runtime identity is unchanged.

A lost submission response can mean an execution already exists. Inspect Cloud
Run executions for the configured worker job and the UUID supplied in its args;
check all relevant executions, including ones whose submission response was lost.
The stored reference may be a launch Operation name rather than an Execution.

```sh
gcloud run jobs executions list --job=WORKER_JOB --region=REGION
gcloud run jobs executions describe EXECUTION --region=REGION
```

A RUNNING claim is never reset because its timestamp is old. First verify the
previous execution has terminated. If it is still active, cancel it explicitly
and inspect its terminal state before proceeding:

```sh
gcloud run jobs executions cancel EXECUTION --region=REGION
uv run --locked python -m src.worker recover --job-id JOB_UUID --gcloud-auth \
  --previous-execution-terminated
```

The flag is an operator assertion, not an automatic cloud termination check.
Recovery invalidates the old claim token and preserves consumed executions and
all output manifests. If three media executions were consumed, recovery records
FAILED and returns an explanatory error instead of starting a fourth. A validated
retained source can then use the administrator retry endpoint; invalid/unverified
sources use deletion and recreation. Superseded, deleted and finished work is
rejected. Deletion has its separate retry policy and does not inherit this media
budget; its approved permanent-guard policy is documented in
[deletion acceptance](deletion-acceptance.md).

Unknown/rejected relaunches stay visible as LAUNCH_FAILED; inspect provider state
before trying again. An interrupted worker or direct launch may require this
manual procedure. No startup scan or background reconciler repairs it. API
publication fences do not prove that an ambiguous storage PUT has drained; this
procedure makes no additional storage-deletion guarantee.

The [Cloud Run execution commands](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/executions)
and [cancellation command](https://docs.cloud.google.com/sdk/gcloud/reference/run/jobs/executions/cancel)
are the provider references for the inspection/cancellation steps. Live execution
and credentials evidence is reserved for MEL-16.

## Local evidence

The contract descriptions/job numbering were updated, validated with
`make lint-api` (45 examples), and regenerated through `ag-generate` before
handwritten behavior. The generator reports 13 operations and 23 HTTP cases;
handwritten recovery tests remain outside generated packages.

The first transient-storage tracer failed before retry orchestration; the explicit
HTTP tracer returned an example 202 while detail remained FAILED before real
retry behavior.19 recovery cases now cover temporary success, exhaustion and
increasing delays, permanent-source rejection, cumulative attempt manifests,
source-validation retention, concurrent explicit retries, current-role denial,
native 422, missing source, launch interruption, manual relaunch, stale/deleting/
finished jobs, mandatory termination confirmation independent of timestamp age,
interrupted final execution without a fourth execution, deletion during retry
backoff, and cleanup relaunch without applying the media budget or clearing the
pending cleanup-policy diagnostic.

They use the real app, PostgreSQL and FFmpeg, controlling external storage,
identity, launch and waiting at their boundaries. Existing source-upload and deletion-admission direct launches now share the same
submission implementation. Native validation cases were retained while retiring
fixed-example assumptions for implemented business operations.

After merging integration `e0f3a77`, `make check` passed OpenAPI validation,
45 examples, Ruff/format and strict Pyright. The full relevant PostgreSQL and
real-media suite passed **199 tests** in 28.24s, with 85% overall measured coverage.
The 19 recovery cases and 5 deletion-admission cases also passed independently.
A repeat `ag` run changed none of the 27 checked ownership/artifact files.
Live cloud execution and physical cleanup remain unverified and are not claimed.

Local operator-auth follow-up: the boundary tracer first failed because explicit
gcloud selection was missing. The completed path passes **38 targeted checks**
covering external CLI success/empty/error/missing/timeout, timeout child reaping,
metadata-only defaults without fallback, run-flag rejection, actual recover CLI
with real PostgreSQL and controlled Cloud Run HTTP, existing recovery/media and
redacted worker-command outcomes. `make check` passes 46 examples, Ruff/format and
strict Pyright. No HTTP schema or generated output changed. These checks do not
claim live operator permissions or a deployed recovery execution.
