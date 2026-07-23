from __future__ import annotations

import argparse
import sys
from pathlib import Path

from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.io import collect_input_paths, resolve_output_path, write_library_file
from excalidraw_svg_to_lib.library import append_to_existing, make_library_file
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.runner import convert_input_to_library


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="excalidraw-svg-to-lib",
        description="Convert SVG files into an Excalidraw library (.excalidrawlib).",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="SVG files or directories containing .svg files",
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
    parser.add_argument(
        "--stroke-width",
        type=float,
        default=None,
        help=(
            "Uniform stroke width for all elements (overrides SVG stroke-width values). "
            "Default: 1"
        ),
    )
    parser.add_argument(
        "--v1",
        action="store_true",
        help="Use legacy v1 library format (default is v2 with searchable names)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    options = ConvertOptions(
        normalize=not args.no_normalize,
        add_label=not args.no_label,
        scale_to_target=not args.no_scale,
        target_icon_size=args.target_size,
        uniform_stroke_width=args.stroke_width,  # defaults to DEFAULT_STROKE_WIDTH in ConvertOptions
        format_version=1 if args.v1 else 2,
    )

    warnings: list[str] = []
    try:
        resolved_inputs = collect_input_paths(args.inputs, warnings=warnings)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    # Print warnings about skipped files (ANSI yellow — universal across shells)
    _YELLOW = "\033[33m"
    _RESET = "\033[0m"
    for warning in warnings:
        print(f"{_YELLOW}{warning}{_RESET}", file=sys.stderr)

    if not resolved_inputs:
        print("Error: no supported icon files to convert.", file=sys.stderr)
        raise SystemExit(1)

    if any(Path(raw_input).resolve().is_dir() for raw_input in args.inputs):
        print(f"Found {len(resolved_inputs)} icon file(s)", file=sys.stderr)

    library_items = []
    icon_names = []
    id_generator = IdGenerator()

    for input_path in resolved_inputs:
        try:
            converted = convert_input_to_library(input_path, options, ids=id_generator)
            library_items.append(converted["library"][0])
            icon_names.append(converted["icon_name"])
            print(
                f"Converted {input_path.name} -> {len(converted['library'][0])} element(s)",
                file=sys.stderr,
            )
        except (OSError, ValueError) as error:
            print(f"Error converting {input_path.name}: {error}", file=sys.stderr)
            raise SystemExit(1) from error

    if options.format_version == 2:
        named_items = list(zip(library_items, icon_names))
        library_file = make_library_file(named_items, format_version=2, ids=id_generator)
    else:
        library_file = make_library_file(library_items)

    append_path = Path(args.append) if args.append else None
    if append_path is not None:
        library_file = append_to_existing(library_file, append_path)

    output_path = resolve_output_path(args.inputs, resolved_inputs, args.output, args.append)
    write_library_file(library_file, output_path)
    items = library_file.get('libraryItems', library_file.get('library', []))
    print(
        f"Wrote {output_path} ({len(items)} library item(s))",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
