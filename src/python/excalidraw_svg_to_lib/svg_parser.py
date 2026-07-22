from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from svg.path import Arc, Close, CubicBezier, Line, Move, Path, QuadraticBezier, parse_path

from excalidraw_svg_to_lib.constants import CURVE_SAMPLES, DEFAULT_FILL, DEFAULT_STROKE
from excalidraw_svg_to_lib.elements import (
    Point,
    apply_paint_style,
    create_base_element,
    finalize_linear_element,
    is_circle_like,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _parse_length(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    return float(value.replace("px", ""))


def parse_view_box(svg_element: ET.Element) -> dict[str, float]:
    view_box = svg_element.get("viewBox")
    if view_box:
        parts = [float(part) for part in view_box.replace(",", " ").split()]
        x, y, width, height = parts
        return {"x": x, "y": y, "width": width, "height": height}

    width = _parse_length(svg_element.get("width"), 64.0)
    height = _parse_length(svg_element.get("height"), 64.0)
    return {"x": 0.0, "y": 0.0, "width": width, "height": height}


def normalize_color(color: str | None) -> str:
    if not color or color == "none":
        return "transparent"
    return color


def inherit_style(parent_style: dict[str, Any], attributes: dict[str, str]) -> dict[str, Any]:
    style = dict(parent_style)

    if "fill" in attributes:
        style["fill"] = normalize_color(attributes["fill"])
    if "stroke" in attributes:
        style["stroke"] = normalize_color(attributes["stroke"])
    if "stroke-width" in attributes:
        style["stroke_width"] = float(attributes["stroke-width"])
    if "opacity" in attributes:
        style["opacity"] = float(attributes["opacity"]) * 100

    return style


def _sample_cubic(
    start: Point,
    control1: Point,
    control2: Point,
    end: Point,
    samples: int = CURVE_SAMPLES,
) -> list[Point]:
    points: list[Point] = []
    for index in range(1, samples + 1):
        t = index / samples
        mt = 1 - t
        x = (
            mt**3 * start[0]
            + 3 * mt**2 * t * control1[0]
            + 3 * mt * t**2 * control2[0]
            + t**3 * end[0]
        )
        y = (
            mt**3 * start[1]
            + 3 * mt**2 * t * control1[1]
            + 3 * mt * t**2 * control2[1]
            + t**3 * end[1]
        )
        points.append((x, y))
    return points


def _sample_quadratic(
    start: Point,
    control: Point,
    end: Point,
    samples: int = CURVE_SAMPLES,
) -> list[Point]:
    points: list[Point] = []
    for index in range(1, samples + 1):
        t = index / samples
        mt = 1 - t
        x = mt**2 * start[0] + 2 * mt * t * control[0] + t**2 * end[0]
        y = mt**2 * start[1] + 2 * mt * t * control[1] + t**2 * end[1]
        points.append((x, y))
    return points


def _complex_to_point(value: complex) -> Point:
    return (value.real, value.imag)


def path_commands_to_points(path_data: str) -> list[list[Point]]:
    parsed_path: Path = parse_path(path_data)
    subpaths: list[list[Point]] = []
    current: list[Point] = []
    cursor: Point = (0.0, 0.0)

    def push_current() -> None:
        nonlocal current
        if len(current) >= 2:
            subpaths.append(current)
        current = []

    for segment in parsed_path:
        if isinstance(segment, Move):
            push_current()
            cursor = _complex_to_point(segment.end)
            current.append(cursor)
        elif isinstance(segment, Line):
            cursor = _complex_to_point(segment.end)
            current.append(cursor)
        elif isinstance(segment, CubicBezier):
            sampled = _sample_cubic(
                cursor,
                _complex_to_point(segment.control1),
                _complex_to_point(segment.control2),
                _complex_to_point(segment.end),
            )
            current.extend(sampled)
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, QuadraticBezier):
            sampled = _sample_quadratic(
                cursor,
                _complex_to_point(segment.control),
                _complex_to_point(segment.end),
            )
            current.extend(sampled)
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, Arc):
            for index in range(1, CURVE_SAMPLES + 1):
                point = segment.point(index / CURVE_SAMPLES)
                current.append(_complex_to_point(point))
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, Close):
            if current:
                current.append(current[0])

    push_current()
    return subpaths


