from __future__ import annotations

import defusedxml.ElementTree as ET
from typing import Any

from excalidraw_svg_to_lib.constants import DEFAULT_FILL, DEFAULT_STROKE
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.svg.converters import _convert_element
from excalidraw_svg_to_lib.svg.transforms import IDENTITY
from excalidraw_svg_to_lib.svg.utils import inherit_style, local_name, parse_length


def _collect_defs(root: ET.Element) -> dict[str, ET.Element]:
    """Walk the SVG tree and collect all elements with an ``id`` attribute.

    These are used to resolve ``<use href="#id">`` references.
    """
    defs: dict[str, ET.Element] = {}

    def _walk(element: ET.Element) -> None:
        elem_id = element.attrib.get("id")
        if elem_id:
            defs[elem_id] = element
        for child in element:
            _walk(child)

    _walk(root)
    return defs


def parse_view_box(svg_element: ET.Element) -> dict[str, float]:
    view_box = svg_element.get("viewBox")
    if view_box:
        parts = [float(part) for part in view_box.replace(",", " ").split()]
        x, y, width, height = parts
        return {"x": x, "y": y, "width": width, "height": height}

    width = parse_length(svg_element.get("width"), 64.0)
    height = parse_length(svg_element.get("height"), 64.0)
    return {"x": 0.0, "y": 0.0, "width": width, "height": height}


def svg_to_elements(svg_content: str, ids: IdGenerator) -> tuple[list[dict[str, Any]], dict[str, float]]:
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid SVG: {exc}") from exc
    if local_name(root.tag) != "svg":
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
            "fill_rule": "nonzero",
        },
        root.attrib,
    )

    defs = _collect_defs(root)
    _convert_element(root, root_style, IDENTITY, group_id, ids, elements, defs=defs)
    return elements, view_box
