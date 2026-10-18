"""Real media files made with FFmpeg, for tests that run the media worker."""

import subprocess
from pathlib import Path


def make_video(path: Path, size: str, seconds: int) -> bytes:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=24:duration={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )  # fmt: skip
    return path.read_bytes()


def make_image(path: Path, size: str) -> bytes:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}",
         "-frames:v", "1", str(path)],
        check=True,
    )  # fmt: skip
    return path.read_bytes()
