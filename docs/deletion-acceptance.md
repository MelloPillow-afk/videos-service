# Guarded deletion (MEL-14)

The user approved permanent zero-byte deletion guards on 2026-10-16. See the
[approved policy](specs/deletion-guard-policy.md); it supersedes the earlier
pending writer-drain decision. Local deletion now completes through the real
application and PostgreSQL. Live provider acceptance is tracked separately.

DELETE requires the current administrator role. One transaction locks the video,
enters DELETING, and records one current DELETION job; direct submission follows
commit. Repeated/concurrent deletion returns 202 without another launch. Missing
or fully removed records return 404. Launch failures retain LAUNCH_FAILED and
safe unknown-outcome diagnostics. A 202 acknowledges persisted admission.

DELETING immediately hides anonymous detail/list/playback discovery and blocks
metadata edits, source/image authorization and acceptance, thumbnail removal,
new worker manifests, and publication. The explicit cleanup worker independently
claims the current DELETION job with a token; duplicate and stale executions
cannot finalize application records.

Cleanup inventories accepted/superseded/pending/removed private upload objects,
accepted originals, registered custom-image copies, current playback and thumbnail
keys, cumulative output keys from every historical worker attempt, and additional
objects under recorded video/job prefixes. Every possible future media key is
registered before its conditional PUT. Deletion fences further registrations.
A single unconditional privileged PUT replaces each existing or absent key with
zero bytes, guard content type and explicit marker metadata. HEAD must verify all
three before deleting the video and its cascaded jobs/upload rows. Listings find
legacy objects; empty listings and URL expiry never substitute for guarding the
complete finite manifest. Ordinary application writers have no delete primitive.

Guards remain indefinitely. Cleanup never deletes then recreates a key, never
expires guards, and does not wait for signed URLs or known workers to drain.
Late conditional PUTs either commit before the guard and are overwritten, or fail
against it. Already cached public content can remain until cache expiry; this is
not immediate CDN revocation.

Provider/verification failures keep DELETING. Cleanup retries after 1, 4, 16 and
then 30 seconds per attempt; delays and the default 900-second invocation runtime
are configurable. There is no three-execution media cap for cleanup. Runtime
exhaustion records FAILED/CLEANUP_RUNTIME_EXHAUSTED; no rows are removed. Inspect
cloud execution termination before explicit recovery:

```sh
uv run --locked python -m src.cleanup inspect --job-id UUID --list-storage
uv run --locked python -m src.worker recover --job-id UUID
# A stranded RUNNING claim additionally requires confirmed prior termination:
uv run --locked python -m src.worker recover --job-id UUID --previous-execution-terminated
```

The inspection command exposes keys/history, not secrets or signed URLs. It is a
read-only snapshot and always reports `physical_cleanup_complete: false`; after
successful cleanup the application rows no longer exist. Cloud Run task timeout
must exceed the cleanup runtime and database finalization allowance. A hard kill
can leave RUNNING and requires explicit terminated-execution confirmation.
No scheduler, reconciliation process, fourth table, or orphan cleanup is added.

Acceptance covers repeated 202, immediate visibility and role fences, launch
failure, read-only inspection, all registered/listed keys including absent ones,
simultaneous claims, guard metadata verification, five temporary failures followed
by success with increasing delays, runtime exhaustion and relaunch beyond the
media budget, old-token rejection, and eventual 404/zero application rows. Real
FFmpeg VIDEO and THUMBNAIL workers and decoded custom-image copies are paused at
the provider write boundary; cleanup guards their persisted manifests before the
late conditional PUTs resume. The signed source upload race is also covered.
R2 SDK request tests require one unconditional PUT with no delete gap and verify
metadata mapping. Local checks do not establish complete deployed cloud behavior;
R2/CDN/browser/IAM evidence belongs to MEL-7/MEL-16.
