"""Bounded local FFprobe validation and real H.264/AAC HLS encoding."""

import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from src.config import Settings


class InvalidMedia(Exception):
    """Permanent source rejection with a safe administrator-facing explanation."""


class MediaProcessingError(Exception):
    """Runtime/encoder failure; raw process diagnostics are never API errors."""


class MediaRejected(MediaProcessingError):
    """A media executable rejected input, distinct from a timeout or missing binary."""


@dataclass(frozen=True)
class MediaInfo:
    duration: Decimal
    video_duration: Decimal
    width: int
    height: int
    video_index: int
    audio_index: int | None
    aspect: float
    rotated: bool


@dataclass(frozen=True)
class EncodedMedia:
    info: MediaInfo
    files: tuple[Path, ...]
    master: Path
    duration: Decimal


def command(arguments: list[str], timeout: float) -> bytes:
    # Disk-backed stderr bounds process memory; only sanitized errors leave this module.
    try:
        with tempfile.TemporaryFile() as errors:
            result = subprocess.run(
                arguments, stdout=subprocess.PIPE, stderr=errors, timeout=timeout
            )
        if result.returncode:
            raise MediaRejected
        return result.stdout
    except (OSError, subprocess.TimeoutExpired):
        raise MediaProcessingError from None


def inspect_media(source: Path, settings: Settings) -> MediaInfo:
    try:
        raw = command(
            [
                settings.ffprobe_binary,
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(source),
            ],
            settings.media_probe_timeout_seconds,
        )
        if len(raw) > 4 * 1024 * 1024:
            raise InvalidMedia("The source media metadata is excessive.")
        document = cast(dict[str, Any], json.loads(raw))
        metadata = cast(dict[str, Any], document["format"])
        if (
            "mp4" not in str(metadata["format_name"]).split(",")
            or metadata.get("tags", {}).get("major_brand", "").strip() == "qt"
        ):
            raise InvalidMedia("The source must contain MP4 video.")
        streams = cast(list[dict[str, Any]], document["streams"])
        videos = [
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
            and not stream.get("disposition", {}).get("attached_pic")
        ]
        if not videos:
            raise InvalidMedia("The source has no usable video stream.")
        video = videos[0]
        durations = [Decimal(str(metadata["duration"]))]
        durations.extend(
            Decimal(str(stream["duration"]))
            for stream in streams
            if stream.get("duration") is not None and stream.get("codec_type") in ("video", "audio")
        )
        if any(not value.is_finite() or value <= 0 for value in durations):
            raise InvalidMedia("The source has an invalid duration.")
        duration = max(durations)
        if duration > Decimal(str(settings.source_max_duration_seconds)):
            raise InvalidMedia("The source exceeds the configured video duration limit.")
        width, height = int(video["width"]), int(video["height"])
        if (
            min(width, height) < 2
            or max(width, height) > settings.media_max_dimension
            or width * height > settings.media_max_pixels
        ):
            raise InvalidMedia("The source dimensions exceed the processing limit.")
        sar = str(video.get("sample_aspect_ratio", "1:1"))
        numerator, denominator = sar.split(":") if ":" in sar else ("1", "1")
        ratio = float(numerator) / float(denominator) if float(denominator) else 1.0
        if not math.isfinite(ratio) or ratio <= 0:
            ratio = 1.0
        rotation = next(
            (
                float(item["rotation"])
                for item in video.get("side_data_list", [])
                if "rotation" in item
            ),
            0.0,
        )
        rotated = abs(round(rotation)) % 180 == 90
        aspect = width * ratio / height
        if rotated:
            width, height, aspect = height, width, 1 / aspect
        audio = next(
            (int(stream["index"]) for stream in streams if stream.get("codec_type") == "audio"),
            None,
        )
        return MediaInfo(
            duration,
            Decimal(str(video.get("duration", metadata["duration"]))),
            width,
            height,
            int(video["index"]),
            audio,
            aspect,
            rotated,
        )
    except InvalidMedia:
        raise
    except (
        MediaRejected,
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
        ZeroDivisionError,
    ):
        raise InvalidMedia("The source is corrupt or unsupported MP4 media.") from None


