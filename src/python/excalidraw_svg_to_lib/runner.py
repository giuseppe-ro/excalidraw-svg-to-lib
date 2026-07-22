from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable

from excalidraw_svg_to_lib.elements import (
    create_label_element,
    element_bounds,
    fit_elements_to_size,
    icon_group_id,
    normalize_elements,
    sort_elements,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.io import collect_input_paths, resolve_output_path, write_library_file
from excalidraw_svg_to_lib.library import make_library_file
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.svg import svg_to_elements


# ---------------------------------------------------------------------------
# File-converter registry (OCP — new formats register without modifying this)
# ---------------------------------------------------------------------------

FileConverter = Callable[[Path, ConvertOptions, IdGenerator], dict[str, Any]]

_FILE_CONVERTERS: dict[str, FileConverter] = {}


def register_converter(extension: str, converter: FileConverter) -> None:
    """Register a converter for a file extension (e.g. ``'.svg'``)."""
    _FILE_CONVERTERS[extension] = converter


def _lookup_converter(extension: str) -> FileConverter | None:
    return _FILE_CONVERTERS.get(extension)


# ---------------------------------------------------------------------------
# Built-in converters
# ---------------------------------------------------------------------------


def _convert_svg(path: Path, options: ConvertOptions, ids: IdGenerator) -> dict[str, Any]:
    elements, view_box = svg_to_elements(path.read_text(encoding="utf-8"), ids)

    if options.normalize:
        elements = normalize_elements(elements)

    if options.scale_to_target:
        elements = fit_elements_to_size(elements, options.target_icon_size)

    return {
        "library": [sort_elements(elements)],
        "files": {},
        "view_box": view_box,
    }


# Register built-in converter at import time
register_converter(".svg", _convert_svg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_svg_to_library(
    svg_content: str,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    """Convert raw SVG text into a library payload (no label added)."""
    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator()
    elements, view_box = svg_to_elements(svg_content, id_generator)

    if resolved_options.normalize:
        elements = normalize_elements(elements)

    if resolved_options.scale_to_target:
        elements = fit_elements_to_size(elements, resolved_options.target_icon_size)

    return {
        "type": "excalidrawlib",
        "version": resolved_options.format_version,
        "library": [sort_elements(elements)],
        "files": {},
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
    extension = path.suffix.lower()
    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator()

    converter = _lookup_converter(extension)
    if converter is None:
        raise ValueError(
            f"Unsupported file type {extension or '(no extension)'}. "
            "Only .svg files are supported."
        )

    result = converter(path, resolved_options, id_generator)

    icon_name = path.stem

    if resolved_options.add_label:
        elements = result["library"][0]
        bounds = element_bounds(elements)
        group_id = icon_group_id(elements)
        elements.append(create_label_element(icon_name, bounds, id_generator, group_id))
        result["library"][0] = sort_elements(elements)

    return {
        "type": "excalidrawlib",
        "version": resolved_options.format_version,
        "library": result["library"],
        "libraryItems": _build_v2_items(result["library"], [icon_name], resolved_options.format_version),
        "files": result.get("files", {}),
        "icon_name": icon_name,
    }


def _build_v2_items(
    element_lists: list[list[dict[str, Any]]],
    names: list[str],
    format_version: int,
) -> list[dict[str, Any]]:
    """Build v2 libraryItems from element lists and names."""
    from excalidraw_svg_to_lib.library import make_v2_item

    if format_version != 2:
        return []

    items = []
    for elements, name in zip(element_lists, names):
        items.append(make_v2_item(elements, name))
    return items


def build_library_file(
    input_paths: list[str | Path],
    options: ConvertOptions | None = None,
    append_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_inputs = collect_input_paths(input_paths)
    if not resolved_inputs:
        raise ValueError("No supported icon files to convert.")

    library_items: list[list[dict[str, Any]]] = []
    icon_names: list[str] = []
    files: dict[str, Any] = {}
    id_generator = IdGenerator()

    for input_path in resolved_inputs:
        converted = convert_input_to_library(input_path, options, ids=id_generator)
        library_items.append(converted["library"][0])
        icon_names.append(converted["icon_name"])
        files.update(converted.get("files", {}))

    resolved_options = options or ConvertOptions()

    if resolved_options.format_version == 2:
        named_items = list(zip(library_items, icon_names))
        library_file = make_library_file(named_items, files or None, format_version=2)
    else:
        library_file = make_library_file(library_items, files or None, format_version=1)

    if append_path is not None:
        from excalidraw_svg_to_lib.library import append_to_existing

        library_file = append_to_existing(library_file, append_path)

    if output_path is not None:
        write_library_file(library_file, output_path)

    return library_file
