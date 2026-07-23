from __future__ import annotations

import time
from typing import Any

from excalidraw_svg_to_lib.constants import (
    DEFAULT_FILL,
    DEFAULT_LABEL_FONT_FAMILY,
    DEFAULT_LABEL_FONT_SIZE,
    DEFAULT_LABEL_LINE_HEIGHT,
    DEFAULT_STROKE,
    DEFAULT_STROKE_WIDTH,
    ELEMENT_SORT_ORDER,
    ICON_PADDING,
    MIN_STROKE_WIDTH,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator

Point = tuple[float, float]


# ---------------------------------------------------------------------------
# Element factories
# ---------------------------------------------------------------------------


def create_base_element(element_type: str, group_id: str, ids: IdGenerator) -> dict[str, Any]:
    """Create the common fields shared by all Excalidraw elements."""
    return {
        "type": element_type,
        "version": 1,
        "versionNonce": ids.random_int(),
        "isDeleted": False,
        "id": ids.random_id(),
        "fillStyle": "solid",
        "strokeWidth": DEFAULT_STROKE_WIDTH,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "strokeColor": DEFAULT_STROKE,
        "backgroundColor": DEFAULT_FILL,
        "seed": ids.random_int(),
        "groupIds": [group_id],
        "strokeSharpness": "sharp",
        "boundElementIds": [],
    }


def apply_paint_style(element: dict[str, Any], style: dict[str, Any]) -> None:
    element["backgroundColor"] = (
        style["fill"] if style["fill"] != "transparent" else DEFAULT_FILL
    )
    # When stroke is "transparent", keep it transparent (not DEFAULT_STROKE).
    # SVG stroke="none" means no stroke at all.
    if style["stroke"] == "transparent":
        element["strokeColor"] = "transparent"
        element["strokeWidth"] = 0
    else:
        element["strokeColor"] = style["stroke"]
        element["strokeWidth"] = (
            style["stroke_width"]
            if style["stroke_width"] > 0
            else DEFAULT_STROKE_WIDTH
        )
    element["opacity"] = style.get("opacity", 100)


def finalize_linear_element(
    element: dict[str, Any],
    absolute_points: list[Point],
) -> dict[str, Any] | None:
    if len(absolute_points) < 2:
        return None

    xs = [point[0] for point in absolute_points]
    ys = [point[1] for point in absolute_points]
    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)

    element["x"] = min_x
    element["y"] = min_y
    element["width"] = max_x - min_x
    element["height"] = max_y - min_y
    element["points"] = [[x - min_x, y - min_y] for x, y in absolute_points]
    element["lastCommittedPoint"] = None
    element["startBinding"] = None
    element["endBinding"] = None
    element["startArrowhead"] = None
    element["endArrowhead"] = None
    return element


def create_invisible_box_element(
    icon_bounds: tuple[float, float, float, float],
    ids: IdGenerator,
    group_id: str,
) -> dict[str, Any]:
    """Create an invisible rectangle around the icon that arrows can snap to."""
    min_x, min_y, max_x, max_y = icon_bounds
    return {
        **create_base_element("rectangle", group_id, ids),
        "strokeColor": "transparent",
        "strokeWidth": 0,
        "backgroundColor": "transparent",
        "frameId": None,
        "roundness": None,
        "x": min_x - ICON_PADDING,
        "y": min_y - ICON_PADDING,
        "width": (max_x - min_x) + 2 * ICON_PADDING,
        "height": (max_y - min_y) + 2 * ICON_PADDING,
    }


def create_label_element(
    label: str,
    outer_box_x: float,
    outer_box_width: float,
    label_y: float,
    ids: IdGenerator,
    group_id: str,
) -> dict[str, Any]:
    """Create a text label element for the icon."""
    font_size = DEFAULT_LABEL_FONT_SIZE
    line_height = DEFAULT_LABEL_LINE_HEIGHT
    return {
        **create_base_element("text", group_id, ids),
        "frameId": None,
        "roundness": None,
        "boundElements": None,
        "link": None,
        "locked": False,
        "updated": int(time.time() * 1000),
        "text": label,
        "originalText": label,
        "fontSize": font_size,
        "fontFamily": DEFAULT_LABEL_FONT_FAMILY,
        "textAlign": "center",
        "verticalAlign": "top",
        "containerId": None,
        "autoResize": True,
        "lineHeight": line_height,
        "x": outer_box_x,
        "y": label_y,
        "width": outer_box_width,
        "height": font_size * line_height,
    }


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def element_bounds(elements: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    min_x = min(element["x"] for element in elements)
    min_y = min(element["y"] for element in elements)
    max_x = max(element["x"] + element["width"] for element in elements)
    max_y = max(element["y"] + element["height"] for element in elements)
    return min_x, min_y, max_x, max_y


def icon_group_id(elements: list[dict[str, Any]]) -> str:
    group_ids = elements[0].get("groupIds") or []
    if not group_ids:
        raise ValueError("Icon elements must belong to a group")
    return group_ids[0]


def is_circle_like(points: list[Point]) -> bool:
    if len(points) < 6:
        return False
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0 or height <= 0 or width > 6 or height > 6:
        return False
    ratio = width / height
    return 0.7 < ratio < 1.3


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------


def sort_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(elements, key=lambda element: ELEMENT_SORT_ORDER.get(element["type"], 99))


def normalize_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not elements:
        return elements
    min_x = min(element["x"] for element in elements)
    min_y = min(element["y"] for element in elements)
    for element in elements:
        element["x"] -= min_x
        element["y"] -= min_y
    return elements


def _scale_elements(elements: list[dict[str, Any]], scale: float) -> list[dict[str, Any]]:
    if scale == 1.0:
        return elements
    for element in elements:
        element["x"] *= scale
        element["y"] *= scale
        element["width"] *= scale
        element["height"] *= scale
        if "strokeWidth" in element:
            sw = element["strokeWidth"] * scale
            # Preserve zero-width strokes (transparent / invisible stroke).
            # When scaling up, clamp to MIN_STROKE_WIDTH so strokes stay
            # visible.  When scaling down, let the stroke shrink proportionally
            # to avoid disproportionately thick strokes on tiny icons.
            if sw > 0 and scale > 1:
                sw = max(MIN_STROKE_WIDTH, sw)
            element["strokeWidth"] = sw
        points = element.get("points")
        if points:
            element["points"] = [[p[0] * scale, p[1] * scale] for p in points]
    return elements


def fit_elements_to_size(
    elements: list[dict[str, Any]],
    target_size: float,
) -> list[dict[str, Any]]:
    if not elements or target_size <= 0:
        return elements
    min_x, min_y, max_x, max_y = element_bounds(elements)
    max_dimension = max(max_x - min_x, max_y - min_y)
    if max_dimension <= 0:
        return elements
    return _scale_elements(elements, target_size / max_dimension)
