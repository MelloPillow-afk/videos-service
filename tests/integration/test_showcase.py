"""Run the real HTTP/PostgreSQL/media journey with controlled external providers."""

import asyncio
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient, MockTransport
from httpx import Request as DeliveryRequest
from httpx import Response as DeliveryResponse
from PIL import Image
from psycopg import AsyncConnection, sql
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from src.config import Settings
from src.providers.storage import StorageArea, StorageConflictError, TemporaryStorageError
from src.repositories.database import Database
from src.repositories.jobs import job_kind
from src.services.job_recovery import JobSubmission
from src.worker import run_job
from tests.integration.test_processing import make_source
from tests.job_provider import RecordingLauncher
from tests.providers import SUBJECT, LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


class ShowcaseStorage(MemoryStorage):
    """Existing conditional storage boundary, with an explicit delivery outage switch."""

    def __init__(self) -> None:
        super().__init__()
        self.unavailable_video_writes = 0

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        if area == "public" and key.endswith((".ts", ".m3u8")) and self.unavailable_video_writes:
            self.unavailable_video_writes -= 1
            raise TemporaryStorageError("Controlled delivery outage")
        await super().write(area, key, data, content_type, create_only=create_only)


class ShowcaseLauncher(RecordingLauncher):
    """Cloud-job boundary that starts the real worker as a separate asyncio task."""

    def __init__(self) -> None:
        super().__init__()
        self.app: FastAPI | None = None
        self.running: dict[str, list[asyncio.Task[bool | None]]] = {}
        self.gates: dict[str, asyncio.Event] = {}
        self.delays: list[float] = []

    def hold(self, kind: str) -> None:
        self.gates[kind] = asyncio.Event()

    def release(self, kind: str) -> None:
        self.gates[kind].set()

    async def launch(self, job_id: UUID) -> str:
        reference = await super().launch(job_id)
        assert self.app is not None
        database: Database = self.app.state.database
        settings: Settings = self.app.state.settings
        storage: ShowcaseStorage = self.app.state.storage
        async with database.connection() as connection:
            kind = await job_kind(connection, job_id)
        assert kind is not None

        async def advance_time(delay: float) -> None:
            self.delays.append(delay)
            await asyncio.sleep(0)

        async def execute() -> bool | None:
            if gate := self.gates.get(kind):
                await gate.wait()
            return await run_job(job_id, database, storage, settings, sleep=advance_time)

        self.running.setdefault(kind, []).append(asyncio.create_task(execute()))
        return reference

    async def finished(self, kind: str) -> list[bool | None]:
        return list(await asyncio.wait_for(asyncio.gather(*self.running[kind]), timeout=30))

    async def close(self) -> None:
        for gate in self.gates.values():
            gate.set()
        tasks = [task for tasks in self.running.values() for task in tasks]
        if tasks:
            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=30)


@pytest.fixture
def storage() -> ShowcaseStorage:
    return ShowcaseStorage()


@pytest.fixture
def launcher() -> ShowcaseLauncher:
    return ShowcaseLauncher()


async def upload_source(
    client: AsyncClient, storage: ShowcaseStorage, path: str, source: bytes
) -> dict[str, str]:
    issued = await client.post(
        path + ":upload-url",
        json={"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": len(source)},
    )
    assert issued.status_code == 200
    upload = issued.json()["upload"]
    await storage.browser_put(upload["url"], source, upload["headers"])
    accepted = await client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    assert accepted.status_code == 202
    return {"job_id": accepted.json()["processing_job_id"], "upload_id": upload["upload_id"]}


