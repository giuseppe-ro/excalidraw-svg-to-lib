from __future__ import annotations

from typing import Any

from svg_to_excalidrawlib.constants import (
    DEFAULT_FILL,
    DEFAULT_STROKE,
    ELEMENT_SORT_ORDER,
)
from svg_to_excalidrawlib.id_generator import IdGenerator

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
