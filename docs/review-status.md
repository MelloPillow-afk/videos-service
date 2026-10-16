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

- **MEL-7:** target accounts, credentials, provider token/schema configuration,
  browser CORS/create-once protection, runtime identities, and readiness evidence.
- **MEL-14:** physical cleanup and eventual row removal await the owner decision
  and evidence for writer drain or permanent guards. Admission/inventory remains
  explicitly partial; no cleanup completion is claimed.
- **MEL-15:** the complete reproducible showcase depends on completed deletion.
- **MEL-16:** real Neon/R2/Cloud Run/CDN end-to-end evidence remains unexecuted.

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
