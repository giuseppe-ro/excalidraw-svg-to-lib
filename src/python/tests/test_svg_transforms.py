from __future__ import annotations

import random

import pytest

from excalidraw_svg_to_lib.id_generator import IdGenerator
from excalidraw_svg_to_lib.svg.transforms import (
    IDENTITY,
    apply_transform_to_element,
    compose,
    parse_transform,
)
from excalidraw_svg_to_lib.svg.parser import svg_to_elements


@pytest.fixture
def ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))


# ---------------------------------------------------------------------------
# parse_transform
# ---------------------------------------------------------------------------


class TestParseTransform:
    def test_identity(self) -> None:
        assert parse_transform("") is None
        assert parse_transform(" ") is None

    def test_translate_simple(self) -> None:
        t = parse_transform("translate(10, 20)")
        assert t is not None
        # translate(10,20) = matrix(1,0,0,1,10,20)
        assert t == (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)

    def test_translate_single_value(self) -> None:
        t = parse_transform("translate(10)")
        assert t == (1.0, 0.0, 0.0, 1.0, 10.0, 0.0)

    def test_translate_spaces_as_separator(self) -> None:
        t = parse_transform("translate(10 20)")
        assert t == (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)

    def test_translate_negative(self) -> None:
        t = parse_transform("translate(-5, -10)")
        assert t == (1.0, 0.0, 0.0, 1.0, -5.0, -10.0)

    def test_scale_uniform(self) -> None:
        t = parse_transform("scale(2)")
        assert t == (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)

    def test_scale_non_uniform(self) -> None:
        t = parse_transform("scale(2, 3)")
        assert t == (2.0, 0.0, 0.0, 3.0, 0.0, 0.0)

    def test_matrix(self) -> None:
        t = parse_transform("matrix(1, 0, 0, 1, 10, 20)")
        assert t == (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)

    def test_matrix_spaces(self) -> None:
        t = parse_transform("matrix(1 0 0 1 10 20)")
        assert t == (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)

    def test_multiple_transforms(self) -> None:
        # translate then scale: scale is applied first in the chain
        t = parse_transform("translate(10, 20) scale(2)")
        # Should compose: translate(10,20) ∘ scale(2)
        # scale(2) = (2,0,0,2,0,0)
        # translate = (1,0,0,1,10,20)
        # compose: a=1*2+0*0=2, b=0*2+1*0=0, c=1*0+0*2=0, d=0*0+1*2=2
        # e=1*0+0*0+10=10, f=0*0+1*0+20=20
        assert t == (2.0, 0.0, 0.0, 2.0, 10.0, 20.0)

    def test_unknown_function_ignored(self) -> None:
        # Gracefully handle unknown transform functions
        t = parse_transform("translate(5, 10) skewX(10)")
        # Should handle at least the translate part
        assert t is not None

    def test_rotate(self) -> None:
        import math
        t = parse_transform("rotate(90)")
        assert t is not None
        cos90 = math.cos(math.radians(90))
        sin90 = math.sin(math.radians(90))
        assert t[0] == pytest.approx(cos90, abs=1e-6)  # a = cos
        assert t[1] == pytest.approx(sin90, abs=1e-6)  # b = sin
        assert t[2] == pytest.approx(-sin90, abs=1e-6)  # c = -sin
        assert t[3] == pytest.approx(cos90, abs=1e-6)  # d = cos


# ---------------------------------------------------------------------------
# compose
# ---------------------------------------------------------------------------


class TestCompose:
    def test_identity_compose(self) -> None:
        t = (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)
        assert compose(IDENTITY, t) == t
        assert compose(t, IDENTITY) == t

    def test_translate_compose(self) -> None:
        t1 = (1.0, 0.0, 0.0, 1.0, 10.0, 0.0)  # translate(10, 0)
        t2 = (1.0, 0.0, 0.0, 1.0, 0.0, 20.0)  # translate(0, 20)
        result = compose(t1, t2)
        assert result == (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)

    def test_scale_then_translate(self) -> None:
        # t1 = translate(10, 20), t2 = scale(2)
        # Result: first scale by 2, then translate by (10, 20)
        t1 = (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)
        t2 = (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)
        result = compose(t1, t2)
        assert result == (2.0, 0.0, 0.0, 2.0, 10.0, 20.0)


