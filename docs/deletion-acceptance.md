# Deletion admission and inventory (MEL-14, partial)

Status: **partial; cleanup completion is not implemented**. The owner decision
between permanent zero-byte guards and verified writer drain is still pending.
Neither policy is assumed by this change. No media or application rows are
removed and no cleanup job is marked SUCCEEDED.

DELETE through the real app now requires the current administrator role. In one
transaction it locks the video, enters DELETING, records one current DELETION
job, and records a safe CLEANUP_POLICY_REQUIRED diagnostic. Direct submission
happens after commit. Concurrent/repeated deletion returns 202 using the retained
work; it does not submit another execution. Missing records return 404. A launch
failure remains LAUNCH_FAILED with an explicit unknown-outcome recovery message;
202 acknowledges persisted acceptance rather than launch or cleanup success.

DELETING immediately removes anonymous detail/list/playback discovery and blocks
metadata edits, new source/image authorizations, upload acceptance, thumbnail
completion/removal, and worker result publication. Administrators can still
inspect the deleting video. Database fencing does not stop a provider write that
was already in flight.

The read-only operator command uses configured DATABASE_URL and DB_SCHEMA:

```sh
uv run --locked python -m src.cleanup inspect --job-id UUID
```

It enumerates the accepted source, every current/superseded/removed/pending
upload object's private key, registered public custom-image copies, current
playback/generated/custom keys, all historical job output manifests/prefixes,
upload URL expiry times, and execution states/references. It retains the entire
cumulative output manifest across attempts. Add `--list-storage` to enrich the
inventory using the existing provider's private/public prefix listings; this
requires actual storage configuration. Neither URL expiry nor an empty listing
is treated as proof that old writes have drained. Output always explicitly
reports `physical_cleanup_complete: false`.

No signed URLs, authorization headers, or provider credentials belong in this
inventory. Treat object keys and execution references as operator diagnostics,
not public API resource fields. Inspect cloud executions before any manual
relaunch; changing a database job state does not terminate an old execution.
The media recovery command is maintained with MEL-10. Physical deletion worker
dispatch, bounded-runtime retry/finalization behavior, and eventual row removal
remain pending the owner decision and required provider evidence. No scheduler
or periodic maintenance service is introduced.

Local HTTP/PostgreSQL acceptance covers one durable cleanup job, repeated 202,
immediate visibility fencing, role checks, launch failure history, blocked
mutations, source verification racing deletion, and the read-only inventory CLI
with historical manifests and attempts. Existing real-media tests cover worker
publication fences. These checks do not establish eventual physical cleanup or
production CDN revocation. MEL-14 must remain open.

Executed locally: `make check` (45 contract examples, Ruff, strict Pyright),
`ag` regeneration (13 operations / 23 generated HTTP cases), and the complete
PostgreSQL/real-media pytest suite: **163 passed**, including five deletion
admission/inventory cases. The inspection CLI is exercised as a separate process;
the coverage report does not collect that subprocess. No storage deletion or
eventual-cleanup scenario has been run.
