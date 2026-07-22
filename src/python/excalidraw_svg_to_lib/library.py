from __future__ import annotations

from pathlib import Path
from typing import Any

from excalidraw_svg_to_lib.io import read_json, write_library_file


def make_library_file(
    library_items: list[list[dict[str, Any]]],
    files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    library_file: dict[str, Any] = {
        "type": "excalidrawlib",
        "version": 1,
        "library": library_items,
    }
    if files:
        library_file["files"] = files
    return library_file


def append_to_existing(
    library_file: dict[str, Any],
    append_path: str | Path,
) -> dict[str, Any]:
    existing = read_json(append_path)
    if existing.get("type") != "excalidrawlib" or not isinstance(existing.get("library"), list):
        raise ValueError(f"Invalid library file: {append_path}")

    return {
        **existing,
        "library": [*existing["library"], *library_file["library"]],
        "files": {**(existing.get("files") or {}), **library_file.get("files", {})},
    }
