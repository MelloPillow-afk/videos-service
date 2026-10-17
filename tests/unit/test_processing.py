"""Rendition sizes follow the source, and the worker command needs one job ID."""

import pytest

from src.providers.ffmpeg import MediaInfo, Rendition
from src.services.processing import renditions
from src.workers.media import main


def media(width: int, height: int) -> MediaInfo:
    return MediaInfo(
        format_names=frozenset({"mp4"}),
        duration_seconds=1,
        width=width,
        height=height,
        has_audio=False,
    )


def test_full_hd_source_gets_every_rendition() -> None:
    assert renditions(media(1920, 1080)) == [
        Rendition("360p", 640, 360, 800),
        Rendition("720p", 1280, 720, 2800),
        Rendition("1080p", 1920, 1080, 5000),
    ]


def test_portrait_source_scales_its_shorter_side() -> None:
    assert renditions(media(720, 1280)) == [
        Rendition("360p", 360, 640, 800),
        Rendition("720p", 720, 1280, 2800),
    ]


def test_source_below_360p_keeps_its_own_size() -> None:
    assert renditions(media(427, 241)) == [Rendition("240p", 426, 240, 800)]


def test_worker_needs_exactly_one_job_id() -> None:
    with pytest.raises(SystemExit, match="usage"):
        main([])
