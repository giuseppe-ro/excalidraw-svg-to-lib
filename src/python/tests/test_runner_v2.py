"""Tests for runner v2 integration and CLI v1 flag."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR, SVG_DIR

from excalidraw_svg_to_lib.cli import main
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.runner import convert_input_to_library


def test_returns_icon_name_from_filename(fixed_ids) -> None:
    """convert_input_to_library returns icon_name derived from filename stem."""
    result = convert_input_to_library(FIXTURES_DIR / "simple_rect.svg", ids=fixed_ids)
    assert result["icon_name"] == "simple_rect"


def test_cli_v1_flag_produces_v1_format(tmp_path: Path, monkeypatch) -> None:
    """--v1 flag produces legacy v1 format."""
    output_path = tmp_path / "icons.excalidrawlib"
    monkeypatch.setattr(
        "sys.argv",
        ["excalidraw-svg-to-lib", str(FIXTURES_DIR), "-o", str(output_path), "--v1"],
    )
    main()

    library = json.loads(output_path.read_text(encoding="utf-8"))
    assert library["version"] == 1
    assert "library" in library
    assert "libraryItems" not in library


def test_converts_all_svg_in_repo_svg_directory() -> None:
    """Integration test: every SVG in the repo's svg/ directory converts
    successfully and produces at least one element.
    """
    if not SVG_DIR.is_dir():
        pytest.skip(f"SVG directory not found: {SVG_DIR}")

    svg_files = sorted(SVG_DIR.glob("*.svg"))
    if not svg_files:
        pytest.skip(f"No SVG files found in {SVG_DIR}")

    options = ConvertOptions()
    converted = 0
    for svg_path in svg_files:
        result = convert_input_to_library(svg_path, options)
        assert len(result["library"]) == 1
        assert len(result["library"][0]) >= 1, f"{svg_path.name} produced no elements"
        assert result["icon_name"] == svg_path.stem
        converted += 1

    assert converted == len(svg_files)