# ---------------------------------------------------------------------------
# apply_transform_to_element
# ---------------------------------------------------------------------------


class TestApplyTransformToElement:
    def test_translate_rectangle(self) -> None:
        elem = {"type": "rectangle", "x": 5, "y": 5, "width": 10, "height": 10}
        t = (1.0, 0.0, 0.0, 1.0, 10.0, 20.0)  # translate(10, 20)
        apply_transform_to_element(t, elem)
        assert elem["x"] == 15.0
        assert elem["y"] == 25.0
        assert elem["width"] == 10.0
        assert elem["height"] == 10.0

    def test_scale_rectangle(self) -> None:
        elem = {"type": "rectangle", "x": 5, "y": 5, "width": 10, "height": 10}
        t = (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)  # scale(2)
        apply_transform_to_element(t, elem)
        assert elem["x"] == 10.0
        assert elem["y"] == 10.0
        assert elem["width"] == 20.0
        assert elem["height"] == 20.0

    def test_identity_no_change(self) -> None:
        elem = {"type": "rectangle", "x": 5, "y": 5, "width": 10, "height": 10}
        apply_transform_to_element(IDENTITY, elem)
        assert elem["x"] == 5
        assert elem["y"] == 5
        assert elem["width"] == 10
        assert elem["height"] == 10

    def test_translate_line_with_points(self) -> None:
        elem = {
            "type": "line",
            "x": 0,
            "y": 0,
            "width": 10,
            "height": 10,
            "points": [[0, 0], [5, 5], [10, 10]],
        }
        t = (1.0, 0.0, 0.0, 1.0, 20.0, 30.0)  # translate(20, 30)
        apply_transform_to_element(t, elem)
        assert elem["x"] == 20.0
        assert elem["y"] == 30.0
        assert elem["width"] == 10.0
        assert elem["height"] == 10.0
        # Points should be recalculated relative to new origin
        assert elem["points"] == [[0, 0], [5, 5], [10, 10]]

    def test_scale_line_with_points(self) -> None:
        elem = {
            "type": "line",
            "x": 5,
            "y": 5,
            "width": 10,
            "height": 10,
            "points": [[0, 0], [5, 5], [10, 10]],
        }
        t = (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)  # scale(2)
        apply_transform_to_element(t, elem)
        assert elem["x"] == 10.0
        assert elem["y"] == 10.0
        assert elem["width"] == 20.0
        assert elem["height"] == 20.0
        # Points: (5,5)->(10,10), (10,10)->(20,20), (15,15)->(30,30)
        # Relative to new origin (10,10): [[0,0],[10,10],[20,20]]
        assert elem["points"] == [[0, 0], [10, 10], [20, 20]]

    def test_translate_ellipse(self) -> None:
        elem = {"type": "ellipse", "x": 16, "y": 16, "width": 32, "height": 32}
        t = (1.0, 0.0, 0.0, 1.0, 5.0, 10.0)
        apply_transform_to_element(t, elem)
        assert elem["x"] == 21.0
        assert elem["y"] == 26.0
        assert elem["width"] == 32.0
        assert elem["height"] == 32.0


# ---------------------------------------------------------------------------
# End-to-end: SVG with transform attribute
# ---------------------------------------------------------------------------


