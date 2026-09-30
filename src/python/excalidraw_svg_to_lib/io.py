from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from excalidraw_svg_to_lib.constants import IGNORED_FILE_NAMES, SUPPORTED_ICON_EXTENSIONS


def is_supported_icon_file(file_path: str | Path) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_ICON_EXTENSIONS


def _is_ignored_file(name: str) -> bool:
    return name in IGNORED_FILE_NAMES or name.startswith(".")


def collect_input_paths(inputs: list[str | Path], *, warnings: list[str] | None = None) -> list[Path]:
    """Collect supported icon file paths from the given inputs.

    Directories are scanned recursively. Files on the silent-ignore list
    (dotfiles like .DS_Store, build artifacts) are skipped without warning.
    Other unsupported files are skipped, and at most one aggregated warning
    is emitted per directory.

    Individual unsupported files are skipped with their own warning.

    Args:
        inputs: File or directory paths to process.
        warnings: Optional list populated with warning messages for skipped files.

    Returns:
        Sorted, deduplicated list of supported icon file paths.
    """
    collected: list[Path] = []
    unsupported: list[str] = []

    for raw_input in inputs:
        resolved = Path(raw_input).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Input not found: {raw_input}")

        if resolved.is_dir():
            for entry in sorted(resolved.rglob("*")):
                if not entry.is_file():
                    continue
                if _is_ignored_file(entry.name):
                    continue
                if is_supported_icon_file(entry.name):
                    collected.append(entry)
                else:
                    unsupported.append(entry.name)
            continue

        if resolved.is_file():
            if _is_ignored_file(resolved.name):
                continue
            if is_supported_icon_file(resolved.name):
                collected.append(resolved)
            elif warnings is not None:
                warnings.append(f"WARN: skipping unsupported file {resolved.name!r}")
            continue

        raise ValueError(f"Not a file or directory: {raw_input}")

    if unsupported and warnings is not None:
        if len(unsupported) == 1:
            warnings.append(f"WARN: skipping unsupported file {unsupported[0]!r}")
        else:
            names = ", ".join(sorted(set(unsupported))[:5])
            more = f" and {len(set(unsupported)) - 5} more" if len(set(unsupported)) > 5 else ""
            warnings.append(
                f"WARN: skipping {len(unsupported)} unsupported file(s): {names}{more}"
            )

    return list(dict.fromkeys(sorted(collected, key=lambda p: p.name.lower())))


def default_output_path(raw_inputs: list[str | Path], resolved_inputs: list[Path]) -> str:
    if len(resolved_inputs) == 1:
        raw = str(raw_inputs[0])
        only_input = Path(raw_inputs[0]).resolve()
        if only_input.is_dir():
            if raw in {".", "./"}:
                return "icons.excalidrawlib"
            return f"{only_input.name}.excalidrawlib"
        return f"{resolved_inputs[0].stem}.excalidrawlib"

    return "icons.excalidrawlib"


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


def read_json(path: str | Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def write_library_file(
    library_file: dict[str, Any],
    output_path: str | Path,
) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"{json.dumps(library_file, indent=2)}\n", encoding="utf-8")
