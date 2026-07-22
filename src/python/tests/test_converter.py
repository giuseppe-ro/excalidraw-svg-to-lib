from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tests.conftest import FIXTURES_DIR, SVG_DIR

from excalidraw_svg_to_lib.constants import (
    DEFAULT_LABEL_FONT_SIZE,
    DEFAULT_LABEL_GAP,
    DEFAULT_TARGET_ICON_SIZE,
    SUPPORTED_ICON_EXTENSIONS,
)
from excalidraw_svg_to_lib.converter import (
    build_library_file,
    convert_image_to_library,
    convert_input_to_library,
    convert_svg_to_library,
)
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.elements import (
    element_bounds,
    fit_elements_to_size,
    is_circle_like,
    normalize_elements,
    scale_elements,
    sort_elements,
)
from excalidraw_svg_to_lib.paths import (
    collect_input_paths,
    default_output_path,
    is_supported_icon_file,
)


@pytest.fixture
def fixed_options() -> ConvertOptions:
    counter = {"value": 0}

    def next_id() -> str:
        counter["value"] += 1
        return f"fixed-id-{counter['value']:03d}"

    def next_int() -> int:
        counter["value"] += 1
        return counter["value"]

    return ConvertOptions(
        normalize=True,
        id_factory=next_id,
        int_factory=next_int,
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_rect_svg(fixtures_dir: Path) -> str:
    return (fixtures_dir / "simple_rect.svg").read_text(encoding="utf-8")


@pytest.fixture
def nested_icon_svg(fixtures_dir: Path) -> str:
    return (fixtures_dir / "nested_icon.svg").read_text(encoding="utf-8")


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (16, 12), color="#336699").save(image_path, format="PNG")
    return image_path


class TestSupportedFiles:
    @pytest.mark.parametrize(
        "filename",
        [".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"],
    )
    def test_supported_icon_extensions(self, filename: str) -> None:
        assert is_supported_icon_file(f"icon{filename}")

    def test_rejects_unknown_extensions(self) -> None:
        assert not is_supported_icon_file("readme.txt")


