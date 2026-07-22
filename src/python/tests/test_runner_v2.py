"""Tests for v2 format in runner and CLI."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR

from excalidraw_svg_to_lib.cli import main
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.runner import (
    build_library_file,
    convert_input_to_library,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator


@pytest.fixture
def fixed_ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


@pytest.fixture
def fixed_options() -> ConvertOptions:
    return ConvertOptions(normalize=True, format_version=2)


class TestConvertInputV2:
    """``convert_input_to_library`` returns icon name for v2."""

    def test_returns_icon_name_from_filename(self, fixed_ids: IdGenerator) -> None:
        svg_path = FIXTURES_DIR / "simple_rect.svg"
        result = convert_input_to_library(svg_path, ids=fixed_ids)

        assert result["icon_name"] == "simple_rect"

    def test_v2_output_has_library_items(self, fixed_options: ConvertOptions, fixed_ids: IdGenerator) -> None:
        svg_path = FIXTURES_DIR / "simple_rect.svg"
        result = convert_input_to_library(svg_path, fixed_options, ids=fixed_ids)

        assert result["version"] == 2
        assert "libraryItems" in result
        assert len(result["libraryItems"]) == 1
        assert result["libraryItems"][0]["name"] == "simple_rect"

    def test_v2_item_has_published_status(self, fixed_options: ConvertOptions, fixed_ids: IdGenerator) -> None:
        svg_path = FIXTURES_DIR / "simple_rect.svg"
        result = convert_input_to_library(svg_path, fixed_options, ids=fixed_ids)

        assert result["libraryItems"][0]["status"] == "published"

    def test_v2_item_has_id(self, fixed_options: ConvertOptions, fixed_ids: IdGenerator) -> None:
        svg_path = FIXTURES_DIR / "simple_rect.svg"
        result = convert_input_to_library(svg_path, fixed_options, ids=fixed_ids)

        item = result["libraryItems"][0]
        assert "id" in item
        assert isinstance(item["id"], str)
        assert len(item["id"]) > 0


class TestBuildLibraryFileV2:
    """``build_library_file`` produces v2 format when configured."""

    def test_builds_v2_library(self, fixed_options: ConvertOptions) -> None:
        svg_path = FIXTURES_DIR / "simple_rect.svg"
        library = build_library_file([svg_path], fixed_options)

        assert library["version"] == 2
        assert "libraryItems" in library
        assert len(library["libraryItems"]) == 1
        assert library["libraryItems"][0]["name"] == "simple_rect"

    def test_builds_v2_library_from_directory(self, fixed_options: ConvertOptions) -> None:
        library = build_library_file([FIXTURES_DIR], fixed_options)

        assert library["version"] == 2
        assert len(library["libraryItems"]) >= 2
        names = {item["name"] for item in library["libraryItems"]}
        assert "simple_rect" in names
        assert "nested_icon" in names


class TestCLIv2:
    """CLI produces v2 format output by default."""

    def test_cli_produces_v2_format(self, tmp_path: Path, monkeypatch, capsys) -> None:
        output_path = tmp_path / "icons.excalidrawlib"

        monkeypatch.setattr(
            "sys.argv",
            ["excalidraw-svg-to-lib", str(FIXTURES_DIR), "-o", str(output_path)],
        )

        main()

        library = json.loads(output_path.read_text(encoding="utf-8"))
        assert library["version"] == 2
        assert "libraryItems" in library
        assert len(library["libraryItems"]) >= 2

        names = {item["name"] for item in library["libraryItems"]}
        assert {"simple_rect", "nested_icon"}.issubset(names)

    def test_cli_v1_flag_produces_v1_format(self, tmp_path: Path, monkeypatch) -> None:
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

    def test_cli_v2_items_have_searchable_names(self, tmp_path: Path, monkeypatch) -> None:
        output_path = tmp_path / "icons.excalidrawlib"

        monkeypatch.setattr(
            "sys.argv",
            ["excalidraw-svg-to-lib", str(FIXTURES_DIR), "-o", str(output_path)],
        )

        main()

        library = json.loads(output_path.read_text(encoding="utf-8"))
        for item in library["libraryItems"]:
            assert "name" in item
            assert isinstance(item["name"], str)
            assert len(item["name"]) > 0

    def test_cli_v2_items_have_elements_array(self, tmp_path: Path, monkeypatch) -> None:
        output_path = tmp_path / "icons.excalidrawlib"

        monkeypatch.setattr(
            "sys.argv",
            ["excalidraw-svg-to-lib", str(FIXTURES_DIR), "-o", str(output_path)],
        )

        main()

        library = json.loads(output_path.read_text(encoding="utf-8"))
        for item in library["libraryItems"]:
            assert isinstance(item["elements"], list)
            assert len(item["elements"]) > 0

    def test_cli_v2_no_label_still_has_name(self, tmp_path: Path, monkeypatch) -> None:
        output_path = tmp_path / "icons.excalidrawlib"

        monkeypatch.setattr(
            "sys.argv",
            ["excalidraw-svg-to-lib", str(FIXTURES_DIR), "-o", str(output_path), "--no-label"],
        )

        main()

        library = json.loads(output_path.read_text(encoding="utf-8"))
        for item in library["libraryItems"]:
            # Name is still present even without text label elements
            assert item["name"] in {"simple_rect", "nested_icon", "stroked_icon"}
            # No text elements in the icon shapes
            element_types = [e["type"] for e in item["elements"]]
            assert "text" not in element_types
