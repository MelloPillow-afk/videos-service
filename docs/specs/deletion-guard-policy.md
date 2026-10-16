# Approved deletion guard exception

Approved by the user on 2026-10-16. This addendum supersedes the earlier pending
writer-drain decision; it leaves the original interview notes intact.

Cleanup replaces all related media bytes with permanent zero-byte guard objects
before removing application rows. It covers every registered private upload or
source key, public image-copy key, cumulative worker output key, active resource
key, and additional object discovered under the video's recorded prefixes.
Previously absent registered keys receive guards too.

Only the privileged cleanup operation may overwrite objects unconditionally.
Ordinary uploads and workers always use conditional create-once PUTs. Cleanup
uses one unconditional overwrite per key, with no delete-then-create gap. A late
conditional PUT therefore either commits before the guard and is overwritten,
or fails against the guard at commit. Verify zero bytes and explicit deletion
marker metadata before deleting application records.

Retain the non-media markers indefinitely, including public delivery markers.
They are the approved exception to removing every related object. Do not expire
them, schedule their removal, or let ordinary writers remove them. Previously
cached public media may remain accessible until cache expiry; publication and
deletion still govern API discovery.

Temporary cleanup failures keep DELETING and retry with increasing delays.
Cleanup has a bounded execution runtime but no three-attempt media abandonment
rule. An exhausted/interrupted execution is visible and explicitly recoverable.
No cron, periodic reconciliation, scheduled orphan cleanup, extra application
table, or full frontend is added. The [cloud readiness record](../cloud-readiness.md)
contains independent live R2 conditional/guard proof; full browser/CDN/deployed
acceptance remains separate.
