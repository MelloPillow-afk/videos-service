"""Where tests serve processed media from, and the sizes a ready thumbnail lists."""

MEDIA_BASE_URL = "https://media.example.com"

# The thumbnail sizes in api-specs, restated so a change to the code's sizes fails tests.
THUMBNAIL_SIZES = {
    "xs": (160, 90),
    "sm": (320, 180),
    "md": (640, 360),
    "lg": (960, 540),
    "xl": (1280, 720),
}


def expected_sizes(prefix: str) -> dict[str, dict[str, object]]:
    return {
        name: {"width": width, "height": height, "url": f"{MEDIA_BASE_URL}/{prefix}/{name}.jpg"}
        for name, (width, height) in THUMBNAIL_SIZES.items()
    }
