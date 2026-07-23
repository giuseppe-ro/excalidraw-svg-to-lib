from __future__ import annotations

import pytest

from excalidraw_svg_to_lib.elements import (
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
        assert element_bounds(elements) == (10, 20, 60, 70)

    def test_bounds_with_negative_coordinates(self) -> None:
        elements = [{"x": -10, "y": -10, "width": 20, "height": 20}]
        assert element_bounds(elements) == (-10, -10, 10, 10)


class TestIconGroupId:
    def test_returns_first_group_id(self) -> None:
        elements = [{"groupIds": ["group-abc"]}]
        assert icon_group_id(elements) == "group-abc"

    def test_raises_when_no_group_ids(self) -> None:
        elements = [{}]
        with pytest.raises(ValueError, match="must belong to a group"):
            icon_group_id(elements)


class TestIsCircleLike:
    def test_detects_circle_like_paths(self) -> None:
        circle_points = [(0, 0), (1, 0), (2, 1), (2, 2), (1, 2), (0, 1), (0, 0)]
        assert is_circle_like(circle_points) is True

    def test_rejects_non_circle_shapes(self) -> None:
        assert not is_circle_like([(0, 0), (20, 0), (20, 1)])  # too large
        assert not is_circle_like([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])  # too few points
