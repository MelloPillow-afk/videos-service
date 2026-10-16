# Local container preparation (MEL-16)

Verified 2026-10-16. **MEL-16 remains incomplete:** this is local Linux image and
operator-CLI evidence, plus the separately recorded actual R2 browser proof.
Subsequent image publication and explicit owner-run production migrations are
recorded in [deployment preparation](cloud-deployment.md); service/job deployment
is now separately recorded; local evidence alone does not certify deployed behavior.
[Cloud readiness](cloud-readiness.md) tracks the remaining target gates.

## Build and entry points

Build from the repository root. Docker/Buildx and Linux AMD64 execution are required:

```sh
docker buildx build --platform linux/amd64 --load -t videos-showcase:local .
docker run --rm --init -p 127.0.0.1:8080:8080 -e PORT=8080 \
  -e DB_POOL_MIN_SIZE=0 videos-showcase:local
```

The default entry point executes Uvicorn on `0.0.0.0:$PORT` (default 8080), without
reload. `/ping` is database-independent. Runtime UID/GID is `10001:10001`; temporary
media files use `/tmp`. The image contains source, locked runtime dependencies,
FFmpeg/FFprobe, Yoyo and migrations. Its allowlisted context excludes environment
files, credentials, Git metadata, host virtual environments, tests, scratch files,
and bytecode. Development packages are absent from the runtime image.

Configure the Cloud Run worker **command array** as
`["/app/.venv/bin/python", "-m", "src.worker"]`. The launcher overrides only its
arguments with `["run", "--job-id", "UUID"]`; putting `-m src.worker` in the job's
replaceable arguments would lose the module invocation. Workers serve no HTTP.
For a local configured invocation:

```sh
docker run --rm --env-file /absolute/private/runtime.env \
  videos-showcase:local python -m src.worker run --job-id UUID
```

Migrations remain a deliberate separate operation, using an owner connection in a
private environment file. The working directory is `/app`, including `yoyo.ini`:

```sh
docker run --rm --env-file /absolute/private/migration.env \
  videos-showcase:local python -m src.repositories.migrate apply
```

The server and worker never run migrations automatically. Supply secrets only at
runtime, outside the build context; the setup/admin R2 credential is not a runtime
credential. Do not deploy until the scoped credentials and target checks are ready.

## Actual image results

The final verified local tag `videos-showcase:showcase-ccb6f66` identifies image
`sha256:f5ccffb6702f6998bb5ef931bcf0d6dd82a283ea120e1908dcf0d0c44a8b1f82`.
It is Linux/AMD64, 273,957,832 reported image bytes, Python 3.13.16, and Debian
FFmpeg/FFprobe `7.1.5-0+deb13u1`. Python and uv base manifests are pinned in the
Dockerfile; Python dependencies come from `uv.lock`. Apt packages come from Debian's
configured repositories, so future rebuilds must record/reverify their versions;
this is not a claim of bit-identical future apt resolution.

- Runtime imports and media executables work under actual AMD64 emulation.
  Pytest and excluded files are absent; migration assets are present.
- Default API process honored alternate `PORT=8766`; `/ping` returned 200 with
  `{"status":"ok"}` while its pool minimum was zero.
- SIGTERM reached Uvicorn and completed application shutdown. With Docker's native
  `--init` wrapper, the emulated process exited 143 in 0.30 seconds. Without that
  wrapper, QEMU as PID 1 remained until forced kill despite the shutdown-complete
  log. This is an observed local emulation limitation; native Cloud Run signal
  behavior and its ten-second termination window remain live checks.
- The actual runtime image's explicit migration command exited 0 against a fresh,
  randomly named **local** PostgreSQL database. It created exactly `videos`,
  `upload_attempts`, and `jobs` plus Yoyo bookkeeping. That database was removed.
- Combined reviewed image `sha256:4e520f133e95d5af997fc85661ec5fe26ff6dcd501590b8992025bf60a9f786a` passed 34 representative checks in 78.18 seconds: real HTTP/PostgreSQL, migrations, CLI, HLS/audio, SAR/rotation, fitted thumbnails, custom images and both complete showcase journeys. The subsequent checkpoint image `sha256:36a70c7ed98f4c983f9a29725cb50ed329e269a177911f2bbe759f11c0793064` changed only the safe CLI recovery diagnostic; all nine affected CLI/redaction checks passed in 8.88 seconds after rebuilding.

