"""Decoded custom images, immutable media writes, and atomic selection."""

from asyncio import to_thread
from collections.abc import Callable
from datetime import datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError

from src.config import Settings
from src.domain.uploads import UploadAttempt, UploadRejected
from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.providers.storage import Storage, StorageConflictError, UploadInstructions
from src.repositories.database import Database
from src.repositories.thumbnails import (
    activate_custom_image,
    create_thumbnail_attempt,
    register_public_key,
    remove_custom_image,
)
from src.repositories.uploads import find_attempt
from src.repositories.videos import get_video
from src.services.videos import utc_now

IMAGE_FORMATS = {
    "image/jpeg": ("JPEG", "jpg"),
    "image/png": ("PNG", "png"),
    "image/webp": ("WEBP", "webp"),
}


def validate_image(data: bytes, content_type: str) -> None:
    try:
        with Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as image:
            if image.format != IMAGE_FORMATS[content_type][0] or image.size != (1280, 720):
                raise UploadRejected(
                    400, "The image must match its declared type and be 1280 by 720 pixels."
                )
            image.verify()
        with Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as image:
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise UploadRejected(400, "The uploaded image could not be decoded.") from None


class CustomThumbnails:
    def __init__(
        self,
        database: Database,
        storage: Storage,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self.database, self.storage, self.settings = database, storage, settings
        self.clock, self.new_id = clock, new_id

    @staticmethod
    def eligible(video: VideoRecord | None) -> VideoRecord:
        if video is None:
            raise VideoNotFound
        if video.status == "DELETING":
            raise VideoConflict("The video is being deleted.")
        return video

    @classmethod
    def current(
        cls, video: VideoRecord | None, attempt: UploadAttempt | None, video_id: UUID
    ) -> UploadAttempt:
        cls.eligible(video)
        if (
            attempt is None
            or attempt.video_id != video_id
            or attempt.kind != "THUMBNAIL"
            or not attempt.is_current
            or attempt.state not in ("PENDING", "ACCEPTED")
        ):
            raise VideoConflict("The thumbnail upload attempt is not current.")
        return attempt

    async def issue(
        self, video_id: UUID, content_type: str, size: int
    ) -> tuple[UploadAttempt, UploadInstructions]:
        if content_type not in IMAGE_FORMATS:
            raise UploadRejected(400, "Custom thumbnails support JPEG, PNG, and WebP.")
        if size > self.settings.thumbnail_max_bytes:
            raise UploadRejected(413, "The image exceeds the configured size limit.")
        async with self.database.connection() as connection:
            self.eligible(await get_video(connection, video_id))
        id = self.new_id()
        key = f"videos/{video_id}/uploads/{id}/thumbnail.{IMAGE_FORMATS[content_type][1]}"
        upload = await self.storage.sign_upload(key, content_type, 900)
        now = self.clock()
        async with self.database.connection() as connection:
            self.eligible(await get_video(connection, video_id, for_update=True))
            attempt = await create_thumbnail_attempt(
                connection,
                id=id,
                video_id=video_id,
                key=key,
                size=size,
                content_type=content_type,
                expires_at=now + timedelta(minutes=15),
                now=now,
            )
        return attempt, upload

    async def confirm(self, video_id: UUID, upload_id: UUID) -> VideoRecord:
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id)
            attempt = self.current(video, await find_attempt(connection, upload_id), video_id)
            if attempt.state == "ACCEPTED":
                assert video is not None
                return video
        observed = await self.storage.head("private", attempt.object_key)
        if observed is None:
            raise UploadRejected(404, "The uploaded image was not found.")
        if observed.size_bytes > self.settings.thumbnail_max_bytes:
            raise UploadRejected(413, "The image exceeds the configured size limit.")
        if (
            observed.size_bytes != attempt.declared_size_bytes
            or observed.content_type != attempt.content_type
        ):
            raise UploadRejected(
                400, "The uploaded image does not match its declared size or type."
            )
        data = await self.storage.read(
            "private", attempt.object_key, self.settings.thumbnail_max_bytes
        )
        if len(data) != attempt.declared_size_bytes:
            raise UploadRejected(400, "The uploaded image does not match its declared size.")
        await to_thread(validate_image, data, attempt.content_type)
        key = f"videos/{video_id}/thumbnails/custom/{attempt.id}/image.{IMAGE_FORMATS[attempt.content_type][1]}"
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id, for_update=True)
            current = self.current(video, await find_attempt(connection, upload_id), video_id)
            if current.state == "ACCEPTED":
                assert video is not None
                return video
            await register_public_key(connection, attempt.id, key)
        try:
            await self.storage.write("public", key, data, attempt.content_type, create_only=True)
        except StorageConflictError:
            # Concurrent confirmation may have committed the same immutable bytes.
            if await self.storage.read("public", key, self.settings.thumbnail_max_bytes) != data:
                raise VideoConflict("The thumbnail output is unavailable.") from None
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id, for_update=True)
            current = self.current(video, await find_attempt(connection, upload_id), video_id)
            if current.state != "ACCEPTED":
                await activate_custom_image(connection, current, key, self.clock())
            result = await get_video(connection, video_id)
            assert result is not None
            return result

    async def remove(self, video_id: UUID) -> VideoRecord:
        async with self.database.connection() as connection:
            self.eligible(await get_video(connection, video_id, for_update=True))
            await remove_custom_image(connection, video_id, self.clock())
            video = await get_video(connection, video_id)
            assert video is not None
            return video
