from __future__ import annotations

import time
from collections.abc import Callable
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET
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
from excalidraw_svg_to_lib.svg.utils import inherit_style, is_url_ref, local_name, parse_length


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
    # Translate SVG rx/ry to Excalidraw roundness (0 = sharp, 8 = pill-shaped)
    rx = parse_length(attributes.get("rx"))
    ry = parse_length(attributes.get("ry"), rx)  # ry defaults to rx per SVG spec
    if rx > 0 or ry > 0:
        # Map SVG radius to Excalidraw roundness value
        radius = rx or ry
        max_radius = min(width, height) / 2
        if max_radius > 0:
            element["roundness"] = {"type": 2, "value": min(radius / max_radius, 1.0)}
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


def _find_background_color(
    elements: list[dict[str, Any]],
    *,
    warnings: list[str] | None = None,
) -> str | None:
    """Scan previously-converted sibling elements for the largest solid-filled
    shape to use as the background colour for evenodd hole-punching.

    DFS traversal order usually places background ``<rect>`` elements before
    ``<path>`` elements, but this is not guaranteed.  When no solid-filled
    sibling is found a warning is emitted and *None* is returned.
    """
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
    if best is None and warnings is not None:
        warnings.append(
            "WARN: evenodd fill-rule used without a preceding solid-background "
            "element; holes may be invisible"
        )
    return best[1] if best else None