def rendition_sizes(info: MediaInfo) -> list[tuple[int, int, int]]:
    # Normalize display aspect without increasing either coded dimension.
    width = min(info.width, info.height * info.aspect)
    height = width / info.aspect
    levels = [tier for tier in (360, 720, 1080) if tier <= min(width, height)]
    if not levels:
        return [(max(2, int(width) // 2 * 2), max(2, int(height) // 2 * 2), 1_000_000)]
    result: list[tuple[int, int, int]] = []
    for tier in levels:
        box_width, box_height = (tier * 16 / 9, tier) if info.aspect >= 1 else (tier, tier * 16 / 9)
        factor = min(box_width / width, box_height / height, 1)
        result.append(
            (
                max(2, int(width * factor) // 2 * 2),
                max(2, int(height * factor) // 2 * 2),
                {360: 1_000_000, 720: 3_000_000, 1080: 6_000_000}[tier],
            )
        )
    return result


def validate_source(source: Path, settings: Settings) -> MediaInfo:
    info = inspect_media(source, settings)
    arguments = [
        settings.ffmpeg_binary,
        "-v",
        "error",
        "-xerror",
        "-nostdin",
        "-threads",
        str(settings.media_threads),
        "-filter_threads",
        "1",
        "-i",
        str(source),
        "-map",
        f"0:{info.video_index}",
    ]
    if info.audio_index is not None:
        arguments += ["-map", f"0:{info.audio_index}"]
    arguments += [
        "-t",
        str(settings.source_max_duration_seconds + 1),
        "-threads",
        str(settings.media_threads),
        "-f",
        "null",
        "-",
    ]
    try:
        command(arguments, settings.media_decode_timeout_seconds)
    except MediaRejected:
        raise InvalidMedia("The source could not be decoded as supported MP4 video.") from None
    return info


def encode_hls(
    source: Path, output: Path, settings: Settings, info: MediaInfo | None = None
) -> EncodedMedia:
    info = info or validate_source(source, settings)
    output.mkdir()
    variants: list[str] = []
    durations: list[Decimal] = []
    for index, (width, height, bandwidth) in enumerate(rendition_sizes(info)):
        playlist = output / f"v{index}.m3u8"
        arguments = [
            settings.ffmpeg_binary,
            "-v",
            "error",
            "-xerror",
            "-nostdin",
            "-y",
            "-threads",
            str(settings.media_threads),
            "-filter_threads",
            "1",
            "-i",
            str(source),
            "-map",
            f"0:{info.video_index}",
        ]
        if info.audio_index is not None:
            arguments += ["-map", f"0:{info.audio_index}"]
        arguments += [
            "-t",
            str(settings.source_max_duration_seconds + 1),
            "-vf",
            f"scale={width}:{height},setsar=1",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-threads",
            str(settings.media_threads),
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-maxrate",
            str(bandwidth),
            "-bufsize",
            str(2 * bandwidth),
            "-flags",
            "+cgop",
            "-sc_threshold",
            "0",
            "-force_key_frames",
            "expr:gte(t,n_forced*4)",
        ]
        if info.audio_index is not None:
            # Bound padding to the selected video timeline. Older FFmpeg/HLS
            # combinations can mux excess buffered audio with apad/-shortest alone.
            # Overall source duration still includes long audio for admission.
            arguments += [
                "-af",
                f"apad,atrim=duration={info.video_duration}",
                "-shortest",
                "-c:a",
                "aac",
                "-ac",
                "2",
                "-ar",
                "48000",
                "-b:a",
                "128k",
            ]
        arguments += [
            "-f",
            "hls",
            "-hls_time",
            "4",
            "-hls_playlist_type",
            "vod",
            "-hls_flags",
            "independent_segments",
            "-hls_segment_filename",
            str(output / f"v{index}_%05d.ts"),
            str(playlist),
        ]
        command(arguments, settings.media_encode_timeout_seconds)
        if sum(path.stat().st_size for path in output.iterdir()) > settings.media_output_max_bytes:
            raise MediaProcessingError
        segment_durations = [
            Decimal(line.split(":", 1)[1].rstrip(","))
            for line in playlist.read_text().splitlines()
            if line.startswith("#EXTINF:")
        ]
        if not segment_durations or sum(segment_durations) > Decimal(
            str(settings.source_max_duration_seconds)
        ):
            raise InvalidMedia("The decoded video exceeds the configured duration limit.")
        duration = sum(segment_durations, start=Decimal(0))
        if duration <= 0 or (durations and abs(duration - durations[0]) > Decimal(1) / 30):
            raise MediaProcessingError
        durations.append(duration)
        command(
            [
                settings.ffmpeg_binary,
                "-v",
                "error",
                "-xerror",
                "-nostdin",
                "-i",
                str(playlist),
                "-f",
                "null",
                "-",
            ],
            settings.media_encode_timeout_seconds,
        )
        variants += [
            f"#EXT-X-STREAM-INF:BANDWIDTH={int((bandwidth + (128000 if info.audio_index is not None else 0)) * 1.1)},RESOLUTION={width}x{height}",
            playlist.name,
        ]
    master = output / "master.m3u8"
    master.write_text(
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-INDEPENDENT-SEGMENTS\n" + "\n".join(variants) + "\n"
    )
    files = tuple(
        sorted(
            output.iterdir(), key=lambda path: (path.suffix == ".m3u8", path == master, path.name)
        )
    )
    return EncodedMedia(info, files, master, durations[0])
