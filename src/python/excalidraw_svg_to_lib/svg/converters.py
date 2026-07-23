from __future__ import annotations

from typing import Any

from excalidraw_svg_to_lib.elements import (
    Point,
    apply_paint_style,
    create_base_element,
    finalize_linear_element,
    is_circle_like,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.svg.path_sampling import path_commands_to_points
from excalidraw_svg_to_lib.svg.transforms import (
    IDENTITY,
    Transform,
    apply_transform_to_element,
    compose,
    parse_transform,
)
from excalidraw_svg_to_lib.svg.utils import inherit_style, local_name, parse_length


def _convert_rect(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    width = parse_length(attributes.get("width"))
    height = parse_length(attributes.get("height"))
    if width <= 0 or height <= 0:
        return []

    element = create_base_element("rectangle", group_id, ids)
    element["x"] = parse_length(attributes.get("x"))
    element["y"] = parse_length(attributes.get("y"))
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
    radius = parse_length(attributes.get("r"))
    if radius <= 0:
        return []

    center_x = parse_length(attributes.get("cx"))
    center_y = parse_length(attributes.get("cy"))
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
    radius_x = parse_length(attributes.get("rx"))
    radius_y = parse_length(attributes.get("ry"))
    if radius_x <= 0 or radius_y <= 0:
        return []

    center_x = parse_length(attributes.get("cx"))
    center_y = parse_length(attributes.get("cy"))
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
            (parse_length(attributes.get("x1")), parse_length(attributes.get("y1"))),
            (parse_length(attributes.get("x2")), parse_length(attributes.get("y2"))),
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


def _convert_element(
    element,
    style: dict[str, Any],
    transform: Transform,
    group_id: str,
    ids: IdGenerator,
    output: list[dict[str, Any]],
) -> None:
    node_style = inherit_style(style, element.attrib)
    tag = local_name(element.tag)

    # Compose this element's transform into the accumulated transform
    raw_transform = element.attrib.get("transform")
    if raw_transform:
        parsed = parse_transform(raw_transform)
        current_transform = compose(transform, parsed) if parsed else transform
    else:
        current_transform = transform

    converters = get_converters()
    if tag in converters:
        new_elements = converters[tag](element.attrib, inherit_style(node_style, element.attrib), group_id, ids)
        # Apply accumulated transform to newly created elements
        if current_transform != IDENTITY:
            for elem in new_elements:
                apply_transform_to_element(current_transform, elem)
        output.extend(new_elements)

    for child in element:
        _convert_element(child, node_style, current_transform, group_id, ids, output)


# Registry of SVG tag → converter function
SVG_CONVERTERS: dict[str, callable] = {}


def get_converters() -> dict[str, callable]:
    if not SVG_CONVERTERS:
        SVG_CONVERTERS.update({
            "rect": lambda attrs, style, gid, ids: _convert_rect(attrs, style, gid, ids),
            "circle": lambda attrs, style, gid, ids: _convert_circle(attrs, style, gid, ids),
            "ellipse": lambda attrs, style, gid, ids: _convert_ellipse(attrs, style, gid, ids),
            "path": lambda attrs, style, gid, ids: _convert_path(attrs, style, gid, ids),
            "line": lambda attrs, style, gid, ids: _convert_line(attrs, style, gid, ids),
            "polygon": lambda attrs, style, gid, ids: _convert_polygon_like(
                attrs, style, gid, ids, close_path=True
            ),
            "polyline": lambda attrs, style, gid, ids: _convert_polygon_like(
                attrs, style, gid, ids, close_path=False
            ),
        })
    return SVG_CONVERTERS
