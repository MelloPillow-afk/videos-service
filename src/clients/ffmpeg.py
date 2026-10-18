"""FFmpeg and FFprobe, run as subprocesses to inspect and convert media files."""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaInfo:
    format_names: frozenset[str]
    duration_seconds: float
    # As displayed, after any rotation the file asks for.
    width: int
    height: int
    has_audio: bool


@dataclass(frozen=True, slots=True)
class Rendition:
    name: str
    width: int
    height: int
    video_kbps: int


class MediaToolError(Exception):
    """FFmpeg or FFprobe could not read or convert the file."""


async def probe(path: Path) -> MediaInfo | None:
    """What the file contains, or None when it holds no readable video."""
    try:
        output = await _run(
            "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
        )
    except MediaToolError:
        return None
    media: dict[str, Any] = json.loads(output)
    streams: list[dict[str, Any]] = media.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    duration = media.get("format", {}).get("duration")
    if video is None or duration is None:
        return None
    width, height = int(video["width"]), int(video["height"])
    if abs(_rotation(video)) in (90, 270):
        width, height = height, width
    return MediaInfo(
        format_names=frozenset(media["format"]["format_name"].split(",")),
        duration_seconds=float(duration),
        width=width,
        height=height,
        has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
    )


async def make_hls(
    source: Path, output: Path, renditions: list[Rendition], *, has_audio: bool
) -> None:
    """Write H.264/AAC HLS renditions to output/<name>/ and a master.m3u8 that lists them."""
    count = len(renditions)
    filters = f"[0:v]split={count}{''.join(f'[s{i}]' for i in range(count))};" + ";".join(
        f"[s{i}]scale={rendition.width}:{rendition.height},setsar=1[v{i}]"
        for i, rendition in enumerate(renditions)
    )
    arguments = ["-filter_complex", filters]
    for i, rendition in enumerate(renditions):
        kbps = rendition.video_kbps
        arguments += [
            "-map", f"[v{i}]",
            f"-b:v:{i}", f"{kbps}k",
            f"-maxrate:v:{i}", f"{kbps * 107 // 100}k",
            f"-bufsize:v:{i}", f"{kbps * 3 // 2}k",
        ]  # fmt: skip
        if has_audio:
            arguments += ["-map", "0:a:0"]
    if has_audio:
        arguments += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    streams = " ".join(
        f"v:{i},a:{i},name:{rendition.name}" if has_audio else f"v:{i},name:{rendition.name}"
        for i, rendition in enumerate(renditions)
    )
    await _run(
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        *arguments,
        "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "main", "-pix_fmt", "yuv420p",
        # Keyframes on segment boundaries, so every rendition switches cleanly.
        "-force_key_frames", "expr:gte(t,n_forced*6)",
        "-f", "hls", "-hls_time", "6", "-hls_playlist_type", "vod",
        "-hls_segment_filename", str(output / "%v" / "segment_%03d.ts"),
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", streams,
        str(output / "%v" / "index.m3u8"),
    )  # fmt: skip


async def make_thumbnail(
    source: Path, output: Path, *, at_seconds: float, width: int, height: int
) -> None:
    """Write one JPEG frame, fitted inside width x height and padded, without cropping."""
    fit = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )
    await _run(
        "ffmpeg", "-v", "error", "-y", "-ss", f"{at_seconds:.3f}", "-i", str(source),
        "-frames:v", "1", "-vf", fit, "-q:v", "3", str(output),
    )  # fmt: skip


@dataclass(frozen=True, slots=True)
class ImageInfo:
    codec: str
    width: int
    height: int


async def probe_image(path: Path) -> ImageInfo | None:
    """The file's first picture, or None when it holds none FFprobe can read."""
    try:
        output = await _run(
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
            "-of", "json", str(path),
        )  # fmt: skip
    except MediaToolError:
        return None
    streams: list[dict[str, Any]] = json.loads(output).get("streams", [])
    if not streams:
        return None
    stream = streams[0]
    return ImageInfo(codec=stream["codec_name"], width=stream["width"], height=stream["height"])


async def crop_image(source: Path, output: Path, *, width: int, height: int) -> None:
    """Write a JPEG that fills width x height, cropping the centered overflow."""
    fill = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    await _run(
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-frames:v", "1", "-vf", fill, "-q:v", "3", str(output),
    )  # fmt: skip


async def resize_image(source: Path, output: Path, *, width: int, height: int) -> None:
    """Write a JPEG scaled to exactly width x height."""
    await _run(
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-frames:v", "1", "-vf", f"scale={width}:{height},setsar=1", "-q:v", "3", str(output),
    )  # fmt: skip


def _rotation(stream: dict[str, Any]) -> int:
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            return int(side_data["rotation"])
    return int(stream.get("tags", {}).get("rotate", 0))


async def _run(*command: str) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise MediaToolError(stderr.decode(errors="replace")[-2000:])
    return stdout
