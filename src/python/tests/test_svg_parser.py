from __future__ import annotations

import random

import pytest

from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.svg.parser import parse_view_box, svg_to_elements


@pytest.fixture
def ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


class TestParseViewBox:
    def test_parses_view_box_with_spaces(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring('<svg viewBox="0 0 64 64"></svg>')
        vb = parse_view_box(root)
        assert vb == {"x": 0.0, "y": 0.0, "width": 64.0, "height": 64.0}

    def test_parses_view_box_with_commas(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring('<svg viewBox="10,20,100,200"></svg>')
        vb = parse_view_box(root)
        assert vb == {"x": 10.0, "y": 20.0, "width": 100.0, "height": 200.0}

    def test_parses_view_box_with_mixed_separators(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring('<svg viewBox="0,0 100 100"></svg>')
        vb = parse_view_box(root)
        assert vb == {"x": 0.0, "y": 0.0, "width": 100.0, "height": 100.0}

    def test_falls_back_to_width_height_attributes(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring('<svg width="32" height="48"></svg>')
        vb = parse_view_box(root)
        assert vb == {"x": 0.0, "y": 0.0, "width": 32.0, "height": 48.0}

    def test_falls_back_to_width_height_with_px(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring('<svg width="64px" height="64px"></svg>')
        vb = parse_view_box(root)
        assert vb == {"x": 0.0, "y": 0.0, "width": 64.0, "height": 64.0}

    def test_defaults_to_64x64_when_no_dimensions(self) -> None:
        import xml.etree.ElementTree as ET

        root = ET.fromstring("<svg></svg>")
        vb = parse_view_box(root)
        assert vb == {"x": 0.0, "y": 0.0, "width": 64.0, "height": 64.0}


class TestSvgToElements:
    def test_converts_simple_rect(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 32 32"><rect x="4" y="6" width="20" height="14" fill="#ff0000"/></svg>'
        elements, view_box = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "rectangle"
        assert elements[0]["x"] == 4.0
        assert elements[0]["y"] == 6.0
        assert view_box == {"x": 0.0, "y": 0.0, "width": 32.0, "height": 32.0}

    def test_converts_circle(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="16" fill="#00ff00"/></svg>'
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "ellipse"
        assert elements[0]["x"] == 16.0
        assert elements[0]["y"] == 16.0
        assert elements[0]["width"] == 32.0
        assert elements[0]["height"] == 32.0

    def test_converts_ellipse(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 100 100"><ellipse cx="50" cy="50" rx="30" ry="20" fill="#0000ff"/></svg>'
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "ellipse"
        assert elements[0]["x"] == 20.0
        assert elements[0]["y"] == 30.0
        assert elements[0]["width"] == 60.0
        assert elements[0]["height"] == 40.0

    def test_converts_line(self, ids: IdGenerator) -> None:
        svg = (
            '<svg viewBox="0 0 100 100">'
            '<line x1="10" y1="10" x2="90" y2="90" '
            'stroke="#ff0000" stroke-width="2"/>'
            '</svg>'
        )
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "line"
        assert elements[0]["x"] == 10.0
        assert elements[0]["y"] == 10.0

    def test_converts_polygon(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 100 100"><polygon points="50,10 90,90 10,90" fill="none" stroke="#ff0000"/></svg>'
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "line"
        # polygon closes the path, so 4 points (3 + repeat of first)
        assert len(elements[0]["points"]) == 4

    def test_converts_polyline(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 100 100"><polyline points="10,10 50,90 90,10" fill="none" stroke="#00ff00"/></svg>'
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "line"
        # polyline does NOT close the path
        assert len(elements[0]["points"]) == 3

    def test_walks_nested_groups(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 64 64">
            <g fill="none">
                <g fill="#E7157B">
                    <rect x="0" y="0" width="64" height="64"/>
                </g>
                <circle cx="32" cy="32" r="8" fill="#FFFFFF"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 2
        assert elements[0]["type"] == "rectangle"
        assert elements[0]["backgroundColor"] == "#E7157B"
        assert elements[1]["type"] == "ellipse"
        assert elements[1]["backgroundColor"] == "#FFFFFF"

    def test_inherits_styles_from_parent_group(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 64 64">
            <g fill="#ff0000" stroke="#000000" stroke-width="2">
                <rect x="0" y="0" width="32" height="32"/>
                <rect x="32" y="0" width="32" height="32" fill="#00ff00"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert elements[0]["backgroundColor"] == "#ff0000"
        assert elements[1]["backgroundColor"] == "#00ff00"

    def test_skips_rect_with_zero_dimensions(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 64 64"><rect x="0" y="0" width="0" height="0" fill="#ff0000"/></svg>'
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 0

    def test_skips_circle_with_zero_radius(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="0" fill="#ff0000"/></svg>'
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 0

    def test_skips_path_with_no_d_attribute(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 64 64"><path fill="#ff0000"/></svg>'
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 0

    def test_skips_polygon_with_fewer_than_two_points(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="0 0 64 64"><polygon points="10,10" fill="none" stroke="#ff0000"/></svg>'
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 0

    def test_rejects_non_svg_root(self, ids: IdGenerator) -> None:
        with pytest.raises(ValueError, match="missing <svg>"):
            svg_to_elements("<root></root>", ids)

    def test_handles_namespace_in_svg_root(self, ids: IdGenerator) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<rect x="0" y="0" width="10" height="10" '
            'fill="#ff0000"/>'
            '</svg>'
        )
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 1

    def test_all_elements_share_group_id(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 64 64">
            <rect x="0" y="0" width="10" height="10" fill="#ff0000"/>
            <circle cx="32" cy="32" r="8" fill="#00ff00"/>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)
        group_ids = {elem["groupIds"][0] for elem in elements}
        assert len(group_ids) == 1

    def test_handles_path_element(self, ids: IdGenerator) -> None:
        svg = (
            '<svg viewBox="0 0 100 100">'
            '<path d="M 10 10 L 90 10 L 90 90" '
            'fill="none" stroke="#ff0000" stroke-width="2"/>'
            '</svg>'
        )
        elements, _ = svg_to_elements(svg, ids)
        assert len(elements) == 1
        assert elements[0]["type"] == "line"

    def test_returns_view_box_from_svg(self, ids: IdGenerator) -> None:
        svg = '<svg viewBox="10 20 200 300"><rect x="0" y="0" width="10" height="10" fill="#ff0000"/></svg>'
        _, view_box = svg_to_elements(svg, ids)
        assert view_box == {"x": 10.0, "y": 20.0, "width": 200.0, "height": 300.0}