class TestPathCollection:
    def test_collects_files_from_directory(self, fixtures_dir: Path) -> None:
        paths = collect_input_paths([fixtures_dir])
        names = [path.name for path in paths]
        assert names == sorted(names, key=str.lower)
        assert "simple_rect.svg" in names
        assert "nested_icon.svg" in names

    def test_collects_explicit_files(self, fixtures_dir: Path) -> None:
        icon = fixtures_dir / "simple_rect.svg"
        paths = collect_input_paths([icon])
        assert paths == [icon.resolve()]

    def test_raises_for_missing_input(self) -> None:
        with pytest.raises(FileNotFoundError):
            collect_input_paths(["missing.svg"])

    def test_default_output_for_directory(self, fixtures_dir: Path) -> None:
        assert default_output_path([fixtures_dir], [fixtures_dir / "a.svg"]) == (
            f"{fixtures_dir.name}.excalidrawlib"
        )

    def test_default_output_for_current_directory(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert default_output_path(["."], [tmp_path / "a.svg"]) == "icons.excalidrawlib"


class TestSvgConversion:
    def test_converts_simple_rectangle(self, simple_rect_svg: str, fixed_options: ConvertOptions) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options)

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

    def test_normalizes_elements_to_origin(self, simple_rect_svg: str, fixed_options: ConvertOptions) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options)
        rectangle = result["library"][0][0]
        assert rectangle["x"] == 0
        assert rectangle["y"] == 0

        options = ConvertOptions(
            normalize=False,
            scale_to_target=False,
            id_factory=fixed_options.id_factory,
            int_factory=fixed_options.int_factory,
        )
        unnormalized = convert_svg_to_library(simple_rect_svg, options)
        raw_rectangle = unnormalized["library"][0][0]
        assert raw_rectangle["x"] == 4
        assert raw_rectangle["y"] == 6

    def test_converts_nested_groups(self, nested_icon_svg: str, fixed_options: ConvertOptions) -> None:
        result = convert_svg_to_library(nested_icon_svg, fixed_options)
        elements = result["library"][0]
        types = [element["type"] for element in elements]

        assert types[0] == "rectangle"
        assert "ellipse" in types
        assert elements[0]["backgroundColor"] == "#E7157B"

    def test_rejects_invalid_svg(self, fixed_options: ConvertOptions) -> None:
        with pytest.raises(ValueError, match="missing <svg>"):
            convert_svg_to_library("<root></root>", fixed_options)

    def test_aws_sns_icon_has_expected_structure(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        sns_path = SVG_DIR / "sns.svg"
        if not sns_path.exists():
            pytest.skip("AWS SNS fixture not available")

        result = convert_input_to_library(sns_path, fixed_options)
        elements = result["library"][0]
        types = [element["type"] for element in elements]

        assert types[0] == "rectangle"
        assert types.count("ellipse") >= 1
        assert types.count("line") >= 1
        assert types[-1] == "text"
        assert elements[0]["backgroundColor"] == "#E7157B"


class TestLabelConversion:
    def test_adds_filename_label_to_svg(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options)
        elements = result["library"][0]
        text = elements[-1]

        assert text["type"] == "text"
        assert text["text"] == "lambda"
        assert text["originalText"] == "lambda"
        assert text["textAlign"] == "center"
        assert text["fontSize"] == DEFAULT_LABEL_FONT_SIZE
        assert text["fontFamily"] == 2

    def test_label_is_centered_below_icon(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options)
        shapes = [element for element in result["library"][0] if element["type"] != "text"]
        text = result["library"][0][-1]

        icon_width = max(element["x"] + element["width"] for element in shapes)
        icon_height = max(element["y"] + element["height"] for element in shapes)

        assert text["y"] == icon_height + DEFAULT_LABEL_GAP
        assert text["x"] + text["width"] / 2 == pytest.approx(icon_width / 2, abs=0.01)

    def test_scales_lambda_icon_to_target_size(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        lambda_path = SVG_DIR / "lambda.svg"
        if not lambda_path.exists():
            pytest.skip("lambda.svg fixture not available")

        result = convert_input_to_library(lambda_path, fixed_options)
        shapes = [element for element in result["library"][0] if element["type"] != "text"]
        text = result["library"][0][-1]

        _, _, max_x, max_y = element_bounds(shapes)
        assert max(max_x, max_y) == pytest.approx(DEFAULT_TARGET_ICON_SIZE, abs=0.01)
        assert text["y"] == pytest.approx(DEFAULT_TARGET_ICON_SIZE + DEFAULT_LABEL_GAP, abs=0.01)

    def test_scales_spaceship_icon_to_target_size(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        spaceship_path = SVG_DIR / "spaceship.svg"
        if not spaceship_path.exists():
            pytest.skip("spaceship.svg fixture not available")

        result = convert_input_to_library(spaceship_path, fixed_options)
        shapes = [element for element in result["library"][0] if element["type"] != "text"]
        text = result["library"][0][-1]

        _, _, max_x, max_y = element_bounds(shapes)
        icon_width = max_x
        icon_height = max_y

        assert max(icon_width, icon_height) == pytest.approx(DEFAULT_TARGET_ICON_SIZE, abs=0.01)
        assert text["y"] == pytest.approx(icon_height + DEFAULT_LABEL_GAP, abs=0.01)
        assert text["x"] + text["width"] / 2 == pytest.approx(icon_width / 2, abs=0.01)

    def test_sns_icon_stays_at_target_size(
        self,
        fixed_options: ConvertOptions,
    ) -> None:
        sns_path = SVG_DIR / "sns.svg"
        if not sns_path.exists():
            pytest.skip("sns.svg fixture not available")

        result = convert_input_to_library(sns_path, fixed_options)
        shapes = [element for element in result["library"][0] if element["type"] != "text"]

        _, _, max_x, max_y = element_bounds(shapes)
        assert max(max_x, max_y) == pytest.approx(DEFAULT_TARGET_ICON_SIZE, abs=0.01)
        assert shapes[0]["width"] == pytest.approx(DEFAULT_TARGET_ICON_SIZE)
        assert shapes[0]["height"] == pytest.approx(DEFAULT_TARGET_ICON_SIZE)

    def test_svg_conversion_without_input_path_has_no_label(
        self,
        simple_rect_svg: str,
        fixed_options: ConvertOptions,
    ) -> None:
        result = convert_svg_to_library(simple_rect_svg, fixed_options)
        types = [element["type"] for element in result["library"][0]]

        assert "text" not in types

    def test_adds_filename_label_to_image(
        self,
        sample_png: Path,
        fixed_options: ConvertOptions,
    ) -> None:
        result = convert_input_to_library(sample_png, fixed_options)
        text = result["library"][0][-1]

        assert text["type"] == "text"
        assert text["text"] == "sample"

    def test_label_is_grouped_with_icon_shapes(
        self,
        sample_png: Path,
        fixed_options: ConvertOptions,
    ) -> None:
        result = convert_input_to_library(sample_png, fixed_options)
        elements = result["library"][0]
        image = elements[0]
        text = elements[-1]

        assert image["type"] == "image"
        assert text["type"] == "text"
        assert text["groupIds"] == image["groupIds"]

    def test_skips_label_when_disabled(
        self,
        sample_png: Path,
        fixed_options: ConvertOptions,
    ) -> None:
        options = ConvertOptions(
            normalize=fixed_options.normalize,
            add_label=False,
            id_factory=fixed_options.id_factory,
            int_factory=fixed_options.int_factory,
        )
        result = convert_input_to_library(sample_png, options)
        types = [element["type"] for element in result["library"][0]]

        assert "text" not in types


class TestImageConversion:
    def test_converts_png_to_image_element(self, sample_png: Path, fixed_options: ConvertOptions) -> None:
        result = convert_image_to_library(sample_png, fixed_options)
        element = result["library"][0][0]

        assert element["type"] == "image"
        assert element["width"] == pytest.approx(64.0)
        assert element["height"] == pytest.approx(48.0)
        assert element["status"] == "saved"
        assert element["fileId"] in result["files"]

        file_data = result["files"][element["fileId"]]
        assert file_data["mimeType"] == "image/png"
        assert file_data["dataURL"].startswith("data:image/png;base64,")


class TestLibraryBuilder:
    def test_builds_library_from_multiple_inputs(
        self,
        fixtures_dir: Path,
        sample_png: Path,
        fixed_options: ConvertOptions,
    ) -> None:
        svg_path = fixtures_dir / "simple_rect.svg"
        library = build_library_file([svg_path, sample_png], fixed_options)

        assert library["type"] == "excalidrawlib"
        assert len(library["library"]) == 2
        assert "files" in library
        assert len(library["files"]) == 1

    def test_appends_to_existing_library(
        self,
        fixtures_dir: Path,
        tmp_path: Path,
        fixed_options: ConvertOptions,
    ) -> None:
        existing_path = tmp_path / "existing.excalidrawlib"
        existing_path.write_text(
            '{"type":"excalidrawlib","version":1,"library":[[{"type":"rectangle","x":0,"y":0,"width":1,"height":1}]]}\n',
            encoding="utf-8",
        )

        library = build_library_file(
            [fixtures_dir / "simple_rect.svg"],
            fixed_options,
            append_path=existing_path,
        )

        assert len(library["library"]) == 2


class TestElementHelpers:
    def test_sort_elements_by_type(self) -> None:
        elements = [
            {"type": "text"},
            {"type": "line"},
            {"type": "rectangle"},
            {"type": "ellipse"},
        ]
        sorted_elements = sort_elements(elements)
        assert [element["type"] for element in sorted_elements] == [
            "rectangle",
            "ellipse",
            "line",
            "text",
        ]

    def test_normalize_elements(self) -> None:
        elements = [
            {"x": 10, "y": 20},
            {"x": 15, "y": 25},
        ]
        normalize_elements(elements)
        assert elements[0]["x"] == 0
        assert elements[0]["y"] == 0
        assert elements[1]["x"] == 5
        assert elements[1]["y"] == 5

    def test_scale_elements(self) -> None:
        elements = [
            {
                "type": "rectangle",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 10,
                "strokeWidth": 2,
            },
            {
                "type": "line",
                "x": 2,
                "y": 4,
                "width": 8,
                "height": 6,
                "strokeWidth": 4,
                "points": [[0, 0], [8, 6]],
            },
        ]

        scale_elements(elements, 2)

        assert elements[0]["width"] == 40
        assert elements[0]["height"] == 20
        assert elements[0]["strokeWidth"] == 4
        assert elements[1]["x"] == 4
        assert elements[1]["y"] == 8
        assert elements[1]["points"] == [[0, 0], [16, 12]]

    def test_fit_elements_to_size(self) -> None:
        elements = [
            {"type": "rectangle", "x": 0, "y": 0, "width": 40, "height": 40, "strokeWidth": 2},
        ]

        fit_elements_to_size(elements, 64)

        assert elements[0]["width"] == pytest.approx(64.0)
        assert elements[0]["height"] == pytest.approx(64.0)

    def test_detects_circle_like_paths(self) -> None:
        circle_points = [(0, 0), (1, 0), (2, 1), (2, 2), (1, 2), (0, 1), (0, 0)]
        assert is_circle_like(circle_points)

        line_points = [(0, 0), (20, 0), (20, 1)]
        assert not is_circle_like(line_points)
