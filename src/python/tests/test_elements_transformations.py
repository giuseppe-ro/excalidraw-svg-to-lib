from __future__ import annotations

import pytest

from excalidraw_svg_to_lib.elements.transformations import (
    fit_elements_to_size,
    normalize_elements,
    scale_elements,
    sort_elements,
)


class TestSortElements:
    def test_sorts_by_element_type_order(self) -> None:
        elements = [
            {"type": "text"},
            {"type": "line"},
            {"type": "rectangle"},
            {"type": "ellipse"},
        ]
        result = sort_elements(elements)
        assert [e["type"] for e in result] == ["rectangle", "ellipse", "line", "text"]

    def test_sorts_image_with_arrow(self) -> None:
        elements = [
            {"type": "text"},
            {"type": "image"},
            {"type": "arrow"},
            {"type": "rectangle"},
        ]
        result = sort_elements(elements)
        assert result[0]["type"] == "rectangle"
        assert result[-1]["type"] == "text"

    def test_unknown_type_sorts_last(self) -> None:
        elements = [
            {"type": "text"},
            {"type": "unknown"},
            {"type": "rectangle"},
        ]
        result = sort_elements(elements)
        assert result[-1]["type"] == "unknown"

    def test_stable_sort_for_same_types(self) -> None:
        elements = [
            {"type": "line", "order": 2},
            {"type": "line", "order": 1},
            {"type": "rectangle", "order": 1},
        ]
        result = sort_elements(elements)
        assert result[0]["type"] == "rectangle"
        assert result[1]["order"] == 2  # stable: original order preserved


class TestNormalizeElements:
    def test_shifts_all_elements_to_origin(self) -> None:
        elements = [
            {"x": 10, "y": 20},
            {"x": 15, "y": 25},
        ]
        normalize_elements(elements)
        assert elements[0]["x"] == 0
        assert elements[0]["y"] == 0
        assert elements[1]["x"] == 5
        assert elements[1]["y"] == 5

    def test_no_op_when_already_at_origin(self) -> None:
        elements = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 20},
        ]
        normalize_elements(elements)
        assert elements[0]["x"] == 0
        assert elements[0]["y"] == 0

    def test_handles_negative_coordinates(self) -> None:
        elements = [
            {"x": -10, "y": -20},
            {"x": 0, "y": 0},
        ]
        normalize_elements(elements)
        assert elements[0]["x"] == 0
        assert elements[0]["y"] == 0
        assert elements[1]["x"] == 10
        assert elements[1]["y"] == 20

    def test_empty_list_returns_empty(self) -> None:
        assert normalize_elements([]) == []

    def test_modifies_in_place(self) -> None:
        elements = [{"x": 5, "y": 5}]
        result = normalize_elements(elements)
        assert result is elements


class TestScaleElements:
    def test_scales_position_and_size(self) -> None:
        elements = [{"x": 10, "y": 10, "width": 20, "height": 10, "strokeWidth": 2}]
        scale_elements(elements, 2)
        assert elements[0]["x"] == 20
        assert elements[0]["y"] == 20
        assert elements[0]["width"] == 40
        assert elements[0]["height"] == 20

    def test_scales_stroke_width_with_minimum(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 10, "height": 10, "strokeWidth": 2}]
        scale_elements(elements, 0.1)
        assert elements[0]["strokeWidth"] == 0.5  # min stroke width is 0.5

    def test_scales_points(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 10, "height": 10, "points": [[0, 0], [10, 10]]}]
        scale_elements(elements, 3)
        assert elements[0]["points"] == [[0, 0], [30, 30]]

    def test_no_op_when_scale_is_1(self) -> None:
        elements = [{"x": 10, "y": 10, "width": 20, "height": 10}]
        result = scale_elements(elements, 1.0)
        assert result is elements
        assert elements[0]["x"] == 10

    def test_returns_same_reference_when_scale_is_1(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 10, "height": 10}]
        result = scale_elements(elements, 1.0)
        assert result is elements


class TestFitElementsToSize:
    def test_fits_wide_icon(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 100, "height": 50, "strokeWidth": 2}]
        fit_elements_to_size(elements, 64)
        assert elements[0]["width"] == pytest.approx(64.0)
        assert elements[0]["height"] == pytest.approx(32.0)

    def test_fits_tall_icon(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 30, "height": 120, "strokeWidth": 2}]
        fit_elements_to_size(elements, 64)
        assert elements[0]["width"] == pytest.approx(16.0)
        assert elements[0]["height"] == pytest.approx(64.0)

    def test_fits_square_icon(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 40, "height": 40, "strokeWidth": 2}]
        fit_elements_to_size(elements, 64)
        assert elements[0]["width"] == pytest.approx(64.0)
        assert elements[0]["height"] == pytest.approx(64.0)

    def test_no_op_when_empty(self) -> None:
        assert fit_elements_to_size([], 64) == []

    def test_no_op_when_target_size_is_zero(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 100, "height": 100}]
        result = fit_elements_to_size(elements, 0)
        assert result[0]["width"] == 100

    def test_no_op_when_target_size_is_negative(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 100, "height": 100}]
        result = fit_elements_to_size(elements, -10)
        assert result[0]["width"] == 100

    def test_fits_multiple_elements_by_combined_bounds(self) -> None:
        elements = [
            {"x": 0, "y": 0, "width": 50, "height": 50, "strokeWidth": 2},
            {"x": 50, "y": 0, "width": 50, "height": 50, "strokeWidth": 2},
        ]
        fit_elements_to_size(elements, 64)
        # Combined bounds: 100 wide, 50 tall → scale = 0.64
        assert elements[0]["width"] == pytest.approx(32.0)

    def test_preserves_aspect_ratio(self) -> None:
        elements = [{"x": 0, "y": 0, "width": 80, "height": 40, "strokeWidth": 2}]
        fit_elements_to_size(elements, 64)
        assert elements[0]["width"] == pytest.approx(64.0)
        assert elements[0]["height"] == pytest.approx(32.0)
        # Verify ratio preserved: 80/40 == 64/32
        assert elements[0]["width"] / elements[0]["height"] == pytest.approx(2.0)
