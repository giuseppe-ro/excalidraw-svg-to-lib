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


def _subpath_bounds(subpath: list[Point]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) for a subpath."""
    xs = [p[0] for p in subpath]
    ys = [p[1] for p in subpath]
    return min(xs), min(ys), max(xs), max(ys)


def _subpath_area(subpath: list[Point]) -> float:
    """Return the bounding-box area of a subpath."""
    min_x, min_y, max_x, max_y = _subpath_bounds(subpath)
    return (max_x - min_x) * (max_y - min_y)


def _bbox_contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    """Check if *outer* bounding box fully contains *inner* bounding box."""
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _find_background_color(elements: list[dict[str, Any]]) -> str | None:
    """Scan existing output elements for a solid-fill rectangle/ellipse to use
    as the background colour for hole-punching when fill-rule='evenodd' is active."""
    best: tuple[float, str] | None = None
    for elem in elements:
        if elem.get("type") not in ("rectangle", "ellipse"):
            continue
        bg = elem.get("backgroundColor", "")
        if bg == "transparent" or not bg:
            continue
        area = elem["width"] * elem["height"]
        if best is None or area > best[0]:
            best = (area, bg)
    return best[1] if best else None


def _convert_path(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    output_elements: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    path_data = attributes.get("d")
    if not path_data:
        return []

    subpaths = path_commands_to_points(path_data)
    if not subpaths:
        return []

    fill_rule = style.get("fill_rule", "nonzero")
    fill = style.get("fill", "transparent")

    # When fill-rule="evenodd" with a non-transparent fill, inner subpaths
    # are *holes* and should show the background.  Detect hole subpaths by
    # bounding-box containment and punch them with the background colour.
    if fill_rule == "evenodd" and fill != "transparent" and len(subpaths) > 1:
        # Sort by area descending — largest subpaths are outer boundaries
        indexed = list(enumerate(subpaths))
        indexed.sort(key=lambda item: _subpath_area(item[1]), reverse=True)

        hole_indices: set[int] = set()
        outer_bounds = [_subpath_bounds(indexed[0][1])]

        # Mark smaller subpaths that are contained within an outer boundary as holes
        for idx, subpath in indexed[1:]:
            sb = _subpath_bounds(subpath)
            if any(_bbox_contains(ob, sb) for ob in outer_bounds):
                hole_indices.add(idx)
            else:
                outer_bounds.append(sb)

        bg_color = None
        if hole_indices and output_elements is not None:
            bg_color = _find_background_color(output_elements)

        # Build outer-boundary elements first, then hole elements on top.
        # This ordering ensures holes render *above* the filled shape and
        # punch through to the background colour visually.
        outer_elements: list[dict[str, Any]] = []
        hole_elements: list[dict[str, Any]] = []

        for idx, subpath in enumerate(subpaths):
            if idx in hole_indices:
                # Hole subpath — fill with background colour to simulate a cutout.
                # Always emit as "line" (not ellipse) so render order is correct:
                # holes must render *after* the outer boundary to punch through.
                hole_style = dict(style)
                if bg_color:
                    hole_style["fill"] = bg_color
                else:
                    hole_style["fill"] = "transparent"

                elem = create_base_element("line", group_id, ids)
                apply_paint_style(elem, hole_style)
                finalized = finalize_linear_element(elem, subpath)
                if finalized is not None:
                    hole_elements.append(finalized)
            else:
                # Outer boundary subpath — normal fill.  Circle detection is
                # still useful here to produce cleaner shapes for standalone
                # circular subpaths.
                if is_circle_like(subpath):
                    outer_elements.append(
                        _convert_circle_like_subpath(subpath, style, group_id, ids)
                    )
                    continue

                elem = create_base_element("line", group_id, ids)
                apply_paint_style(elem, style)
                finalized = finalize_linear_element(elem, subpath)
                if finalized is not None:
                    outer_elements.append(finalized)

        return outer_elements + hole_elements

    # Default behaviour (nonzero fill-rule or single subpath)
    elements: list[dict[str, Any]] = []
    for subpath in subpaths:
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
        elem_style = inherit_style(node_style, element.attrib)
        # Pass *output* to _convert_path so it can look up background colours
        # for hole-punching when fill-rule="evenodd" is active.
        if tag == "path":
            new_elements = converters[tag](element.attrib, elem_style, group_id, ids, output)
        else:
            new_elements = converters[tag](element.attrib, elem_style, group_id, ids)
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
            "rect": lambda attrs, style, gid, ids, _o=None: _convert_rect(attrs, style, gid, ids),
            "circle": lambda attrs, style, gid, ids, _o=None: _convert_circle(attrs, style, gid, ids),
            "ellipse": lambda attrs, style, gid, ids, _o=None: _convert_ellipse(attrs, style, gid, ids),
            "path": lambda attrs, style, gid, ids, output=None: _convert_path(attrs, style, gid, ids, output),
            "line": lambda attrs, style, gid, ids, _o=None: _convert_line(attrs, style, gid, ids),
            "polygon": lambda attrs, style, gid, ids, _o=None: _convert_polygon_like(
                attrs, style, gid, ids, close_path=True
            ),
            "polyline": lambda attrs, style, gid, ids, _o=None: _convert_polygon_like(
                attrs, style, gid, ids, close_path=False
            ),
        })
    return SVG_CONVERTERS
