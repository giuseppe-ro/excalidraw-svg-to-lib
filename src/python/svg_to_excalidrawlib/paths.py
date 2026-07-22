from __future__ import annotations

from pathlib import Path

from svg_to_excalidrawlib.constants import SUPPORTED_ICON_EXTENSIONS


def is_supported_icon_file(file_path: str | Path) -> bool:
    return Path(file_path).suffix.lower() in SUPPORTED_ICON_EXTENSIONS


def collect_input_paths(inputs: list[str | Path]) -> list[Path]:
    collected: list[Path] = []

    for raw_input in inputs:
        resolved = Path(raw_input).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Input not found: {raw_input}")

        if resolved.is_dir():
            icon_files = sorted(
                (
                    resolved / entry.name
                    for entry in resolved.iterdir()
                    if entry.is_file() and is_supported_icon_file(entry.name)
                ),
                key=lambda path: path.name.lower(),
            )
            collected.extend(icon_files)
            continue

        if resolved.is_file():
            collected.append(resolved)
            continue

        raise ValueError(f"Not a file or directory: {raw_input}")

    return list(dict.fromkeys(collected))


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
