"""Where tests serve processed media from, and the sizes a ready thumbnail lists."""

from src.libs.thumbnails import SIZES

MEDIA_BASE_URL = "https://media.example.com"


def expected_sizes(prefix: str) -> dict[str, dict[str, object]]:
    return {
        name: {"width": width, "height": height, "url": f"{MEDIA_BASE_URL}/{prefix}/{name}.jpg"}
        for name, (width, height) in SIZES.items()
    }
