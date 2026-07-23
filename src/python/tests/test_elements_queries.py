from __future__ import annotations

import pytest

from excalidraw_svg_to_lib.elements.queries import (
    element_bounds,
    icon_group_id,
    is_circle_like,
)


class TestElementBounds:
    def test_returns_correct_bounds(self) -> None:
        elements = [
            {"x": 10, "y": 20, "width": 30, "height": 40},
            {"x": 50, "y": 60, "width": 10, "height": 10},
        ]
        # elem1: max_x=10+30=40, max_y=20+40=60; elem2: max_x=50+10=60, max_y=60+10=70
        assert element_bounds(elements) == (10, 20, 60, 70)

    def test_bounds_with_single_element(self) -> None:
        elements = [{"x": 5, "y": 5, "width": 20, "height": 20}]
        assert element_bounds(elements) == (5, 5, 25, 25)

    def test_bounds_with_negative_coordinates(self) -> None:
        elements = [
            {"x": -10, "y": -10, "width": 20, "height": 20},
        ]
        assert element_bounds(elements) == (-10, -10, 10, 10)

    def test_bounds_with_origin_element(self) -> None:
        elements = [
            {"x": 0, "y": 0, "width": 100, "height": 50},
            {"x": 50, "y": 25, "width": 25, "height": 25},
        ]
        assert element_bounds(elements) == (0, 0, 100, 50)


class TestIconGroupId:
    def test_returns_first_group_id(self) -> None:
        elements = [{"groupIds": ["group-abc"]}]
        assert icon_group_id(elements) == "group-abc"

    def test_raises_when_no_group_ids(self) -> None:
        elements = [{}]
        with pytest.raises(ValueError, match="must belong to a group"):
            icon_group_id(elements)

    def test_raises_when_empty_group_ids_list(self) -> None:
        elements = [{"groupIds": []}]
        with pytest.raises(ValueError, match="must belong to a group"):
            icon_group_id(elements)

    def test_ignores_extra_group_ids(self) -> None:
        elements = [{"groupIds": ["primary", "secondary"]}]
        assert icon_group_id(elements) == "primary"


class TestIsCircleLike:
    def test_detects_perfect_circle(self) -> None:
        points = [(0, 0), (1, 0), (2, 1), (2, 2), (1, 2), (0, 1), (0, 0)]
        assert is_circle_like(points) is True

    def test_detects_near_circle(self) -> None:
        # Slightly elliptical but within ratio tolerance
        points = [(0, 0), (0.9, 0), (2, 0.9), (2, 2), (0.9, 2), (0, 0.9), (0, 0)]
        assert is_circle_like(points) is True

    def test_rejects_line(self) -> None:
        points = [(0, 0), (20, 0), (20, 1)]
        assert is_circle_like(points) is False

    def test_rejects_too_few_points(self) -> None:
        points = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        assert is_circle_like(points) is False

    def test_rejects_large_shape(self) -> None:
        # Circle-like ratio but too large (> 6 in any dimension)
        points = [(0, 0), (5, 0), (10, 5), (10, 10), (5, 10), (0, 5), (0, 0)]
        assert is_circle_like(points) is False

    def test_rejects_zero_width(self) -> None:
        points = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 0)]
        assert is_circle_like(points) is False

    def test_rejects_zero_height(self) -> None:
        points = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (0, 0)]
        assert is_circle_like(points) is False

    def test_rejects_highly_elliptical(self) -> None:
        # Very stretched — ratio outside 0.7-1.3
        points = [(0, 0), (0.2, 0), (1, 0.2), (1, 5), (0.2, 5), (0, 0.2), (0, 0)]
        assert is_circle_like(points) is False
