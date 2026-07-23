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


def _subpath_bounds(points: list[Point]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _signed_area(points: list[Point]) -> float:
    """Compute signed area of a polygon via the shoelace formula.

    In screen coordinates (Y-down), a **positive** value indicates
    clockwise winding and a **negative** value counter-clockwise.
    """
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area * 0.5


def _bbox_contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _find_background_color(elements: list[dict[str, Any]]) -> str | None:
    """Scan existing output for the largest solid-filled rectangle."""
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

    # When fill-rule="evenodd", subpaths alternate the SVG fill between
    # the path's colour and transparent (showing the background).  We
    # approximate this by layering subpaths with alternating colours:
    #
    #   0 crossings → background  (green)  ← background rect
    #   1 crossing  → path fill   (white)  ← CCW subpath
    #   2 crossings → background  (green)  ← CW subpath (hole)
    #   3 crossings → path fill   (white)  ← CW subpath inside another CW
    #   … and so on.
    #
    # Subpaths are sorted largest-first and assigned a colour based on
    # their nesting depth.  Elements are emitted bottom-to-top so that
    # deeper layers render underneath shallower ones.
    if fill_rule == "evenodd" and fill != "transparent" and len(subpaths) > 1:
        bg_color = None
        if output_elements is not None:
            bg_color = _find_background_color(output_elements)

        # Pair each subpath with its winding sign and bounding box
        indexed: list[tuple[int, list[Point], float, tuple[float, float, float, float]]] = []
        for idx, sp in enumerate(subpaths):
            indexed.append((idx, sp, _signed_area(sp), _subpath_bounds(sp)))

        # Sort by bounding-box area descending (largest first)
        indexed.sort(
            key=lambda item: (
                (item[3][2] - item[3][0]) * (item[3][3] - item[3][1])
            ),
            reverse=True,
        )

        # Determine fill colour for each subpath by walking the nesting
        # hierarchy.  The first (largest) subpath toggles the background
        # to the path colour.  Each subsequent subpath that is contained
        # within any earlier subpath toggles again.  When a subpath is
        # nested inside *multiple* earlier subpaths we must use the
        # *innermost* (smallest) container to compute the correct
        # crossing depth.
        fills: dict[int, str] = {}
        for pos, (orig_idx, _sp, _area, sb) in enumerate(indexed):
            if pos == 0:
                fills[orig_idx] = fill
            else:
                # Find the *innermost* (smallest-area) containing subpath
                best_container: tuple[int, float] | None = None
                for earlier_pos in range(pos):
                    _, _, _, ob = indexed[earlier_pos]
                    if _bbox_contains(ob, sb):
                        ob_area = (ob[2] - ob[0]) * (ob[3] - ob[1])
                        if best_container is None or ob_area < best_container[1]:
                            best_container = (earlier_pos, ob_area)

                if best_container is not None:
                    earlier_idx = indexed[best_container[0]][0]
                    fills[orig_idx] = (
                        bg_color
                        if fills[earlier_idx] == fill and bg_color
                        else fill
                    )
                else:
                    fills[orig_idx] = fill

        # Emit every subpath as a "line" element (not ellipse) so that
        # all share the same z-sort order and array position controls
        # layering.  CCW/canvas subpaths first (bottom), holes next,
        # restoration patches last (top).
        bottom: list[dict[str, Any]] = []  # canvas / base shapes
        middle: list[dict[str, Any]] = []  # holes
        top: list[dict[str, Any]] = []     # restoration layers

        for orig_idx, sp, area_val, _sb in indexed:
            colour = fills.get(orig_idx, fill)
            sp_style = dict(style)
            sp_style["fill"] = colour

            elem = create_base_element("line", group_id, ids)
            apply_paint_style(elem, sp_style)
            finalized = finalize_linear_element(elem, sp)
            if finalized is None:
                continue

            if area_val < 0:
                # CCW = canvas → bottom layer
                bottom.append(finalized)
            elif colour == fill:
                # CW, path-colour = restoration → top layer
                top.append(finalized)
            else:
                # CW, bg-colour = hole → middle layer
                middle.append(finalized)

        return bottom + middle + top

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


def _convert_poly_points(
    attributes: dict[str, str],
    close_path: bool,
) -> list[Point]:
    """Parse SVG polygon/polyline points attribute into a list of (x, y) tuples."""
    raw_points = attributes.get("points", "").replace(",", " ").split()
    numbers = [float(value) for value in raw_points if value]
    points: list[Point] = [
        (numbers[index], numbers[index + 1]) for index in range(0, len(numbers) - 1, 2)
    ]
    if len(points) < 2:
        return []
    if close_path:
        points.append(points[0])
    return points


def _convert_polygon(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    points = _convert_poly_points(attributes, close_path=True)
    if not points:
        return []
    element = create_base_element("line", group_id, ids)
    apply_paint_style(element, style)
    finalized = finalize_linear_element(element, points)
    return [finalized] if finalized is not None else []


def _convert_polyline(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> list[dict[str, Any]]:
    points = _convert_poly_points(attributes, close_path=False)
    if not points:
        return []
    element = create_base_element("line", group_id, ids)
    apply_paint_style(element, style)
    finalized = finalize_linear_element(element, points)
    return [finalized] if finalized is not None else []


# SVG elements whose children should never be converted to visible output
_NON_RENDERING = frozenset({
    "defs",
    "clipPath",
    "mask",
    "pattern",
    "linearGradient",
    "radialGradient",
    "filter",
    "marker",
    "symbol",
    "style",
    "title",
    "desc",
    "metadata",
})


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

    elem_style = inherit_style(node_style, element.attrib)
    if tag in _CONVERTERS:
        new_elements = _CONVERTERS[tag](element.attrib, elem_style, group_id, ids)
    elif tag == "path":
        new_elements = _convert_path(element.attrib, elem_style, group_id, ids, output)
    else:
        new_elements = []
    # Apply accumulated transform to newly created elements
    if current_transform != IDENTITY:
        for elem in new_elements:
            apply_transform_to_element(current_transform, elem)
    output.extend(new_elements)

    # Do not recurse into non-rendering elements (defs, clipPath, masks, etc.)
    if tag not in _NON_RENDERING:
        for child in element:
            _convert_element(child, node_style, current_transform, group_id, ids, output)


# Registry of SVG tag → converter function (all have signature (attrs, style, gid, ids) -> list)
_CONVERTERS: dict[str, callable] = {
    "rect": _convert_rect,
    "circle": _convert_circle,
    "ellipse": _convert_ellipse,
    "line": _convert_line,
    "polygon": _convert_polygon,
    "polyline": _convert_polyline,
}