def _convert_path_evenodd(
    subpaths: list[list[Point]],
    style: dict[str, Any],
    fill: str,
    group_id: str,
    ids: IdGenerator,
    bg_color: str | None,
    *,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert path subpaths using the evenodd fill-rule by layering
    elements with alternating fill/background colours.

    See :func:`_convert_path` for a detailed explanation.
    """
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

    # Determine fill colour for each subpath by nesting depth
    fills: dict[int, str] = {}
    for pos, (orig_idx, _sp, _area, sb) in enumerate(indexed):
        if pos == 0:
            fills[orig_idx] = fill
        else:
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

    # Layer: bottom (canvas), middle (holes), top (restoration)
    bottom: list[dict[str, Any]] = []
    middle: list[dict[str, Any]] = []
    top: list[dict[str, Any]] = []

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
            bottom.append(finalized)
        elif colour == fill:
            top.append(finalized)
        else:
            middle.append(finalized)

    return bottom + middle + top


def _convert_path(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    output_elements: list[dict[str, Any]] | None = None,
    *,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    path_data = attributes.get("d")
    if not path_data:
        return []

    subpaths = path_commands_to_points(path_data)
    if not subpaths:
        return []

    fill_rule = style.get("fill_rule", "nonzero")
    fill = style.get("fill", "transparent")

    if fill_rule == "evenodd" and fill != "transparent" and len(subpaths) > 1:
        bg_color = None
        if output_elements is not None:
            bg_color = _find_background_color(output_elements)
        return _convert_path_evenodd(
            subpaths, style, fill, group_id, ids, bg_color,
        )

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


def _convert_text(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    element_text: str = "",
    *,
    tspans: list[Element] | None = None,
) -> list[dict[str, Any]]:
    """Convert an SVG ``<text>`` element to an Excalidraw text element.

    When *tspans* is provided, each ``<tspan>`` is appended as a separate
    text element positioned relative to the parent ``<text>``.
    """
    text_content = element_text.strip()
    has_tspans = tspans and len(tspans) > 0
    if not text_content and not has_tspans:
        return []

    elements: list[dict[str, Any]] = []

    if text_content:
        elements.append(_make_text_element(
            text_content, attributes, style, group_id, ids,
        ))

    if has_tspans:
        assert tspans is not None
        for ts in tspans:
            ts_text = (ts.text or "").strip()
            if not ts_text:
                continue
            ts_attribs = dict(attributes)
            ts_attribs.update(ts.attrib)
            # <tspan> x/y are relative to parent <text> when absent
            ts_style = inherit_style(style, ts.attrib)
            elem = _make_text_element(ts_text, ts_attribs, ts_style, group_id, ids)
            elements.append(elem)

    return elements


def _make_text_element(
    text_content: str,
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
) -> dict[str, Any]:
    """Build a single Excalidraw text element dict."""
    font_size = parse_length(attributes.get("font-size"), 12.0)
    x = parse_length(attributes.get("x"))
    y = parse_length(attributes.get("y"))

    element = create_base_element("text", group_id, ids)
    fill = style.get("fill", "#000000")
    if fill and fill != "transparent":
        element["strokeColor"] = fill
    element["backgroundColor"] = "transparent"
    element["opacity"] = style.get("opacity", 100)
    element.update({
        "x": x,
        "y": y - font_size,  # SVG y is baseline, Excalidraw y is top
        "width": 0,
        "height": 0,
        "text": text_content,
        "originalText": text_content,
        "fontSize": font_size,
        "fontFamily": 2,
        "textAlign": "left",
        "verticalAlign": "top",
        "autoResize": True,
        "lineHeight": 1.25,
        "updated": int(time.time() * 1000),
    })
    return element


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
    "text",
})


def _convert_use(
    attributes: dict[str, str],
    style: dict[str, Any],
    group_id: str,
    ids: IdGenerator,
    defs: dict[str, Element],
    *,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve a ``<use>`` element by looking up the referenced element and
    converting it with the use element's own x/y offset and styles applied.
    """
    href = attributes.get("href") or attributes.get("{http://www.w3.org/1999/xlink}href", "")
    if not href or not href.startswith("#"):
        return []
    ref_id = href[1:]
    ref_elem = defs.get(ref_id)
    if ref_elem is None:
        return []

    # Apply x/y offset from the <use> element (translate first, then any explicit transform)
    ox = parse_length(attributes.get("x"))
    oy = parse_length(attributes.get("y"))
    use_transform = parse_transform(attributes.get("transform", ""))
    if ox != 0 or oy != 0:
        translate = (1.0, 0.0, 0.0, 1.0, ox, oy)
        use_transform = compose(translate, use_transform) if use_transform else translate

    output: list[dict[str, Any]] = []
    # Recurse into the referenced element with the use element's transform
    _convert_element(ref_elem, style, use_transform or IDENTITY, group_id, ids, output,
                     defs=defs, warnings=warnings)
    return output


def _convert_element(
    element: Element,
    style: dict[str, Any],
    transform: Transform,
    group_id: str,
    ids: IdGenerator,
    output: list[dict[str, Any]],
    *,
    defs: dict[str, Element] | None = None,
    warnings: list[str] | None = None,
) -> None:
    """Recursively convert an SVG element and its children.

    Walks the SVG tree depth-first, converting recognised elements into
    Excalidraw element dicts and appending them to ``output``.  Unrecognised
    elements are skipped but their children are still traversed (unless the
    tag is in :data:`_NON_RENDERING`).

    When *warnings* is provided, non-fatal issues (unsupported features,
    missing references, etc.) are appended to it.
    """
    node_style = inherit_style(style, element.attrib)
    tag = local_name(element.tag)

    # Compose this element's transform into the accumulated transform
    raw_transform = element.attrib.get("transform")
    if raw_transform:
        parsed = parse_transform(raw_transform)
        current_transform = compose(transform, parsed) if parsed else transform
    else:
        current_transform = transform

    # Warn about gradient / pattern fills (unsupported — element gets no fill)
    if warnings is not None and is_url_ref(element.attrib.get("fill")):
        warnings.append(
            f"WARN: unsupported fill reference {element.attrib['fill']!r} "
            f"on <{tag}> — gradients/patterns are not supported"
        )

    if tag in _CONVERTERS:
        new_elements = _CONVERTERS[tag](element.attrib, node_style, group_id, ids)
    elif tag == "image":
        if warnings is not None:
            warnings.append(
                f"WARN: <image> elements are not supported "
                f"({element.attrib.get('href', element.attrib.get('{http://www.w3.org/1999/xlink}href', '?'))})"
            )
        new_elements = []
    elif tag == "path":
        new_elements = _convert_path(
            element.attrib, node_style, group_id, ids, output, warnings=warnings,
        )
    elif tag == "use":
        resolved_defs = defs or {}
        new_elements = _convert_use(element.attrib, node_style, group_id, ids, resolved_defs,
                                    warnings=warnings)
    elif tag == "text":
        # Collect <tspan> children
        text_children = [c for c in element if local_name(c.tag) == "tspan"]
        new_elements = _convert_text(
            element.attrib, node_style, group_id, ids,
            element_text=element.text or "",
            tspans=text_children if text_children else None,
        )
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
            _convert_element(
                child, node_style, current_transform, group_id, ids, output,
                defs=defs, warnings=warnings,
            )


# Registry of SVG tag → converter function (all have signature (attrs, style, gid, ids) -> list)
_CONVERTERS: dict[str, Callable[[dict[str, str], dict[str, Any], str, IdGenerator], list[dict[str, Any]]]] = {
    "rect": _convert_rect,
    "circle": _convert_circle,
    "ellipse": _convert_ellipse,
    "line": _convert_line,
    "polygon": _convert_polygon,
    "polyline": _convert_polyline,
}
