"""Run one video through a deployed service end to end, then delete it.

Creates a video, uploads a generated five-second MP4 through the signed URL, waits for
the processing job, checks the thumbnail loads, publishes the video, checks its HLS
playlist loads from the media origin, and deletes the video. Needs ffmpeg on PATH and a bearer token:

    TOKEN=$(uv run --locked python scripts/get_token.py --email you@example.com)
    TOKEN=$TOKEN uv run --locked python scripts/smoke.py https://videos-api-....run.app
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

JOB_TIMEOUT_SECONDS = 600
THUMBNAIL_TIMEOUT_SECONDS = 300


def step(message: str) -> None:
    print(f"- {message}", file=sys.stderr)


def check(response: httpx.Response, status: int) -> Any:
    if response.status_code != status:
        raise SystemExit(
            f"error: expected HTTP {status} from {response.request.method} "
            f"{response.request.url}, got {response.status_code}: {response.text[:500]}"
        )
    return response.json() if response.content else None


def make_clip(directory: Path) -> Path:
    clip = directory / "smoke.mp4"
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440", "-t", "5", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(clip),
        ],
        check=True,
    )  # fmt: skip
    return clip


def wait_for(description: str, timeout: float, poll: Any) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = poll()
        if result is not None:
            return result
        time.sleep(3)
    raise SystemExit(f"error: timed out after {timeout:.0f}s waiting for {description}")


def run(api: httpx.Client, clip: Path) -> None:
    video = check(api.post("/v1/admin/videos", json={"title": "Smoke test"}), 201)
    video_id = video["id"]
    step(f"created video {video_id}")
    try:
        size = clip.stat().st_size
        body = {"file_name": clip.name, "content_type": "video/mp4", "size_bytes": size}
        upload = check(api.post(f"/v1/admin/videos/{video_id}:upload-url", json=body), 200)
        signed = upload["upload"]
        check(
            httpx.put(
                signed["url"], content=clip.read_bytes(), headers=signed["headers"], timeout=60
            ),
            200,
        )
        step(f"uploaded {size} bytes to R2")

        body = {"upload_id": signed["upload_id"]}
        job = check(api.post(f"/v1/admin/videos/{video_id}:complete-upload", json=body), 202)
        step(f"queued job {job['id']}")

        def job_finished() -> Any:
            job_now = check(api.get(f"/v1/jobs/{job['id']}"), 200)
            return job_now if job_now["status"] in ("SUCCEEDED", "FAILED") else None

        job = wait_for("the processing job", JOB_TIMEOUT_SECONDS, job_finished)
        if job["status"] != "SUCCEEDED":
            raise SystemExit(f"error: job failed: {job['message']}")
        step("processing job succeeded")

        def thumbnail_ready() -> Any:
            thumbnail = check(api.get(f"/v1/admin/videos/{video_id}"), 200)["thumbnail"]
            if thumbnail["status"] == "FAILED":
                raise SystemExit("error: thumbnail generation failed")
            return thumbnail if thumbnail["status"] == "READY" else None

        thumbnail = wait_for("the thumbnail", THUMBNAIL_TIMEOUT_SECONDS, thumbnail_ready)
        check_media(thumbnail["url"], "image/")
        step("thumbnail loads from the media origin")

        # Viewers can play only published videos.
        body = {"publication_status": "PUBLISHED"}
        check(api.patch(f"/v1/admin/videos/{video_id}", json=body), 200)
        step("published video")

        playback = check(api.get(f"/v1/videos/{video_id}/playback"), 200)["playback"]
        playlist = check_media(playback["url"], "")
        if not playlist.text.startswith("#EXTM3U"):
            raise SystemExit(f"error: {playback['url']} is not an HLS playlist")
        step("HLS playlist loads from the media origin")
    finally:
        api.delete(f"/v1/admin/videos/{video_id}")
        step(f"deleted video {video_id}")


def check_media(url: str, content_type: str) -> httpx.Response:
    response = httpx.get(url, timeout=30, follow_redirects=True)
    check_status = response.status_code == 200 and response.headers.get(
        "content-type", ""
    ).startswith(content_type)
    if not check_status:
        raise SystemExit(f"error: GET {url} gave {response.status_code} {response.headers}")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one video through a deployed service.")
    parser.add_argument("base_url", help="the service origin, for example http://127.0.0.1:8000")
    arguments = parser.parse_args()
    token = os.environ.get("TOKEN")
    if not token:
        raise SystemExit("error: set TOKEN to a bearer token (see scripts/get_token.py)")
    headers = {"Authorization": f"Bearer {token}"}
    with (
        TemporaryDirectory() as work,
        httpx.Client(base_url=arguments.base_url, headers=headers, timeout=30) as api,
    ):
        check(api.get("/ping"), 200)
        step("ping ok")
        run(api, make_clip(Path(work)))
    print("smoke test passed", file=sys.stderr)


if __name__ == "__main__":
    main()
