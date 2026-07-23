from __future__ import annotations

import random
import pytest

from excalidraw_svg_to_lib.elements.models import (
    apply_paint_style,
    create_base_element,
    create_invisible_box_element,
    create_label_element,
    finalize_linear_element,
)
from excalidraw_svg_to_lib.constants import ICON_PADDING, DEFAULT_LABEL_GAP
from excalidraw_svg_to_lib.id_generator import IdGenerator


@pytest.fixture
def ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


class TestCreateBaseElement:
    def test_creates_rectangle_element(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "group-1", ids)
        assert elem["type"] == "rectangle"
        assert elem["version"] == 1
        assert elem["isDeleted"] is False
        assert elem["groupIds"] == ["group-1"]
        assert elem["fillStyle"] == "solid"
        assert elem["strokeWidth"] == 0.2
        assert elem["strokeStyle"] == "solid"
        assert elem["roughness"] == 0
        assert elem["opacity"] == 100
        assert elem["angle"] == 0

    def test_creates_element_with_all_required_fields(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "group-1", ids)
        required = {
            "type", "version", "versionNonce", "isDeleted", "id",
            "fillStyle", "strokeWidth", "strokeStyle", "roughness",
            "opacity", "angle", "strokeColor", "backgroundColor",
            "seed", "groupIds", "strokeSharpness", "boundElementIds",
        }
        assert required.issubset(elem.keys())

    def test_different_types_produce_different_elements(self, ids: IdGenerator) -> None:
        rect = create_base_element("rectangle", "g1", ids)
        ellip = create_base_element("ellipse", "g1", ids)
        line = create_base_element("line", "g1", ids)
        assert rect["type"] == "rectangle"
        assert ellip["type"] == "ellipse"
        assert line["type"] == "line"


class TestApplyPaintStyle:
    def test_sets_background_color_from_fill(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "#ff0000", "stroke": "transparent", "stroke_width": 0})
        assert elem["backgroundColor"] == "#ff0000"

    def test_sets_transparent_background_when_fill_is_transparent(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "transparent", "stroke": "transparent", "stroke_width": 0})
        assert elem["backgroundColor"] == "transparent"

    def test_sets_stroke_color_from_stroke(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "transparent", "stroke": "#00ff00", "stroke_width": 2})
        assert elem["strokeColor"] == "#00ff00"

    def test_sets_transparent_stroke_when_stroke_is_transparent(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "transparent", "stroke": "transparent", "stroke_width": 2})
        assert elem["strokeColor"] == "#000000"

    def test_sets_stroke_width_when_visible(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "#fff", "stroke": "#000", "stroke_width": 3.5})
        assert elem["strokeWidth"] == 3.5

    def test_defaults_stroke_width_to_2_when_stroke_transparent(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "#fff", "stroke": "transparent", "stroke_width": 0})
        assert elem["strokeWidth"] == 0.2

    def test_sets_opacity(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "#fff", "stroke": "#000", "stroke_width": 1, "opacity": 75})
        assert elem["opacity"] == 75

    def test_defaults_opacity_to_100_when_missing(self, ids: IdGenerator) -> None:
        elem = create_base_element("rectangle", "g1", ids)
        apply_paint_style(elem, {"fill": "#fff", "stroke": "#000", "stroke_width": 1})
        assert elem["opacity"] == 100


class TestFinalizeLinearElement:
    def test_sets_bounds_and_relative_points(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "g1", ids)
        result = finalize_linear_element(elem, [(10, 20), (30, 40)])
        assert result is not None
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["width"] == 20
        assert result["height"] == 20
        assert result["points"] == [[0, 0], [20, 20]]

    def test_returns_none_for_fewer_than_two_points(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "g1", ids)
        assert finalize_linear_element(elem, [(0, 0)]) is None
        assert finalize_linear_element(elem, []) is None

    def test_sets_bindings_to_none(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "g1", ids)
        result = finalize_linear_element(elem, [(0, 0), (10, 10)])
        assert result["lastCommittedPoint"] is None
        assert result["startBinding"] is None
        assert result["endBinding"] is None
        assert result["startArrowhead"] is None
        assert result["endArrowhead"] is None

    def test_handles_negative_coordinates(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "g1", ids)
        result = finalize_linear_element(elem, [(-10, -20), (10, 20)])
        assert result["x"] == -10
        assert result["y"] == -20
        assert result["width"] == 20
        assert result["height"] == 40
        assert result["points"] == [[0, 0], [20, 40]]

    def test_multi_point_path(self, ids: IdGenerator) -> None:
        elem = create_base_element("line", "g1", ids)
        result = finalize_linear_element(elem, [(0, 0), (50, 0), (50, 50), (0, 50), (0, 0)])
        assert result["x"] == 0
        assert result["y"] == 0
        assert result["width"] == 50
        assert result["height"] == 50
        assert len(result["points"]) == 5


