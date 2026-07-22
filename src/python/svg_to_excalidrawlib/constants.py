from __future__ import annotations

DEFAULT_STROKE = "#000000"
DEFAULT_FILL = "transparent"
CURVE_SAMPLES = 8

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
SUPPORTED_ICON_EXTENSIONS = frozenset({".svg", *SUPPORTED_IMAGE_EXTENSIONS})

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

ELEMENT_SORT_ORDER = {
    "rectangle": 0,
    "ellipse": 1,
    "line": 2,
    "arrow": 3,
}
