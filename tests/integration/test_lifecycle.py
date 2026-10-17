"""A video goes from creation to published playback through the API and the media worker,
with no rows arranged by hand, so each step reads exactly what the step before it wrote."""

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from src.workers.media import run
from tests.api_client import running
from tests.fakes import FakeLauncher, FakeStorage
from tests.media_files import make_image
from tests.media_urls import MEDIA_BASE_URL, THUMBNAIL_SIZES

pytestmark = pytest.mark.integration


def served(storage: FakeStorage, url: str) -> bytes:
    """The bytes a viewer downloads from a media URL."""
    return storage.media[url.removeprefix(f"{MEDIA_BASE_URL}/")]


def assert_thumbnail_is_served(storage: FakeStorage, thumbnail: dict[str, Any]) -> None:
    assert {
        name: (size["width"], size["height"]) for name, size in thumbnail["sizes"].items()
    } == THUMBNAIL_SIZES
    assert thumbnail["url"] == thumbnail["sizes"]["xl"]["url"]
    for size in thumbnail["sizes"].values():
        assert served(storage, size["url"]).startswith(b"\xff\xd8")  # JPEG


async def start_upload(
    client: AsyncClient, path: str, content_type: str, file: bytes
) -> dict[str, Any]:
    response = await client.post(
        path,
        json={"file_name": "upload", "content_type": content_type, "size_bytes": len(file)},
    )
    assert response.status_code == 200, response.text
    upload: dict[str, Any] = response.json()["upload"]
    return upload


async def run_launched(launcher: FakeLauncher, app: FastAPI) -> None:
    """Run every launched worker to completion, as Cloud Run would."""
    jobs, launcher.launched = launcher.launched, []
    for job_id in jobs:
        await run(job_id, app.state.settings)


async def test_uploaded_video_is_published_and_played(
    api_app: FastAPI,
    api_bearer_token: str,
    storage: FakeStorage,
    launcher: FakeLauncher,
    landscape_mp4: bytes,
    tmp_path: Path,
) -> None:
    # The worker opens its own database and storage, as its own process does, so the
    # API runs only between worker runs.
    async with running(api_app, api_bearer_token) as client:
        video = (await client.post("/v1/admin/videos", json={"title": "Lesson"})).json()
        path = f"/v1/admin/videos/{video['id']}"
        upload = await start_upload(client, f"{path}:upload-url", "video/mp4", landscape_mp4)
        storage.put(upload["url"], landscape_mp4)
        response = await client.post(
            f"{path}:complete-upload", json={"upload_id": upload["upload_id"]}
        )
        assert response.status_code == 202
        job_id = response.json()["id"]

    await run_launched(launcher, api_app)

    async with running(api_app, api_bearer_token) as client:
        assert (await client.get(f"/v1/jobs/{job_id}")).json()["status"] == "SUCCEEDED"
        response = await client.patch(path, json={"publication_status": "PUBLISHED"})
        assert response.status_code == 200
        video = response.json()
        assert (video["status"], video["size_bytes"]) == ("READY", len(landscape_mp4))
        assert video["duration_seconds"] == pytest.approx(2, abs=0.1)
        assert (video["thumbnail"]["status"], video["thumbnail"]["source"]) == (
            "READY",
            "GENERATED",
        )
        assert_thumbnail_is_served(storage, video["thumbnail"])

        del client.headers["Authorization"]
        (listed,) = (await client.get("/v1/videos")).json()["data"]
        assert (listed["id"], listed["thumbnail"]) == (video["id"], video["thumbnail"])
        playback = (await client.get(f"/v1/videos/{video['id']}/playback")).json()["playback"]
        assert playback["type"] == "hls"
        master = served(storage, playback["url"]).decode()
        renditions = [line for line in master.splitlines() if line.endswith(".m3u8")]
        assert len(renditions) == 2  # 360p and 720p for a 720p source.
        base = playback["url"].rsplit("/", 1)[0]
        for rendition in renditions:
            assert served(storage, f"{base}/{rendition}").startswith(b"#EXTM3U")

    image = make_image(tmp_path / "cover.png", "1920x1080")
    async with running(api_app, api_bearer_token) as client:
        upload = await start_upload(client, f"{path}/thumbnails:upload-url", "image/png", image)
        storage.put(upload["url"], image)
        response = await client.post(
            f"{path}/thumbnails:complete-upload", json={"upload_id": upload["upload_id"]}
        )
        assert response.status_code == 202

    await run_launched(launcher, api_app)

    async with running(api_app, api_bearer_token) as client:
        (listed,) = (await client.get("/v1/videos")).json()["data"]
        assert (listed["thumbnail"]["status"], listed["thumbnail"]["source"]) == (
            "READY",
            "CUSTOM",
        )
        assert listed["thumbnail"]["url"] != video["thumbnail"]["url"]
        assert_thumbnail_is_served(storage, listed["thumbnail"])