class TestCreateInvisibleBoxElement:
    def test_creates_rectangle_element(self, ids: IdGenerator) -> None:
        box = create_invisible_box_element((0, 0, 64, 64), ids, "group-1")
        assert box["type"] == "rectangle"

    def test_extends_beyond_icon_by_padding(self, ids: IdGenerator) -> None:
        box = create_invisible_box_element((0, 0, 64, 64), ids, "group-1")
        assert box["x"] == -ICON_PADDING
        assert box["y"] == -ICON_PADDING
        assert box["width"] == 64 + 2 * ICON_PADDING
        assert box["height"] == 64 + 2 * ICON_PADDING

    def test_has_minimal_stroke(self, ids: IdGenerator) -> None:
        box = create_invisible_box_element((0, 0, 64, 64), ids, "group-1")
        assert box["strokeWidth"] == 0.2  # DEFAULT_STROKE_WIDTH
        assert box["backgroundColor"] == "transparent"

    def test_sets_group_ids(self, ids: IdGenerator) -> None:
        box = create_invisible_box_element((0, 0, 64, 64), ids, "group-1")
        assert box["groupIds"] == ["group-1"]

    def test_handles_offset_icon_bounds(self, ids: IdGenerator) -> None:
        box = create_invisible_box_element((10, 20, 74, 84), ids, "g1")
        assert box["x"] == 10 - ICON_PADDING
        assert box["y"] == 20 - ICON_PADDING
        assert box["width"] == 64 + 2 * ICON_PADDING
        assert box["height"] == 64 + 2 * ICON_PADDING


class TestCreateLabelElement:
    def test_creates_text_element(self, ids: IdGenerator) -> None:
        label = create_label_element("test", -4, 72, 70, ids, "group-1")
        assert label["type"] == "text"
        assert label["text"] == "test"
        assert label["originalText"] == "test"

    def test_positions_label_below_icon(self, ids: IdGenerator) -> None:
        # icon bounds (0,0,64,64), outer box starts at -4, label y = 64 + gap(2) = 66
        label = create_label_element(
            "icon", -ICON_PADDING, 64 + 2 * ICON_PADDING, 64 + DEFAULT_LABEL_GAP, ids, "group-1"
        )
        assert label["y"] == 66

    def test_label_width_matches_outer_box(self, ids: IdGenerator) -> None:
        outer_width = 64 + 2 * ICON_PADDING
        label = create_label_element("test", -ICON_PADDING, outer_width, 70, ids, "g1")
        assert label["width"] == outer_width
        assert label["x"] == -ICON_PADDING

    def test_centers_label_under_icon(self, ids: IdGenerator) -> None:
        # outer box centered on 64-wide icon: x=-4, width=72, center at 32
        label = create_label_element("icon", -ICON_PADDING, 64 + 2 * ICON_PADDING, 66, ids, "group-1")
        assert label["x"] + label["width"] / 2 == pytest.approx(32.0)

    def test_sets_group_ids(self, ids: IdGenerator) -> None:
        label = create_label_element("test", -ICON_PADDING, 72, 66, ids, "group-1")
        assert label["groupIds"] == ["group-1"]

    def test_sets_text_alignment(self, ids: IdGenerator) -> None:
        label = create_label_element("test", -ICON_PADDING, 72, 66, ids, "group-1")
        assert label["textAlign"] == "center"
        assert label["verticalAlign"] == "top"

    def test_sets_font_properties(self, ids: IdGenerator) -> None:
        label = create_label_element("test", -ICON_PADDING, 72, 66, ids, "group-1")
        assert label["fontSize"] == 10
        assert label["fontFamily"] == 2

    def test_text_box_width_matches_outer_box_regardless_of_label_length(self, ids: IdGenerator) -> None:
        outer_width = 64 + 2 * ICON_PADDING
        short = create_label_element("a", -ICON_PADDING, outer_width, 66, ids, "g1")
        long = create_label_element("verylonglabel", -ICON_PADDING, outer_width, 66, ids, "g1")
        assert short["width"] == outer_width
        assert long["width"] == outer_width
        assert short["x"] == long["x"]
