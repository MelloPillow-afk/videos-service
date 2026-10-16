# Integration review fixes

Review range: `fe07f99...03f0062`; fixes start from `03f0062`.
The Standards and Spec reviews were conducted separately against the approved
showcase specification and repository guidance. This file records their findings
without treating known incomplete tickets as completed work.

## Standards

- **P2, recovery policy placement — fixed.** The repository loads a typed recovery
  snapshot while retaining the parent-video-before-job locks. Eligibility,
  allowable operator states, termination confirmation, the three-execution media
  budget, and domain rejection decisions now belong to `JobSubmission.recover`
  in the same transaction. Repository functions map rows and perform guarded SQL
  transitions. Existing recovery, interrupted-final-attempt, supersession, and
  uncapped deletion-relaunch acceptance remains unchanged.
- **P3, duplicated upload rejection mapping — fixed.** A small handler helper
  maps source/image admission failures to the existing HTTP status and detail
  body. No generic exception framework or new error envelope was introduced.

## Spec

- **P2, UTC HTTP timestamps — fixed.** Video creation/update/publication and
  source/image upload expiry share an explicit UTC formatter. A real HTTP test
  sets the PostgreSQL pool session to America/Chicago while using a UTC clock;
  it reproduced `-05:00` wire values before the fix and now verifies canonical
  UTC values in creation, detail, publication, list, and both upload responses.
- **P2, audio/video ending and playable duration — fixed.** Video governs the
  produced timeline. Existing audio is trimmed at video end or padded with
  silence; video-only input remains video-only. Admission still checks the
  maximum actual container/audio/video duration. The worker stores verified HLS
  playlist duration rather than source-container maximum. Real unequal-duration
  fixtures reproduce the former 5-second resource/1-second playlist mismatch and
  short-audio ending; regressions verify decoded PCM sample count, packet end
  times, silence in the padded tail, and full output decoding. Existing genuine
  300/300.1-second, rotation, aspect, and no-upscaling cases remain in the suite.

## Canonical removal example

DELETE custom-thumbnail now references `thumbnails.ThumbnailRemoval`, whose
GENERATED example describes the fallback returned by that operation. The two
HTTP properties are unchanged. The reusable `Thumbnail` CUSTOM example still
describes upload completion. A separate schema is required because the generator
rejects conflicting schema/response examples. The handwritten Arrange hook seeds
the canonical generated image and no longer overrides the expected response.
The schema supplies the single canonical removal example without a duplicated
inline operation example. Contract checks and regeneration remain authoritative.

## Outstanding gates

- **MEL-7:** [current cloud readiness](cloud-readiness.md) records verified
  Neon JWT/current-role demotion, runtime grants, R2 browser/privacy/public-origin
  and scoped Google IAM evidence. Matching object-scoped R2 runtime credentials
  and deployed identity/direct-launch verification remain open.
- **MEL-14:** the owner subsequently approved permanent guards. Local cleanup,
  late-writer fencing, runtime exhaustion, manual recovery and row removal are
  covered by [deletion acceptance](deletion-acceptance.md). Configured live
  provider evidence remains separately tracked under MEL-7/MEL-16.
- **MEL-15:** the [local showcase](showcase.md) now exercises the complete journey;
  its controlled provider boundaries do not constitute deployed cloud evidence.
- **MEL-16:** the [deployment record](cloud-deployment.md) records the private image
  publication checkpoint and explicit production migrations. Deployed API/job,
  player, recovery and guarded-deletion end-to-end evidence remains pending.

No cron, periodic reconciliation, scheduled orphan cleanup, extra application
table, full frontend, billing expansion, or cloud completion claim was added.

## Verification

Contract validation passes **46 examples**. `ag` regenerated 13 operations and
23 generated HTTP cases; the canonical removal expectation is exercised directly.
`make check` passes Ruff, formatting, and strict Pyright. The full isolated local
suite passes **204 tests** through real PostgreSQL and media processing, including
the new UTC/session and unequal-audio/video regressions, existing recovery policy
cases, and genuine 300-second boundary/rotation/rendition checks. Measured
coverage is 85%; the separately exercised inventory CLI subprocess is outside
that coverage collection. No live cloud verification was performed.

