"""Real fitted JPEG extraction; displayed aspect includes source SAR and rotation."""

import json
import math
from pathlib import Path
from typing import Any, cast

from src.config import Settings
from src.services.media import MediaProcessingError, command, validate_source


def extract_thumbnail(source: Path, output: Path, settings: Settings) -> Path:
    info = validate_source(source, settings)
    # FFmpeg autorotates on decode. Explicit dimensions use the display aspect;
    # setsar then prevents anamorphic metadata from distorting the final canvas.
    width = max(2, math.floor(min(1280, 720 * info.aspect) / 2) * 2)
    height = max(2, math.floor(min(720, 1280 / info.aspect) / 2) * 2)
    command(
        [
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
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:{height},setsar=1,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black",
            "-q:v",
            "2",
            "-threads",
            str(settings.media_threads),
            str(output),
        ],
        settings.media_encode_timeout_seconds,
    )
    try:
        if not 0 < output.stat().st_size <= settings.thumbnail_max_bytes:
            raise MediaProcessingError
        metadata = cast(
            dict[str, Any],
            json.loads(
                command(
                    [
                        settings.ffprobe_binary,
                        "-v",
                        "error",
                        "-show_streams",
                        "-of",
                        "json",
                        str(output),
                    ],
                    settings.media_probe_timeout_seconds,
                )
            ),
        )
        stream = metadata["streams"][0]
        if (stream["width"], stream["height"], stream["codec_name"]) != (1280, 720, "mjpeg"):
            raise MediaProcessingError
        command(
            [
                settings.ffmpeg_binary,
                "-v",
                "error",
                "-xerror",
                "-nostdin",
                "-i",
                str(output),
                "-f",
                "null",
                "-",
            ],
            settings.media_decode_timeout_seconds,
        )
        return output
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        raise MediaProcessingError from None