The initial image run exposed an FFmpeg 7 compatibility defect: unbounded `apad`
with `-shortest` muxed excess buffered AAC although HLS video durations were right.
The selected video stream duration now bounds audio padding/trimming. Overall
container/audio duration still governs source admission; silent sources remain
video-only. After rebuilding, all seven affected image cases passed, including
long audio, padded short audio with decoded silence, silent video, AAC packet/PCM
length, long-audio admission rejection, and migration apply/reapply/rollback.
No assertion was weakened for the Linux version.

The final image was rebuilt from reviewed integration `ccb6f66`, including the
explicit local `recover --gcloud-auth` provider boundary. All **19 affected
CLI/operator checks passed in 16.23s** using that actual image and real disposable
PostgreSQL. These cover successful, failed and no-op CLI outcomes, command-array
behavior, explicit token acquisition, redaction, timeout kill/reaping, and the
runtime metadata default with no gcloud fallback. The first emulated run exposed
a test startup assumption: a 0.25-second timeout killed the fake Python helper
before it recorded its PID. Giving that helper two seconds before timeout while
it deliberately sleeps ten preserves the termination assertion; the production
ten-second authentication timeout is unchanged. All eight operator checks also
passed natively in 2.77s. Only test timing changed after the image build; tests
are excluded from its context.

Final runtime readback reconfirmed UID/GID `10001:10001`, the API entrypoint and
`CMD ["api"]`, migration assets, absent pytest/gcloud, and absent environment,
Git, tests and user-reference files. No unaffected media suite was repeated.

## Reproduce representative image acceptance

Use an existing isolated local PostgreSQL container. The example below shares its
network namespace; this is solely a local verification setup. It passes no cloud
credentials. Install locked test tools only in the disposable verification
container, leaving the production image unchanged. Send only test files through
stdin because Colima may not mount temporary macOS worktrees. macOS metadata
sidecars must be excluded so Yoyo does not mistake AppleDouble files for migrations.

```sh
COPYFILE_DISABLE=1 tar --no-xattrs --exclude=__pycache__ --exclude='._*' -cf - tests |
  docker run --rm -i --platform linux/amd64 --user 0 \
    --network container:videos-showcase-postgres-test \
    -e TEST_DATABASE_URL=postgresql://videos:videos@127.0.0.1:5432/videos_test \
    videos-showcase:local sh -c '
      tar -xf - &&
      uv sync --locked --all-groups --no-install-project --no-cache &&
      python -m pytest -q tests/integration/test_worker_cli.py \
        tests/integration/test_database.py tests/integration/test_migrations.py \
        tests/integration/test_showcase.py \
        tests/integration/test_processing.py::test_playback_duration_follows_video_and_existing_audio_is_trimmed_or_padded \
        tests/integration/test_generated_thumbnails.py::test_fitted_canvas_preserves_display_aspect_and_black_padding
    '
```

The final verification also covers source-to-HLS publication behavior, stereo AAC,
SAR/rotation, overall long-audio admission, custom JPEG/PNG processing and actual
CLI configuration-error redaction. PostgreSQL remains real; R2 and job launch are
controlled only at their provider boundaries. Media processing uses the image's
FFmpeg binaries. CPU/memory measurements under QEMU on a 2 CPU/2 GiB Colima VM do
not establish native Cloud Run workload budgets.

## Operator-visible outcomes

The worker prints one sanitized JSON outcome with job ID and command:

| Outcome | Exit | Meaning |
| --- | --- | --- |
| `succeeded` | 0 | This invocation completed claimed work, or confirmed the requested manual relaunch. |
| `no_op` | 0 | No eligible claim, duplicate delivery, or execution fenced by newer/deleting state. No budget is reset. |
| `failed` | 1 | This invocation persisted invalid/exhausted processing or cleanup failure, recovery was not confirmed, or executable setup failed. Inspect persisted state and provider execution. |

Malformed CLI arguments retain argparse's exit 2. Raw provider/configuration
exceptions and credentials are not emitted. Handled media failures consume at most
three total attempts with the persisted history; cleanup retains its independent
bounded runtime and manual recovery. Platform retries must remain zero. A terminal
Cloud Run result alone never substitutes for persisted state and media evidence.

Remaining live work includes deployed HTTP Neon token/admin demotion, independent Run job
executions, native resource/signal limits, and public HLS player playback/deletion. Provider token/demotion and the owner-selected
processed `r2.dev` origin’s public/private sentinel and Range checks have passed;
see the readiness record for their exact scope and development limits.

References: [uv image guidance](https://docs.astral.sh/uv/guides/integration/docker/),
[Cloud Run runtime contract](https://docs.cloud.google.com/run/docs/container-contract),
[FFmpeg audio padding/trimming](https://ffmpeg.org/ffmpeg-filters.html#apad).
