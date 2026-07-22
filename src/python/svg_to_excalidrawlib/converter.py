from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image

from svg_to_excalidrawlib.constants import IMAGE_MIME_TYPES, SUPPORTED_IMAGE_EXTENSIONS
from svg_to_excalidrawlib.elements import (
    create_base_element,
    create_label_element,
    element_bounds,
    icon_group_id,
    normalize_elements,
    sort_elements,
)
from svg_to_excalidrawlib.id_generator import IdGenerator
from svg_to_excalidrawlib.options import ConvertOptions
from svg_to_excalidrawlib.paths import collect_input_paths, default_output_path
from svg_to_excalidrawlib.svg_parser import svg_to_elements


def generate_file_id(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def convert_svg_to_library(
    svg_content: str,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator(resolved_options)
    elements, view_box = svg_to_elements(svg_content, id_generator)

    if resolved_options.normalize:
        elements = normalize_elements(elements)

    return {
        "type": "excalidrawlib",
        "version": 1,
        "library": [sort_elements(elements)],
        "files": {},
        "metadata": {
            "source_view_box": view_box,
            "element_count": len(elements),
        },
    }


def convert_image_to_library(
    input_path: str | Path,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    path = Path(input_path)
    extension = path.suffix.lower()
    mime_type = IMAGE_MIME_TYPES.get(extension)
    if mime_type is None:
        raise ValueError(f"Unsupported image format: {extension}")

    data = path.read_bytes()
    with Image.open(path) as image:
        width, height = image.size

    if width <= 0 or height <= 0:
        raise ValueError(f"Could not read image dimensions from {path}")

    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator(resolved_options)
    file_id = generate_file_id(data)
    now = int(time.time() * 1000)
    data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"

    element = create_base_element("image", id_generator.random_id(), id_generator)
    element.update(
        {
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "strokeColor": "transparent",
            "backgroundColor": "transparent",
            "strokeSharpness": "round",
            "status": "saved",
            "fileId": file_id,
            "scale": [1, 1],
            "crop": None,
            "link": None,
            "locked": False,
            "updated": now,
        }
    )

    return {
        "type": "excalidrawlib",
        "version": 1,
        "library": [[element]],
        "files": {
            file_id: {
                "mimeType": mime_type,
                "id": file_id,
                "dataURL": data_url,
                "created": now,
                "lastRetrieved": now,
            }
        },
        "metadata": {
            "element_count": 1,
            "source_file": path.name,
        },
    }


def convert_input_to_library(
    input_path: str | Path,
    options: ConvertOptions | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    path = Path(input_path)
    extension = path.suffix.lower()
    resolved_options = options or ConvertOptions()
    id_generator = ids or IdGenerator(resolved_options)

    if extension == ".svg":
        converted = convert_svg_to_library(
            path.read_text(encoding="utf-8"),
            resolved_options,
            ids=id_generator,
        )
    elif extension in SUPPORTED_IMAGE_EXTENSIONS:
        converted = convert_image_to_library(path, resolved_options, ids=id_generator)
    else:
        raise ValueError(
            f"Unsupported file type {extension or '(no extension)'}. "
            "Use SVG or PNG/JPG/GIF/WebP images."
        )

    if resolved_options.add_label:
        elements = converted["library"][0]
        bounds = element_bounds(elements)
        group_id = icon_group_id(elements)
        elements.append(create_label_element(path.stem, bounds, id_generator, group_id))
        converted["library"][0] = sort_elements(elements)
        converted["metadata"]["element_count"] = len(converted["library"][0])

    return converted


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
    files: dict[str, Any] = {}
    id_generator = IdGenerator(options)

    for input_path in resolved_inputs:
        converted = convert_input_to_library(input_path, options, ids=id_generator)
        library_items.append(converted["library"][0])
        files.update(converted.get("files", {}))

    library_file: dict[str, Any] = {
        "type": "excalidrawlib",
        "version": 1,
        "library": library_items,
    }
    if files:
        library_file["files"] = files

    if append_path is not None:
        existing = json.loads(Path(append_path).read_text(encoding="utf-8"))
        if existing.get("type") != "excalidrawlib" or not isinstance(existing.get("library"), list):
            raise ValueError(f"Invalid library file: {append_path}")

        library_file = {
            **existing,
            "library": [*existing["library"], *library_items],
            "files": {**(existing.get("files") or {}), **files},
        }

    if output_path is not None:
        write_library_file(library_file, output_path)

    return library_file


def write_library_file(library_file: dict[str, Any], output_path: str | Path) -> None:
    payload = {
        key: value
        for key, value in library_file.items()
        if key != "metadata"
    }
    Path(output_path).write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def resolve_output_path(
    raw_inputs: list[str | Path],
    resolved_inputs: list[Path],
    output_path: str | Path | None,
    append_path: str | Path | None,
) -> Path:
    if output_path is not None:
        return Path(output_path)
    if append_path is not None:
        return Path(append_path)
    return Path(default_output_path(raw_inputs, resolved_inputs))
