from __future__ import annotations

import time
from typing import Any

from excalidraw_svg_to_lib.constants import (
    DEFAULT_FILL,
    DEFAULT_LABEL_FONT_FAMILY,
    DEFAULT_LABEL_FONT_SIZE,
    DEFAULT_LABEL_GAP,
    DEFAULT_LABEL_LINE_HEIGHT,
    DEFAULT_STROKE,
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
        "x": 0,
        "y": icon_height + DEFAULT_LABEL_GAP,
        "width": icon_width,
        "height": text_height,
    }


def finalize_linear_element(
    element: dict[str, Any],
    absolute_points: list[tuple[float, float]],
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
