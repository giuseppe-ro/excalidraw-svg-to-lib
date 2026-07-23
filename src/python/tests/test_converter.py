from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.conftest import FIXTURES_DIR, SVG_DIR

from excalidraw_svg_to_lib.constants import (
    DEFAULT_LABEL_GAP,
    DEFAULT_TARGET_ICON_SIZE,
    ICON_PADDING,
)
from excalidraw_svg_to_lib.library import make_library_file, append_to_existing
from excalidraw_svg_to_lib.runner import (
    convert_input_to_library,
    convert_svg_to_library,
)
from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.elements import element_bounds


@pytest.fixture
def fixed_options() -> ConvertOptions:
    return ConvertOptions(normalize=True, format_version=1)


@pytest.fixture
def fixed_ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_rect_svg(fixtures_dir: Path) -> str:
    return (fixtures_dir / "simple_rect.svg").read_text(encoding="utf-8")


@pytest.fixture
def nested_icon_svg(fixtures_dir: Path) -> str:
    return (fixtures_dir / "nested_icon.svg").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Core pipeline — SVG → elements → library
# ---------------------------------------------------------------------------


class TestSvgConversion:
    def test_converts_simple_rectangle(
        self, simple_rect_svg: str, fixed_options: ConvertOptions, fixed_ids: IdGenerator
    ) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options, ids=fixed_ids)

        assert result["type"] == "excalidrawlib"
        assert result["version"] == 1
        assert len(result["library"]) == 1

        elements = result["library"][0]
        assert len(elements) == 1
        rectangle = elements[0]
        assert rectangle["type"] == "rectangle"
        assert rectangle["backgroundColor"] == "#ff0000"
        assert rectangle["width"] == pytest.approx(64.0)
        assert rectangle["height"] == pytest.approx(44.8)
        assert rectangle["x"] == 0
        assert rectangle["y"] == 0

    def test_normalizes_elements_to_origin(
        self, simple_rect_svg: str, fixed_options: ConvertOptions, fixed_ids: IdGenerator
    ) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options, ids=fixed_ids)
        rectangle = result["library"][0][0]
        assert rectangle["x"] == 0
        assert rectangle["y"] == 0

        unnormalized_options = ConvertOptions(normalize=False, scale_to_target=False)
        unnormalized = convert_svg_to_library(
            simple_rect_svg, unnormalized_options, ids=IdGenerator(rng=random.Random(42))
        )
        raw_rectangle = unnormalized["library"][0][0]
        assert raw_rectangle["x"] == 4
        assert raw_rectangle["y"] == 6

    def test_converts_nested_groups(
        self, nested_icon_svg: str, fixed_options: ConvertOptions, fixed_ids: IdGenerator
    ) -> None:
        result = convert_svg_to_library(nested_icon_svg, fixed_options, ids=fixed_ids)
        elements = result["library"][0]
        types = [element["type"] for element in elements]

        assert types[0] == "rectangle"
        assert "ellipse" in types
        assert elements[0]["backgroundColor"] == "#E7157B"

    def test_rejects_invalid_svg(
        self, fixed_options: ConvertOptions, fixed_ids: IdGenerator
    ) -> None:
        with pytest.raises(ValueError, match="missing <svg>"):
            convert_svg_to_library("<root></root>", fixed_options, ids=fixed_ids)

    def test_complex_icon_has_expected_structure(
        self, fixed_options: ConvertOptions, fixed_ids: IdGenerator,
    ) -> None:
        sns_path = SVG_DIR / "sns.svg"
        if not sns_path.exists():
            pytest.skip("AWS SNS fixture not available")

        result = convert_input_to_library(sns_path, fixed_options, ids=fixed_ids)
        elements = result["library"][0]
        types = [element["type"] for element in elements]

        # First element is the invisible outer box, icon elements start at index 1
        assert types[0] == "rectangle"  # invisible box
        # Circle-like hole subpaths are now emitted as "line" (not "ellipse")
        # to maintain correct z-ordering for evenodd hole-punching.
        assert types.count("line") >= 1
        assert types[-1] == "text"
        assert elements[1]["backgroundColor"] == "#E7157B"


# ---------------------------------------------------------------------------
# Labels — filename text added below icons
# ---------------------------------------------------------------------------


class TestLabelConversion:
    def test_adds_filename_label_to_svg(
        self, fixed_options: ConvertOptions, fixed_ids: IdGenerator,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options, ids=fixed_ids)
        elements = result["library"][0]
        text = elements[-1]

        assert text["type"] == "text"
        assert text["text"] == "lambda"

    def test_label_is_centered_below_icon(
        self, fixed_options: ConvertOptions, fixed_ids: IdGenerator,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options, ids=fixed_ids)
        shapes = [
            element
            for element in result["library"][0][1:]
            if element["type"] != "text"
        ]
        text = result["library"][0][-1]

        icon_width = max(element["x"] + element["width"] for element in shapes)
        icon_height = max(element["y"] + element["height"] for element in shapes)

        assert text["y"] == icon_height + ICON_PADDING + DEFAULT_LABEL_GAP
        assert text["x"] + text["width"] / 2 == pytest.approx(icon_width / 2, abs=0.01)

    def test_scales_icon_to_target_size(
        self, fixed_options: ConvertOptions, fixed_ids: IdGenerator,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options, ids=fixed_ids)
        shapes = [
            element
            for element in result["library"][0][1:]
            if element["type"] != "text"
        ]

        _, _, max_x, max_y = element_bounds(shapes)
        assert max(max_x, max_y) == pytest.approx(DEFAULT_TARGET_ICON_SIZE, abs=0.01)

    def test_svg_conversion_without_input_path_has_no_label(
        self, simple_rect_svg: str, fixed_options: ConvertOptions, fixed_ids: IdGenerator
    ) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options, ids=fixed_ids)
        types = [element["type"] for element in result["library"][0]]
        assert "text" not in types

    def test_skips_label_when_disabled(
        self, fixed_ids: IdGenerator,
    ) -> None:
        options = ConvertOptions(add_label=False)
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")
        result = convert_input_to_library(lambda_path, options, ids=fixed_ids)
        types = [element["type"] for element in result["library"][0]]
        assert "text" not in types


# ---------------------------------------------------------------------------
# Library builder — multiple inputs, append, output
# ---------------------------------------------------------------------------


class TestLibraryBuilder:
    def test_builds_library_from_multiple_inputs(
        self, fixtures_dir: Path, fixed_options: ConvertOptions,
    ) -> None:
        svg_path_a = fixtures_dir / "simple_rect.svg"
        svg_path_b = fixtures_dir / "nested_icon.svg"

        library_items = []
        for path in [svg_path_a, svg_path_b]:
            converted = convert_input_to_library(path, fixed_options)
            library_items.append(converted["library"][0])

        library = make_library_file(library_items, format_version=1)

        assert library["type"] == "excalidrawlib"
        assert len(library["library"]) == 2

    def test_appends_to_existing_library(
        self, fixtures_dir: Path, tmp_path: Path, fixed_options: ConvertOptions,
    ) -> None:
        existing_path = tmp_path / "existing.excalidrawlib"
        existing_path.write_text(
            '{"type":"excalidrawlib","version":1,'
            '"library":[[{"type":"rectangle",'
            '"x":0,"y":0,"width":1,"height":1}]]}\n',
            encoding="utf-8",
        )

        converted = convert_input_to_library(fixtures_dir / "simple_rect.svg", fixed_options)
        library = make_library_file([converted["library"][0]], format_version=1)
        library = append_to_existing(library, existing_path)

        assert len(library["library"]) == 2
