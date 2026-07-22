"""Tests for uniform stroke width normalization."""

from __future__ import annotations

import random

import pytest

from tests.conftest import FIXTURES_DIR

from excalidraw_svg_to_lib.elements.transformations import normalize_stroke_width
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.runner import convert_svg_to_library
from excalidraw_svg_to_lib.id_generator import IdGenerator


@pytest.fixture
def fixed_ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


# ---------------------------------------------------------------------------
# Unit tests — normalize_stroke_width (pure function)
# ---------------------------------------------------------------------------


class TestStrokeNormalization:
    def test_sets_uniform_stroke_across_all_elements(self) -> None:
        elements = [
            {"type": "line", "strokeWidth": 4},
            {"type": "line", "strokeWidth": 2},
            {"type": "line", "strokeWidth": 1},
        ]
        normalize_stroke_width(elements, 1.5)

        assert elements[0]["strokeWidth"] == 1.5
        assert elements[1]["strokeWidth"] == 1.5
        assert elements[2]["strokeWidth"] == 1.5

    def test_works_with_mixed_element_types(self) -> None:
        elements = [
            {"type": "rectangle", "strokeWidth": 3},
            {"type": "line", "strokeWidth": 2},
            {"type": "text", "strokeWidth": 1},
        ]
        normalize_stroke_width(elements, 1)

        assert elements[0]["strokeWidth"] == 1
        assert elements[1]["strokeWidth"] == 1
        assert elements[2]["strokeWidth"] == 1

    def test_raises_on_zero_stroke_width(self) -> None:
        elements = [{"type": "line", "strokeWidth": 2}]
        with pytest.raises(ValueError, match="positive"):
            normalize_stroke_width(elements, 0)

    def test_raises_on_negative_stroke_width(self) -> None:
        elements = [{"type": "line", "strokeWidth": 2}]
        with pytest.raises(ValueError, match="positive"):
            normalize_stroke_width(elements, -1)

    def test_no_op_on_empty_list(self) -> None:
        result = normalize_stroke_width([], 1)
        assert result == []

    def test_modifies_in_place_and_returns_same_ref(self) -> None:
        elements = [{"type": "line", "strokeWidth": 2}]
        result = normalize_stroke_width(elements, 1)
        assert result is elements


# ---------------------------------------------------------------------------
# Integration tests — stroke normalization through the conversion pipeline
# ---------------------------------------------------------------------------


class TestStrokeWidthInPipeline:
    def test_none_preserves_original_stroke_widths(self, fixed_ids: IdGenerator) -> None:
        """When uniform_stroke_width is None, original SVG stroke-widths are preserved."""
        svg = (FIXTURES_DIR / "stroked_icon.svg").read_text(encoding="utf-8")
        opts = ConvertOptions(normalize=True, scale_to_target=True, uniform_stroke_width=None)
        result = convert_svg_to_library(svg, opts, ids=fixed_ids)

        elements = result["library"][0]
        lines = [e for e in elements if e["type"] == "line"]

        # After scaling, the original stroke-widths (2, 3, 1.5) are scaled proportionally
        # and clamped to MIN_STROKE_WIDTH=1, so they diverge
        stroke_widths = [e["strokeWidth"] for e in lines]
        # They should NOT all be the same (original values differ)
        assert len(set(stroke_widths)) > 1

    def test_uniform_stroke_normalizes_all_elements(self, fixed_ids: IdGenerator) -> None:
        """When uniform_stroke_width=1, all lines end up at exactly 1."""
        svg = (FIXTURES_DIR / "stroked_icon.svg").read_text(encoding="utf-8")
        opts = ConvertOptions(normalize=True, scale_to_target=True, uniform_stroke_width=1)
        result = convert_svg_to_library(svg, opts, ids=fixed_ids)

        elements = result["library"][0]
        lines = [e for e in elements if e["type"] == "line"]

        for line in lines:
            assert line["strokeWidth"] == 1

    def test_uniform_stroke_applied_after_scaling(self, fixed_ids: IdGenerator) -> None:
        """Stroke normalization happens after scaling, so the value is exact."""
        svg = (FIXTURES_DIR / "stroked_icon.svg").read_text(encoding="utf-8")
        opts = ConvertOptions(
            normalize=True, scale_to_target=True, uniform_stroke_width=1.5
        )
        result = convert_svg_to_library(svg, opts, ids=fixed_ids)

        elements = result["library"][0]
        for element in elements:
            if element["type"] == "line":
                assert element["strokeWidth"] == 1.5

    def test_uniform_stroke_with_normalize_disabled(self, fixed_ids: IdGenerator) -> None:
        """Works regardless of normalize flag."""
        svg = (FIXTURES_DIR / "stroked_icon.svg").read_text(encoding="utf-8")
        opts = ConvertOptions(
            normalize=False, scale_to_target=False, uniform_stroke_width=1
        )
        result = convert_svg_to_library(svg, opts, ids=fixed_ids)

        elements = result["library"][0]
        lines = [e for e in elements if e["type"] == "line"]
        for line in lines:
            assert line["strokeWidth"] == 1