async def playback_copy(storage: ShowcaseStorage, url: str, directory: Path) -> Path:
    """Fetch every real HLS asset through a controlled HTTP delivery boundary."""
    directory.mkdir()

    async def deliver(request: DeliveryRequest) -> DeliveryResponse:
        item = storage.objects.get(("public", unquote(urlsplit(str(request.url)).path.lstrip("/"))))
        return (
            DeliveryResponse(200, content=item[0], headers={"Content-Type": item[1]})
            if item
            else DeliveryResponse(404)
        )

    # MockTransport controls the external CDN only; all bytes came from real FFmpeg.
    async with AsyncClient(transport=MockTransport(deliver)) as delivery:
        pending = [url]
        seen: set[str] = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            response = await delivery.get(current)
            assert response.status_code == 200
            seen.add(current)
            (directory / urlsplit(current).path.rsplit("/", 1)[1]).write_bytes(response.content)
            if current.endswith(".m3u8"):
                pending += [
                    urljoin(current, line)
                    for line in response.text.splitlines()
                    if line and not line.startswith("#")
                ]
    master = directory / "master.m3u8"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(master), "-f", "null", "-"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return master


async def test_showcase_confirmation_executes_full_library_journey(
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    storage: ShowcaseStorage,
    launcher: ShowcaseLauncher,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    launcher.app = api_app
    launcher.hold("THUMBNAIL")
    launcher.hold("DELETION")
    source = make_source(tmp_path / "source.mp4", size="1280x720")
    observed_handlers: set[str] = set()

    @api_app.middleware("http")
    async def observe_handler(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        endpoint = request.scope["endpoint"]
        observed_handlers.add(endpoint.__module__ + "." + endpoint.__name__)
        return response

    token = signing_keys.token()
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + token},
        ) as admin,
        AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as viewer,
    ):
        try:
            print("\nLOCAL SHOWCASE | real HTTP app + PostgreSQL + FFmpeg/FFprobe")
            print(
                "CONTROLLED | identity keys/provider roles, R2 direct PUT/storage, job launch, CDN, retry clock"
            )
            assert (await viewer.get("/ping")).json() == {"status": "ok"}
            created = await admin.post("/v1/videos", json={"title": "Interview showcase"})
            assert created.status_code == 201 and created.json()["status"] == "CREATED"
            path = created.headers["Location"]
            assert (await viewer.get(path)).status_code == 404
            assert (
                await admin.patch(path, json={"publication_status": "PUBLISHED"})
            ).status_code == 409
            await upload_source(admin, storage, path, source)
            assert set(launcher.running) == {"VIDEO", "THUMBNAIL"}
            assert len(launcher.submissions) == 2
            assert not launcher.running["THUMBNAIL"][0].done()
            assert await launcher.finished("VIDEO") == [True]
            ready = (await admin.get(path)).json()
            assert ready["status"] == "READY" and ready["publication_status"] == "DRAFT"
            assert ready["thumbnail"] == {"status": "PENDING", "source": "NONE", "url": None}
            assert (await admin.get(path + "/playback")).status_code == 200
            assert (await viewer.get(path + "/playback")).status_code == 404
            print(
                "PASS 01 | create -> direct conditional upload -> confirm 202 launches VIDEO and THUMBNAIL"
            )
            print(
                "PASS 02 | VIDEO reaches READY/DRAFT while independent THUMBNAIL remains pending; admin preview only"
            )

            image = BytesIO()
            Image.new("RGB", (1280, 720), "blue").save(image, format="JPEG")
            issued = await admin.post(
                path + "/thumbnails:upload-url",
                json={
                    "file_name": "cover.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": len(image.getvalue()),
                },
            )
            assert issued.status_code == 200
            upload = issued.json()["upload"]
            await storage.browser_put(upload["url"], image.getvalue(), upload["headers"])
            custom = await admin.post(
                path + "/thumbnails:complete-upload", json={"upload_id": upload["upload_id"]}
            )
            assert custom.status_code == 200 and custom.json()["thumbnail"]["source"] == "CUSTOM"
            custom_thumbnail = custom.json()["thumbnail"]
            launcher.release("THUMBNAIL")
            assert await launcher.finished("THUMBNAIL") == [True]
            assert (await admin.get(path)).json()["thumbnail"] == custom_thumbnail
            removed = await admin.delete(path + "/thumbnails")
            assert (
                removed.status_code == 200 and removed.json()["thumbnail"]["source"] == "GENERATED"
            )
            thumbnail_url = str(removed.json()["thumbnail"]["url"])
            thumbnail = storage.objects[("public", urlsplit(thumbnail_url).path.lstrip("/"))][0]
            with Image.open(BytesIO(thumbnail)) as decoded:
                decoded.load()
                assert decoded.size == (1280, 720)
            print(
                "PASS 03 | decoded custom image stays active after generated worker completes; removal restores 1280x720 fallback"
            )

            published = await admin.patch(path, json={"publication_status": "PUBLISHED"})
            assert published.status_code == 200 and published.json()["published_at"] is not None
            assert (await viewer.get(path)).json()["id"] == created.json()["id"]
            assert [item["id"] for item in (await viewer.get("/v1/videos")).json()["data"]] == [
                created.json()["id"]
            ]
            playback = await viewer.get(path + "/playback")
            assert playback.status_code == 200
            master = await playback_copy(
                storage, playback.json()["playback"]["url"], tmp_path / "playback"
            )
            assert master.read_text().count("#EXT-X-STREAM-INF") == 2
            assert (await admin.post(path + ":retry")).status_code == 409
            source_key = next(
                key
                for area, key in storage.objects
                if area == "private" and key.endswith("source.mp4")
            )
            assert await storage.read("private", source_key, len(source)) == source
            print(
                "PASS 04 | publish -> anonymous list/detail/playback -> all HLS references fetched; real decode passes (360p/720p)"
            )
            print(f"PLAYBACK COPY | {master} (downloaded client copy; usable with ffplay/VLC)")

            url, schema = test_database
            async with await AsyncConnection.connect(url, autocommit=True) as connection:
                await connection.execute(
                    sql.SQL("UPDATE {}.\"user\" SET role='user' WHERE id=%s").format(
                        sql.Identifier(schema + "_auth")
                    ),
                    (SUBJECT,),
                )
            assert (await admin.patch(path, json={"title": "Denied"})).status_code == 403
            assert (await admin.get(path)).status_code == 200
            async with await AsyncConnection.connect(url, autocommit=True) as connection:
                await connection.execute(
                    sql.SQL("UPDATE {}.\"user\" SET role='admin' WHERE id=%s").format(
                        sql.Identifier(schema + "_auth")
                    ),
                    (SUBJECT,),
                )
            print(
                "PASS 05 | provider role demotion immediately denies mutation with the same still-valid JWT; public viewing continues"
            )

            deleting = await admin.delete(path)
            assert deleting.status_code == 202
            assert (await viewer.get(path)).status_code == 404
            assert (await admin.get(path)).json()["status"] == "DELETING"
            assert (await admin.patch(path, json={"title": "Too late"})).status_code == 409
            launcher.release("DELETION")
            assert await launcher.finished("DELETION") == [True]
            assert (await admin.get(path)).status_code == 404
            assert (await admin.delete(path)).status_code == 404
            assert storage.objects and set(storage.objects) == storage.guards
            assert all(data == b"" for data, _ in storage.objects.values())
            with pytest.raises(StorageConflictError):
                await storage.write("private", source_key, source, "video/mp4", create_only=True)
            print(
                "PASS 06 | delete 202 hides immediately -> verified permanent zero-byte guards -> records 404; late PUT rejected"
            )
            assert len(observed_handlers) == 13
            assert all(
                handler.startswith("src.handlers.") and ".generated." not in handler
                for handler in observed_handlers
            )
            print(
                "PASS 07 | all 13 actual HTTP routes selected handwritten handlers; no generated example endpoint remains"
            )
        finally:
            await launcher.close()


