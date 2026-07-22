from __future__ import annotations

from typing import Any

Point = tuple[float, float]


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
