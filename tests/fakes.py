"""Stand-ins for R2 and worker launches, so no test reaches Cloudflare, Google, or Docker."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from src.providers.cloudflare import PresignedUpload

UPLOAD_EXPIRES_AT = datetime(2026, 10, 13, 14, 15, tzinfo=UTC)


@dataclass
class FakeStorage:
    """Uploaded files and published media, by key."""

    files: dict[str, bytes] = field(default_factory=dict[str, bytes])
    media: dict[str, bytes] = field(default_factory=dict[str, bytes])

    def presign_upload(self, key: str, _content_type: str) -> PresignedUpload:
        return PresignedUpload(
            url=f"https://uploads.example.com/{key}?signature=test",
            expires_at=UPLOAD_EXPIRES_AT,
        )

    async def uploaded_size(self, key: str) -> int | None:
        file = self.files.get(key)
        return None if file is None else len(file)

    async def download_source(self, key: str, path: Path) -> None:
        path.write_bytes(self.files[key])

    async def upload_media(self, path: Path, key: str) -> None:
        self.media[key] = path.read_bytes()


@dataclass
class FakeLauncher:
    """Records launched jobs; launches numbered in failing raise instead, counting from 0."""

    launched: list[UUID] = field(default_factory=list[UUID])
    failing: set[int] = field(default_factory=set[int])
    _calls: int = 0

    async def run_job(self, job_id: UUID) -> None:
        call, self._calls = self._calls, self._calls + 1
        if call in self.failing:
            raise RuntimeError("launch failed")
        self.launched.append(job_id)
