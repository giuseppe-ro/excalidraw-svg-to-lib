from __future__ import annotations

from excalidraw_svg_to_lib.svg.utils import (
    inherit_style,
    local_name,
    normalize_color,
    parse_length,
)


class TestLocalName:
    def test_returns_tag_as_is_when_no_namespace(self) -> None:
        assert local_name("rect") == "rect"

    def test_strips_svg_namespace(self) -> None:
        assert (
            local_name("{http://www.w3.org/2000/svg}rect") == "rect"
        )

    def test_strips_custom_namespace(self) -> None:
        assert local_name("{http://example.com}path") == "path"

    def test_handles_empty_string(self) -> None:
        assert local_name("") == ""


class TestParseLength:
    def test_parses_plain_number(self) -> None:
        assert parse_length("42") == 42.0

    def test_parses_float(self) -> None:
        assert parse_length("3.14") == 3.14

    def test_parses_px_suffix(self) -> None:
        assert parse_length("64px") == 64.0

    def test_returns_default_on_none(self) -> None:
        assert parse_length(None) == 0.0

    def test_returns_custom_default_on_none(self) -> None:
        assert parse_length(None, default=100.0) == 100.0

    def test_returns_default_on_empty_string(self) -> None:
        assert parse_length("") == 0.0

    def test_parses_negative_value(self) -> None:
        assert parse_length("-10") == -10.0


class TestNormalizeColor:
    def test_returns_transparent_for_none(self) -> None:
        assert normalize_color(None) == "transparent"

    def test_returns_transparent_for_none_literal(self) -> None:
        assert normalize_color("none") == "transparent"

    def test_returns_hex_color_unchanged(self) -> None:
        assert normalize_color("#ff0000") == "#ff0000"

    def test_returns_named_color_unchanged(self) -> None:
        assert normalize_color("blue") == "blue"

    def test_returns_rgb_unchanged(self) -> None:
        assert normalize_color("rgb(255, 0, 0)") == "rgb(255, 0, 0)"


class TestInheritStyle:
    def test_returns_copy_of_parent_when_no_attributes(self) -> None:
        parent = {"fill": "#fff", "stroke": "#000"}
        result = inherit_style(parent, {})
        assert result == parent
        assert result is not parent

    def test_inherits_fill(self) -> None:
        result = inherit_style({"fill": "#fff"}, {"fill": "#ff0000"})
        assert result["fill"] == "#ff0000"

    def test_inherits_stroke(self) -> None:
        result = inherit_style({"stroke": "#fff"}, {"stroke": "#00ff00"})
        assert result["stroke"] == "#00ff00"

    def test_inherits_stroke_width(self) -> None:
        result = inherit_style({}, {"stroke-width": "2.5"})
        assert result["stroke_width"] == 2.5

    def test_inherits_opacity_and_scales_to_percent(self) -> None:
        result = inherit_style({}, {"opacity": "0.2"})
        assert result["opacity"] == 20.0

    def test_normalizes_fill_to_transparent(self) -> None:
        result = inherit_style({}, {"fill": "none"})
        assert result["fill"] == "transparent"

    def test_normalizes_stroke_to_transparent(self) -> None:
        result = inherit_style({}, {"stroke": "none"})
        assert result["stroke"] == "transparent"

    def test_preserves_parent_values_not_overridden(self) -> None:
        parent = {"fill": "#fff", "stroke": "#000", "stroke_width": 1.0}
        result = inherit_style(parent, {"fill": "#ff0000"})
        assert result["fill"] == "#ff0000"
        assert result["stroke"] == "#000"
        assert result["stroke_width"] == 1.0

    def test_multiple_inheritances_chain(self) -> None:
        root = {"fill": "#fff", "stroke": "#000"}
        level1 = inherit_style(root, {"fill": "#ff0000"})
        level2 = inherit_style(level1, {"stroke": "#00ff00"})
        assert level2["fill"] == "#ff0000"
        assert level2["stroke"] == "#00ff00"