class TestSvgParserWithTransforms:
    def test_translate_group_shifts_element(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 80 80">
            <g transform="translate(10, 20)">
                <rect x="5" y="5" width="10" height="10" fill="#ff0000"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["x"] == 15.0
        assert elements[0]["y"] == 25.0
        assert elements[0]["width"] == 10.0
        assert elements[0]["height"] == 10.0

    def test_scale_group_scales_element(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 100 100">
            <g transform="scale(2)">
                <rect x="5" y="5" width="10" height="10" fill="#ff0000"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["x"] == 10.0
        assert elements[0]["y"] == 10.0
        assert elements[0]["width"] == 20.0
        assert elements[0]["height"] == 20.0

    def test_nested_transforms_compose(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 200 200">
            <g transform="translate(10, 0)">
                <g transform="scale(2)">
                    <rect x="5" y="5" width="10" height="10" fill="#ff0000"/>
                </g>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        # Inner scale first: (5,5,10,10) → (10,10,20,20)
        # Then outer translate: (10,10,20,20) → (20,10,20,20)
        assert len(elements) == 1
        assert elements[0]["x"] == 20.0
        assert elements[0]["y"] == 10.0
        assert elements[0]["width"] == 20.0
        assert elements[0]["height"] == 20.0

    def test_multiple_elements_in_transformed_group(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 80 80">
            <rect x="0" y="0" width="80" height="80" fill="#0000ff"/>
            <g transform="translate(10, 10)">
                <rect x="0" y="0" width="10" height="10" fill="#ff0000"/>
                <circle cx="20" cy="20" r="5" fill="#00ff00"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 3
        # Background rect — no transform
        assert elements[0]["type"] == "rectangle"
        assert elements[0]["x"] == 0
        assert elements[0]["y"] == 0
        assert elements[0]["width"] == 80

        # Translated rect
        assert elements[1]["type"] == "rectangle"
        assert elements[1]["x"] == 10.0
        assert elements[1]["y"] == 10.0

        # Translated circle
        assert elements[2]["type"] == "ellipse"
        # circle: cx=20, r=5, so x=15, y=15, w=10, h=10
        # After translate(10,10): x=25, y=25, w=10, h=10
        assert elements[2]["x"] == 25.0
        assert elements[2]["y"] == 25.0

    def test_line_points_transformed(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 100 100">
            <g transform="translate(10, 20)">
                <line x1="0" y1="0" x2="50" y2="50" stroke="#ff0000" stroke-width="2"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 1
        assert elements[0]["type"] == "line"
        assert elements[0]["x"] == 10.0
        assert elements[0]["y"] == 20.0
        assert elements[0]["width"] == 50.0
        assert elements[0]["height"] == 50.0
        assert elements[0]["points"] == [[0, 0], [50, 50]]

    def test_path_in_translated_group(self, ids: IdGenerator) -> None:
        svg = """<svg viewBox="0 0 80 80">
            <rect x="0" y="0" width="80" height="80" fill="#C925D1"/>
            <g transform="translate(13, 12)">
                <path d="M5,5 L15,5 L15,15 Z" fill="#FFFFFF"/>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) >= 2
        rect = elements[0]
        assert rect["x"] == 0
        assert rect["y"] == 0

        # The path should be shifted by (13, 12)
        path_elem = elements[1]
        assert path_elem["x"] == pytest.approx(18.0)  # 5 + 13
        assert path_elem["y"] == pytest.approx(17.0)  # 5 + 12

    def test_aws_activate_style_svg(self, ids: IdGenerator) -> None:
        """Simulate the activate.svg structure: background + translated content group."""
        svg = """<svg viewBox="0 0 80 80">
            <g stroke="none" fill="none">
                <g fill="#C925D1">
                    <rect x="0" y="0" width="80" height="80"/>
                </g>
                <g transform="translate(12.9998, 11.9998)" fill="#FFFFFF">
                    <rect x="0" y="0" width="54" height="56"/>
                </g>
            </g>
        </svg>"""
        elements, _ = svg_to_elements(svg, ids)

        assert len(elements) == 2
        bg = elements[0]
        icon = elements[1]

        assert bg["x"] == 0
        assert bg["y"] == 0
        assert bg["width"] == 80
        assert bg["height"] == 80

        assert icon["x"] == pytest.approx(12.9998)
        assert icon["y"] == pytest.approx(11.9998)
        assert icon["width"] == pytest.approx(54.0)
        assert icon["height"] == pytest.approx(56.0)
