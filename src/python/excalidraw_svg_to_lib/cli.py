from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from excalidraw_svg_to_lib.converter import (
    convert_input_to_library,
    resolve_output_path,
    write_library_file,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.paths import collect_input_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="excalidraw-svg-to-lib",
        description="Convert SVG or image files into an Excalidraw library (.excalidrawlib).",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Icon files or directories containing .svg / image files",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: derived from input name)",
    )
    parser.add_argument(
        "--append",
        help="Append converted icons to an existing .excalidrawlib file",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Keep original SVG coordinates instead of shifting to origin",
    )
    parser.add_argument(
        "--no-label",
        action="store_true",
        help="Skip adding filename labels below icons",
    )
    parser.add_argument(
        "--target-size",
        type=float,
        default=64,
        help="Scale icons so their largest dimension matches this size (default: 64)",
    )
    parser.add_argument(
        "--no-scale",
        action="store_true",
        help="Keep original icon dimensions instead of scaling to --target-size",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    options = ConvertOptions(
        normalize=not args.no_normalize,
        add_label=not args.no_label,
        scale_to_target=not args.no_scale,
        target_icon_size=args.target_size,
    )

    try:
        resolved_inputs = collect_input_paths(args.inputs)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    if not resolved_inputs:
        print("Error: no supported icon files to convert.", file=sys.stderr)
        raise SystemExit(1)

    if any(Path(raw_input).resolve().is_dir() for raw_input in args.inputs):
        print(f"Found {len(resolved_inputs)} icon file(s)", file=sys.stderr)

    library_items = []
    files = {}
    id_generator = IdGenerator(options)

    for input_path in resolved_inputs:
        try:
            converted = convert_input_to_library(input_path, options, ids=id_generator)
            library_items.append(converted["library"][0])
            files.update(converted.get("files", {}))
            print(
                f"Converted {input_path.name} -> {len(converted['library'][0])} element(s)",
                file=sys.stderr,
            )
        except (OSError, ValueError) as error:
            print(f"Error converting {input_path.name}: {error}", file=sys.stderr)
            raise SystemExit(1) from error

    library_file: dict[str, object] = {
        "type": "excalidrawlib",
        "version": 1,
        "library": library_items,
    }
    if files:
        library_file["files"] = files

    append_path = Path(args.append) if args.append else None
    if append_path is not None:
        existing = json.loads(append_path.read_text(encoding="utf-8"))
        if existing.get("type") != "excalidrawlib" or not isinstance(existing.get("library"), list):
            print(f"Error: Invalid library file: {append_path}", file=sys.stderr)
            raise SystemExit(1)

        library_file = {
            **existing,
            "library": [*existing["library"], *library_items],
            "files": {**(existing.get("files") or {}), **files},
        }

    output_path = resolve_output_path(args.inputs, resolved_inputs, args.output, args.append)
    write_library_file(library_file, output_path)
    print(
        f"Wrote {output_path} ({len(library_file['library'])} library item(s))",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
