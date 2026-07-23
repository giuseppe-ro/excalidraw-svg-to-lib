from __future__ import annotations

from pathlib import Path
from typing import Any

from excalidraw_svg_to_lib.constants import ICON_PADDING, DEFAULT_LABEL_GAP
from excalidraw_svg_to_lib.elements import (
    create_invisible_box_element,
    create_label_element,
    element_bounds,
    fit_elements_to_size,
    icon_group_id,
    normalize_elements,
    sort_elements,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.svg import svg_to_elements


def _apply_options(
    elements: list[dict[str, Any]],
    options: ConvertOptions,
) -> list[dict[str, Any]]:
    """Apply normalize and scale options to elements."""
    if options.normalize:
        elements = normalize_elements(elements)
    if options.scale_to_target:
        elements = fit_elements_to_size(elements, options.target_icon_size)
    return elements


def convert_svg_to_library(
    svg_content: str,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    """Convert raw SVG text into Excalidraw elements.

    Returns a dict with ``"elements"`` (sorted list of element dicts) and
    ``"view_box"`` (the parsed SVG viewBox).
    """
    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator()
    elements, view_box = svg_to_elements(svg_content, id_generator)
    elements = _apply_options(elements, resolved_options)

    return {
        "elements": sort_elements(elements),
        "view_box": view_box,
    }


def convert_input_to_library(
    input_path: str | Path,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    """Convert a single SVG file into a library payload.

    Adds a filename label when ``options.add_label`` is *True*.
    Returns ``icon_name`` derived from the filename stem for v2 naming.
    """
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {input_path}")
    if path.suffix.lower() != ".svg":
        raise ValueError(f"Unsupported file type '{path.suffix}'. Only .svg files are supported.")

    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator()
    result = convert_svg_to_library(path.read_text(encoding="utf-8"), resolved_options, id_generator)
    elements = result["elements"]
    icon_name = path.stem

    if resolved_options.add_label:
        bounds = element_bounds(elements)
        group_id = icon_group_id(elements)
        min_x, min_y, max_x, max_y = bounds

        invisible_box = create_invisible_box_element(bounds, id_generator, group_id)
        outer_box_x = min_x - ICON_PADDING
        outer_box_width = (max_x - min_x) + 2 * ICON_PADDING
        label_y = max_y + ICON_PADDING + DEFAULT_LABEL_GAP

        label = create_label_element(
            icon_name, outer_box_x, outer_box_width, label_y, id_generator, group_id
        )

        elements = [invisible_box] + elements + [label]
        elements = sort_elements(elements)

    return {
        "library": [elements],
        "icon_name": icon_name,
        "view_box": result["view_box"],
    }
