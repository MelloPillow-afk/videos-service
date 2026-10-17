"""The 16:9 sizes every thumbnail is rendered at, and where each size is stored."""

# Smallest first; xl is the size a thumbnail is rendered from.
SIZES: dict[str, tuple[int, int]] = {
    "xs": (160, 90),
    "sm": (320, 180),
    "md": (640, 360),
    "lg": (960, 540),
    "xl": (1280, 720),
}


def size_key(prefix: str, name: str) -> str:
    return f"{prefix}/{name}.jpg"
