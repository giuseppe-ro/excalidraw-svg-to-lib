from __future__ import annotations

DEFAULT_STROKE = "#000000"
DEFAULT_FILL = "transparent"
CURVE_SAMPLES = 8

SUPPORTED_ICON_EXTENSIONS = frozenset({".svg"})

ELEMENT_SORT_ORDER = {
    "rectangle": 0,
    "ellipse": 1,
    "line": 2,
    "arrow": 3,
    "image": 3,
    "text": 4,
}

DEFAULT_LABEL_FONT_SIZE = 8
DEFAULT_LABEL_FONT_FAMILY = 2
DEFAULT_LABEL_GAP = 2
DEFAULT_LABEL_LINE_HEIGHT = 1.25

DEFAULT_TARGET_ICON_SIZE = 64
MIN_STROKE_WIDTH = 1
DEFAULT_STROKE_WIDTH = 2