async def test_showcase_failed_processing_and_stranded_launch_recovery(
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    storage: ShowcaseStorage,
    launcher: ShowcaseLauncher,
    tmp_path: Path,
) -> None:
    launcher.app = api_app
    source = make_source(tmp_path / "retry-source.mp4")
    storage.unavailable_video_writes = 3
    database: Database = api_app.state.database
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as admin,
    ):
        try:
            created = await admin.post("/v1/videos", json={"title": "Recovery showcase"})
            assert created.status_code == 201
            path = created.headers["Location"]
            accepted = await upload_source(admin, storage, path, source)
            original_job = UUID(accepted["job_id"])
            assert await launcher.finished("VIDEO") == [False]
            assert await launcher.finished("THUMBNAIL") == [True]
            failed = (await admin.get(path)).json()
            assert failed["status"] == "FAILED"
            assert failed["processing_error"]["code"] == "PROCESSING_FAILED"
            assert failed["thumbnail"]["source"] == "GENERATED"
            assert launcher.delays == [1, 4]
            async with database.connection() as connection:
                audit = await (
                    await connection.execute(
                        "SELECT execution_attempts,execution_history,output_keys FROM jobs WHERE id=%s",
                        (original_job,),
                    )
                ).fetchone()
            assert audit is not None and audit[0] == 3
            assert [event["state"] for event in audit[1]] == [
                "RUNNING",
                "TEMPORARY_FAILURE",
                "RUNNING",
                "TEMPORARY_FAILURE",
                "RUNNING",
                "FAILED",
            ]
            assert all(any(f"/attempt-{n}-" in key for key in audit[2]) for n in (1, 2, 3))
            print(
                "\nPASS 08 | controlled storage outage -> three real video executions -> FAILED; increasing delays 1s/4s, audited manifests retained"
            )
            print(
                "PASS 09 | independent generated thumbnail succeeds despite video failure; validated private source remains recoverable"
            )

            launcher.fail = True
            retried = await admin.post(path + ":retry")
            assert retried.status_code == 202
            retry_job = UUID(retried.json()["processing_job_id"])
            assert retry_job != original_job and retried.json()["attempt"] == 2
            queued = (await admin.get(path)).json()
            assert queued["status"] == "QUEUED" and queued["publication_status"] == "DRAFT"
            async with database.connection() as connection:
                stranded = await (
                    await connection.execute(
                        "SELECT state,error_code,execution_attempts,output_prefix FROM jobs WHERE id=%s",
                        (retry_job,),
                    )
                ).fetchone()
            assert stranded is not None and stranded[:3] == (
                "LAUNCH_FAILED",
                "LAUNCH_UNCONFIRMED",
                0,
            )
            assert str(retry_job) in stranded[3]
            print(
                "PASS 10 | explicit retry creates a new QUEUED/DRAFT job/namespace; launch outage leaves LAUNCH_FAILED instead of pretending dispatch"
            )

            launcher.fail = False
            assert await JobSubmission(database, launcher).recover(retry_job)
            assert await launcher.finished("VIDEO") == [False, True]
            ready = (await admin.get(path)).json()
            assert ready["status"] == "READY" and ready["publication_status"] == "DRAFT"
            assert ready["thumbnail"] == failed["thumbnail"]
            assert len(launcher.running["THUMBNAIL"]) == 1
            playback = await admin.get(path + "/playback")
            assert playback.status_code == 200
            await playback_copy(storage, playback.json()["playback"]["url"], tmp_path / "recovered")
            print(
                "PASS 11 | explicit operator recovery submits that current job; real processing reaches READY, thumbnail unchanged, HLS decodes"
            )
            assert (await admin.delete(path)).status_code == 202
            assert await launcher.finished("DELETION") == [True]
            assert (await admin.get(path)).status_code == 404
            assert all(data == b"" for data, _ in storage.objects.values())
            assert all(("public", key) in storage.guards for key in audit[2])
            print(
                "PASS 12 | explicit deletion guards successful and failed-attempt keys; recovery demonstration finishes with 404"
            )
        finally:
            await launcher.close()
