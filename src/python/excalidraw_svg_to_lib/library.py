from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.io import read_json


def make_v2_item(
    elements: list[dict[str, Any]],
    name: str,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    """Create a single v2 library item dict."""
    gen = ids or IdGenerator()
    return {
        "id": gen.random_id(),
        "status": "published",
        "name": name,
        "elements": elements,
        "created": int(time.time() * 1000),
    }


# ---------------------------------------------------------------------------
# Library file builders
# ---------------------------------------------------------------------------


def make_library_file(
    items: list[list[dict[str, Any]]] | list[tuple[list[dict[str, Any]], str]],
    files: dict[str, Any] | None = None,
    *,
    format_version: int = 1,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    """Build an Excalidraw library file payload."""
    if format_version == 2:
        return _make_v2_file(items, files, ids)
    return _make_v1_file(items, files)


def _make_v1_file(
    items: list[list[dict[str, Any]]] | list[tuple[list[dict[str, Any]], str]],
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    library_file: dict[str, Any] = {
        "type": "excalidrawlib",
        "version": 1,
        "library": [item if isinstance(item, list) else item[0] for item in items],
    }
    if files:
        library_file["files"] = files
    return library_file


def _make_v2_file(
    items: list[list[dict[str, Any]]] | list[tuple[list[dict[str, Any]], str]],
    files: dict[str, Any] | None = None,
    ids: IdGenerator | None = None,
) -> dict[str, Any]:
    library_items: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, tuple):
            elements, name = item
        else:
            elements, name = item, ""
        library_items.append(make_v2_item(elements, name, ids))

    library_file: dict[str, Any] = {
        "type": "excalidrawlib",
        "version": 2,
        "source": "https://excalidraw.com",
        "libraryItems": library_items,
    }
    if files:
        library_file["files"] = files
    return library_file


# ---------------------------------------------------------------------------
# Append
# ---------------------------------------------------------------------------


def _get_library_items(
    data: dict[str, Any],
) -> tuple[str, list]:
    """Return ``(key, items)`` for whichever library format is present."""
    if "libraryItems" in data and isinstance(data["libraryItems"], list):
        return "libraryItems", data["libraryItems"]
    if "library" in data and isinstance(data["library"], list):
        return "library", data["library"]
    raise ValueError("Invalid library file: missing 'library' or 'libraryItems' key")


def append_to_existing(
    library_file: dict[str, Any],
    append_path: str | Path,
) -> dict[str, Any]:
    """Append new library items to an existing library file.

    Supports both v1 (``library``) and v2 (``libraryItems``) formats.
    """
    existing = read_json(append_path)
    if existing.get("type") != "excalidrawlib":
        raise ValueError(f"Invalid library file: {append_path}")

    # Determine which key to use in the existing file
    existing_key, existing_items = _get_library_items(existing)

    # Determine which items to append from the new file
    if "libraryItems" in library_file:
        new_items = library_file["libraryItems"]
        target_key = "libraryItems"
    elif "library" in library_file:
        new_items = library_file["library"]
        target_key = "library"
    else:
        raise ValueError("New library file has no 'library' or 'libraryItems' key")

    merged_items = list(existing_items) + list(new_items)

    result: dict[str, Any] = {
        **existing,
        existing_key: merged_items,
    }

    # If the new items use a different key than the existing file,
    # also set that key so the result has both formats
    if target_key != existing_key:
        result[target_key] = merged_items

    # Merge files
    result["files"] = {**(existing.get("files") or {}), **(library_file.get("files") or {})}

    # Remove files key if empty
    if not result["files"]:
        del result["files"]

    return result