def _convert_rect(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    width = _parse_length(attributes.get("width"))
    height = _parse_length(attributes.get("height"))
    if width <= 0 or height <= 0:
        return []

    element = create_base_element("rectangle", group_id, ids)
    element["x"] = _parse_length(attributes.get("x"))
    element["y"] = _parse_length(attributes.get("y"))
    element["width"] = width
    element["height"] = height
    apply_paint_style(element, style)
    return [element]


def _convert_circle(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    radius = _parse_length(attributes.get("r"))
    if radius <= 0:
        return []

    center_x = _parse_length(attributes.get("cx"))
    center_y = _parse_length(attributes.get("cy"))
    element = create_base_element("ellipse", group_id, ids)
    element["x"] = center_x - radius
    element["y"] = center_y - radius
    element["width"] = radius * 2
    element["height"] = radius * 2
    apply_paint_style(element, style)
    return [element]


def _convert_ellipse(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    radius_x = _parse_length(attributes.get("rx"))
    radius_y = _parse_length(attributes.get("ry"))
    if radius_x <= 0 or radius_y <= 0:
        return []

    center_x = _parse_length(attributes.get("cx"))
    center_y = _parse_length(attributes.get("cy"))
    element = create_base_element("ellipse", group_id, ids)
    element["x"] = center_x - radius_x
    element["y"] = center_y - radius_y
    element["width"] = radius_x * 2
    element["height"] = radius_y * 2
    apply_paint_style(element, style)
    return [element]


def _convert_circle_like_subpath(
    subpath: list[Point],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> dict[str, Any]:
    xs = [point[0] for point in subpath]
    ys = [point[1] for point in subpath]
    element = create_base_element("ellipse", group_id, ids)
    element["x"] = min(xs)
    element["y"] = min(ys)
    element["width"] = max(xs) - min(xs)
    element["height"] = max(ys) - min(ys)
    apply_paint_style(element, style)
    return element


def _convert_path(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    path_data = attributes.get("d")
    if not path_data:
        return []

    elements: list[dict[str, Any]] = []
    for subpath in path_commands_to_points(path_data):
        if is_circle_like(subpath):
            elements.append(_convert_circle_like_subpath(subpath, style, group_id, ids))
            continue

        element = create_base_element("line", group_id, ids)
        apply_paint_style(element, style)
        finalized = finalize_linear_element(element, subpath)
        if finalized is not None:
            elements.append(finalized)

    return elements


def _convert_line(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    element = create_base_element("line", group_id, ids)
    line_style = dict(style)
    line_style["fill"] = "transparent"
    apply_paint_style(element, line_style)
    finalized = finalize_linear_element(
        element,
        [
            (_parse_length(attributes.get("x1")), _parse_length(attributes.get("y1"))),
            (_parse_length(attributes.get("x2")), _parse_length(attributes.get("y2"))),
        ],
    )
    return [finalized] if finalized is not None else []


def _convert_polygon_like(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    close_path: bool,
) -> list[dict[str, Any]]:
    raw_points = attributes.get("points", "").replace(",", " ").split()
    numbers = [float(value) for value in raw_points if value]
    points: list[Point] = [
        (numbers[index], numbers[index + 1]) for index in range(0, len(numbers) - 1, 2)
    ]

    if len(points) < 2:
        return []

    if close_path:
        points.append(points[0])

    element = create_base_element("line", group_id, ids)
    apply_paint_style(element, style)
    finalized = finalize_linear_element(element, points)
    return [finalized] if finalized is not None else []


def _walk_element(
    element: ET.Element,
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    output: list[dict[str, Any]],
) -> None:
    node_style = inherit_style(style, element.attrib)
    tag = _local_name(element.tag)

    converters = {
        "rect": lambda attrs: _convert_rect(attrs, inherit_style(node_style, attrs), group_id, ids),
        "circle": lambda attrs: _convert_circle(attrs, inherit_style(node_style, attrs), group_id, ids),
        "ellipse": lambda attrs: _convert_ellipse(attrs, inherit_style(node_style, attrs), group_id, ids),
        "path": lambda attrs: _convert_path(attrs, inherit_style(node_style, attrs), group_id, ids),
        "line": lambda attrs: _convert_line(attrs, inherit_style(node_style, attrs), group_id, ids),
        "polygon": lambda attrs: _convert_polygon_like(
            attrs,
            inherit_style(node_style, attrs),
            group_id,
            ids,
            close_path=True,
        ),
        "polyline": lambda attrs: _convert_polygon_like(
            attrs,
            inherit_style(node_style, attrs),
            group_id,
            ids,
            close_path=False,
        ),
    }

    if tag in converters:
        output.extend(converters[tag](element.attrib))

    for child in element:
        _walk_element(child, node_style, group_id, ids, output)


def svg_to_elements(svg_content: str, ids: IdGenerator) -> tuple[list[dict[str, Any]], dict[str, float]]:
    root = ET.fromstring(svg_content)
    if _local_name(root.tag) != "svg":
        raise ValueError("Invalid SVG: missing <svg> root element")

    view_box = parse_view_box(root)
    group_id = ids.random_id()
    elements: list[dict[str, Any]] = []
    root_style = inherit_style(
        {
            "fill": DEFAULT_FILL,
            "stroke": DEFAULT_STROKE,
            "stroke_width": 0.0,
            "opacity": 100.0,
        },
        root.attrib,
    )

    _walk_element(root, root_style, group_id, ids, elements)
    return elements, view_box
