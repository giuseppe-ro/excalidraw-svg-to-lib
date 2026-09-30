from __future__ import annotations

DEFAULT_STROKE = "#000000"
DEFAULT_FILL = "transparent"
CURVE_SAMPLES = 8
MIN_ARC_SAMPLES = 4

SUPPORTED_ICON_EXTENSIONS = frozenset({".svg"})

# Files silently skipped when scanning directories (no warning).
IGNORED_FILE_NAMES = frozenset({
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "node_modules",
    "package-lock.json",
})

ELEMENT_SORT_ORDER = {
    "rectangle": 0,
    "ellipse": 1,
    "line": 2,
    "arrow": 3,
    "image": 3,
    "text": 4,
}

DEFAULT_LABEL_FONT_SIZE = 10
DEFAULT_LABEL_FONT_FAMILY = 2
DEFAULT_LABEL_GAP = 2
DEFAULT_LABEL_LINE_HEIGHT = 1.25

DEFAULT_TARGET_ICON_SIZE = 64
ICON_PADDING = 4
MIN_STROKE_WIDTH = 0.2
DEFAULT_STROKE_WIDTH = 0.2

# Thresholds for is_circle_like — classifies small-circular sampled paths
# (from approximated arcs / circles) as ellipses for cleaner output.
CIRCLE_LIKE_MIN_POINTS = 6
CIRCLE_LIKE_MAX_DIM = 6
CIRCLE_LIKE_MIN_RATIO = 0.7
CIRCLE_LIKE_MAX_RATIO = 1.3
