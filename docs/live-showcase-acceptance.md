# Live showcase acceptance checkpoint — 2026-10-16

**MEL-16 remains in progress.** These are actual deployed-service, R2 and browser
observations. [Cloud readiness](cloud-readiness.md), [deployment identities and
image pins](cloud-deployment.md), and [native worker measurements](cloud-worker-resources.md)
record the completed prerequisites independently.

## Actual browser playback

The temporary localhost:8765 acceptance harness played the published 18-second
fixture through its public R2 HLS delivery URL using **hls.js 1.7.3**. It offered
360p and 720p; playback at 720p advanced from zero through 14 seconds and reached
the **18.07-second** end. Browser state reported readyState 4, zero dropped frames
and no media error. This establishes actual browser playback of the retained
published fixture, rather than playlist fetching alone.

[Sanitized playback observations](evidence/live-hls-player-result-2026-10-16.json)
accompany the unchanged browser screenshot:

![Actual live 720p HLS player at the end of playback](evidence/live-hls-player-2026-10-16.png)

## Application-issued direct browser uploads

The deployed API issued the MP4 and 1280×720 JPEG upload instructions. Actual
browser PUTs from localhost:8765 each returned **200** initially and **412** when
attempting different replacement bytes. Independent authenticated S3 GETs using
the verified runtime credential returned **200** and confirmed both original
lengths and SHA-256 digests after those replacement attempts:

| Object | Bytes | SHA-256 |
| --- | --- | --- |
| MP4 source | 2,238,866 | `299c36101fac4bbea7ad2e222c287657c7260280fd680845d3bd647ad304f251` |
| JPEG image | 15,028 | `21f2b6f66bd50be6cd0d676a5422c127663a1384d6175108c50565143735ba02` |

The [browser result](evidence/live-browser-put-result-2026-10-16.json) and
[independent private GET result](evidence/live-browser-private-get-2026-10-16.json)
contain no credentials, signed URLs or media payloads. The screenshot is retained
unchanged:

![Actual application-issued browser upload and conditional replacement results](evidence/live-browser-put-2026-10-16.png)

## Remaining live acceptance and fixture policy

Record application CORS, invalid-source rejection, actual signed-URL expiry,
full 300-second output decoding and guarded deletion while processing is in flight
before marking MEL-16 complete. The successful native manual recovery and sampled
resource observations are linked above; their platform task result does not
substitute for complete media/state acceptance.

Retain the approved happy-path 18-second PUBLISHED fixture so an interviewer can
play actual content. Other disposable acceptance fixtures—including browser
uploads, invalid sources, expiry, recovery and in-flight deletion cases—must
finish the explicit application cleanup flow and retain their permanent guards.
This checkpoint does not claim that cleanup has finished. Stop the temporary
localhost harness after acceptance; no full frontend or scheduled cleanup is
introduced.