Final integration-checkout verification on 2026-10-16 also passed `make check`
(46 examples, Ruff/format, strict Pyright with zero errors) and all **204 tests**
against local PostgreSQL and real FFmpeg/FFprobe. A second `ag` run was
byte-identical across all 26 owned files and the ownership record. Generated
source-location metadata now points at the integration checkout. Both reviewers
confirmed their findings resolved; no new actionable finding remained in the
follow-up review. The outstanding gates above remain open.

Approved deletion follow-up: after merging cloud readiness and the verified Neon
pool compatibility fix, MEL-14 quality checks passed and all **217 unique local
tests** were verified (215 in the full run plus the two migration subprocess
cases rerun successfully through uv's PATH). See [deletion acceptance](deletion-acceptance.md)
for exact evidence and the retained-guard exception. This does not supersede the
remaining showcase or live deployment gates.

## Final Standards follow-up

The `fe07f99...29f2f1f` Standards review identified two remaining P2 responsibility
breaches. Both are fixed without HTTP or lifecycle changes. `src.worker` keeps
compatible `run_job`/`process_video` wrappers and CLI/resource composition, while
`services/media_jobs.py` owns claim orchestration, failure classification, media
processing, manifest publication and retry decisions. The media service chooses
retry versus final failure and source invalidation; repository operations persist
that selected transition. Parent-before-job locks, current claim tokens and
defensive SQL execution caps remain in place.

The coordinated worker CLI distinguishes success (`True`), persisted failure
(`False`) and benign unclaimed/fenced work (`None`); the move preserves those
outcomes and CLI exit behavior. Existing real HTTP/PostgreSQL/media acceptance
provides regression evidence; no tests of private calls or mechanical module
placement were introduced. Targeted recovery, worker CLI and local-showcase
checks pass **30 tests**.

Final combined checkpoint `5c1cdb5` includes the local showcase, Linux runtime
packaging, explicit bounded audio padding/trimming and sanitized CLI outcomes.
`make check` passes all **46 examples**, Ruff/format checks and strict Pyright
with zero errors. The complete native suite ran once through `uv run --locked
pytest --cov --cov-report=term-missing -q --tb=short`: **228 passed in 35.55s**,
including PostgreSQL migration subprocesses, real FFmpeg/Pillow processing,
worker command outcomes, recovery, deletion races and both showcase journeys.
Measured native coverage is **88%**. The image checks and remaining live gates
are independently recorded in [container acceptance](container-local-acceptance.md)
and [cloud readiness](cloud-readiness.md); native success does not close MEL-7
or MEL-16. No additional HTTP change or generation was required for these
responsibility fixes.

After merging the reviewed implementation and current cloud evidence into the
integration checkout, `make lint-api` passed and `ag` regenerated **13 operations
and 23 HTTP cases**. A repeated run was byte-identical across all **26 owned
files and the ownership record**. Only generated test source-location metadata
changed during normalization. Final `make check` and both `make showcase`
journeys pass in the integration checkout. The final Standards and Spec delta
reviews have **zero open actionable findings**; the two Standards findings above
are resolved. Real Auth/provider demotion and browser R2 privacy/upload checks
are recorded separately from the still-required deployed application sequence.


## Operator recovery and final image checkpoint

The `32a08bf...76ef342` operator delta passed separate Standards and Spec reviews
with **zero actionable findings**. Local `recover --gcloud-auth` explicitly uses
the authenticated host CLI; ordinary runtime launch still uses metadata identity
without fallback. Token subprocess output stays private, and failed/invalid
credentials and timeout termination produce sanitized errors. Existing recovery
transaction locks and eligibility rules are unchanged.

Final integration `ccb6f66` passed `make check` (**46 examples**, Ruff/format,
strict Pyright zero errors) and the complete native suite: **238 passed in
36.77s**, **88% coverage**, including both showcase journeys. All 26 generated
files plus their ownership record remain byte-identical to the deterministic
`9b682d3` checkpoint. All seven original user-owned files remain unchanged.

The final Linux/AMD64 runtime image built from that reviewed source separately
passed **19 affected CLI/operator checks in 16.23s** through real PostgreSQL.
An emulation-sensitive test helper timeout was raised from 0.25 to two seconds
while retaining its ten-second delay and child-reaping assertion; production
behavior is unchanged. The eight operator checks passed natively in 2.77s.
These local and image checkpoints do not close the remaining deployed-cloud
gates in the [deployment record](cloud-deployment.md).
