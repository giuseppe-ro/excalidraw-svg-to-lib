from __future__ import annotations

import time
from typing import Any

from excalidraw_svg_to_lib.constants import (
    CHAR_WIDTH_RATIO,
    DEFAULT_FILL,
    DEFAULT_LABEL_FONT_FAMILY,
    DEFAULT_LABEL_FONT_SIZE,
    DEFAULT_LABEL_GAP,
    DEFAULT_LABEL_LINE_HEIGHT,
    DEFAULT_STROKE,
    ELEMENT_SORT_ORDER,
    MIN_STROKE_WIDTH,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator

Point = tuple[float, float]


def apply_paint_style(element: dict[str, Any], style: dict[str, Any]) -> None:
    element["backgroundColor"] = (
        style["fill"] if style["fill"] != "transparent" else DEFAULT_FILL
    )
    element["strokeColor"] = (
        style["stroke"] if style["stroke"] != "transparent" else DEFAULT_STROKE
    )
    element["strokeWidth"] = (
        style["stroke_width"]
        if style["stroke"] != "transparent" and style["stroke_width"] > 0
        else 2
    )
    element["opacity"] = style.get("opacity", 100)


def create_base_element(element_type: str, group_id: str, ids: IdGenerator) -> dict[str, Any]:
    return {
        "type": element_type,
        "version": 1,
        "versionNonce": ids.random_int(),
        "isDeleted": False,
        "id": ids.random_id(),
        "fillStyle": "solid",
        "strokeWidth": 2,
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


def element_bounds(elements: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    min_x = min(element["x"] for element in elements)
    min_y = min(element["y"] for element in elements)
    max_x = max(element["x"] + element["width"] for element in elements)
    max_y = max(element["y"] + element["height"] for element in elements)
    return min_x, min_y, max_x, max_y


def scale_elements(elements: list[dict[str, Any]], scale: float) -> list[dict[str, Any]]:
    if scale == 1.0:
        return elements

    for element in elements:
        element["x"] *= scale
        element["y"] *= scale
        element["width"] *= scale
        element["height"] *= scale

        if "strokeWidth" in element:
            element["strokeWidth"] = max(MIN_STROKE_WIDTH, element["strokeWidth"] * scale)

        points = element.get("points")
        if points:
            element["points"] = [[point[0] * scale, point[1] * scale] for point in points]

    return elements


def fit_elements_to_size(
    elements: list[dict[str, Any]],
    target_size: float,
) -> list[dict[str, Any]]:
    if not elements or target_size <= 0:
        return elements

    min_x, min_y, max_x, max_y = element_bounds(elements)
    bounds_width = max_x - min_x
    bounds_height = max_y - min_y
    max_dimension = max(bounds_width, bounds_height)

    if max_dimension <= 0:
        return elements

    scale = target_size / max_dimension
    return scale_elements(elements, scale)


def icon_group_id(elements: list[dict[str, Any]]) -> str:
    group_ids = elements[0].get("groupIds") or []
    if not group_ids:
        raise ValueError("Icon elements must belong to a group")
    return group_ids[0]


def create_label_element(
    label: str,
    icon_bounds: tuple[float, float, float, float],
    ids: IdGenerator,
    group_id: str,
) -> dict[str, Any]:
    min_x, min_y, max_x, max_y = icon_bounds
    icon_width = max_x - min_x
    icon_height = max_y - min_y

    font_size = DEFAULT_LABEL_FONT_SIZE
    line_height = DEFAULT_LABEL_LINE_HEIGHT
    text_width = len(label) * font_size * CHAR_WIDTH_RATIO
    text_height = font_size * line_height

    return {
        "type": "text",
        "version": 1,
        "versionNonce": ids.random_int(),
        "isDeleted": False,
        "id": ids.random_id(),
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "strokeColor": DEFAULT_STROKE,
        "backgroundColor": DEFAULT_FILL,
        "seed": ids.random_int(),
        "groupIds": [group_id],
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
        "autoResize": False,
        "lineHeight": line_height,
        "x": (icon_width - text_width) / 2,
        "y": icon_height + DEFAULT_LABEL_GAP,
        "width": text_width,
        "height": text_height,
    }
