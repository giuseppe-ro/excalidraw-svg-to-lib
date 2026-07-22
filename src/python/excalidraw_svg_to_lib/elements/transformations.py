from __future__ import annotations

from typing import Any

from excalidraw_svg_to_lib.constants import ELEMENT_SORT_ORDER, MIN_STROKE_WIDTH
from excalidraw_svg_to_lib.elements.queries import element_bounds


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
