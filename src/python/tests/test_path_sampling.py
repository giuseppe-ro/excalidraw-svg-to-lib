from __future__ import annotations

from excalidraw_svg_to_lib.svg.path_sampling import path_commands_to_points


class TestPathCommandsToPoints:
    def test_simple_line_path(self) -> None:
        subpaths = path_commands_to_points("M 0 0 L 10 10")
        assert len(subpaths) == 1
        assert len(subpaths[0]) == 2
        assert subpaths[0][0] == (0.0, 0.0)
        assert subpaths[0][1] == (10.0, 10.0)

    def test_move_then_line(self) -> None:
        subpaths = path_commands_to_points("M 5 5 L 15 15 L 25 5")
        assert len(subpaths) == 1
        assert len(subpaths[0]) == 3

    def test_multiple_subpaths(self) -> None:
        subpaths = path_commands_to_points("M 0 0 L 10 10 M 20 20 L 30 30")
        assert len(subpaths) == 2
        assert len(subpaths[0]) == 2
        assert len(subpaths[1]) == 2

    def test_cubic_bezier_produces_sampled_points(self) -> None:
        subpaths = path_commands_to_points("M 0 0 C 10 0, 90 0, 100 0")
        assert len(subpaths) == 1
        # 1 start (Move) + 8 sampled points
        assert len(subpaths[0]) == 9

    def test_quadratic_bezier_produces_sampled_points(self) -> None:
        subpaths = path_commands_to_points("M 0 0 Q 50 50 100 0")
        assert len(subpaths) == 1
        # 1 start (Move) + 8 sampled points
        assert len(subpaths[0]) == 9

    def test_close_path_repeats_first_point(self) -> None:
        subpaths = path_commands_to_points("M 0 0 L 10 0 L 10 10 Z")
        assert len(subpaths) == 1
        # M, L, L, then Z appends first point
        assert subpaths[0][0] == subpaths[0][-1]

    def test_single_move_produces_no_subpath(self) -> None:
        subpaths = path_commands_to_points("M 0 0")
        # A subpath needs at least 2 points
        assert len(subpaths) == 0

    def test_absolute_coordinates(self) -> None:
        subpaths = path_commands_to_points("M 100 200 L 300 400")
        assert subpaths[0][0] == (100.0, 200.0)
        assert subpaths[0][1] == (300.0, 400.0)

    def test_arc_produces_sampled_points(self) -> None:
        subpaths = path_commands_to_points(
            "M 10 50 A 40 40 0 0 1 90 50"
        )
        assert len(subpaths) == 1
        # 1 start (Move) + adaptively-sampled arc points (180° arc → ~16 samples)
        assert len(subpaths[0]) >= 9

    def test_complex_path_with_multiple_segments(self) -> None:
        subpaths = path_commands_to_points("M 0 0 L 50 0 C 50 20, 80 20, 80 50 L 80 100")
        assert len(subpaths) == 1
        # M(1) + L(1) + C(8 samples) + L(1) = 11
        assert len(subpaths[0]) == 11

    def test_empty_path_data(self) -> None:
        subpaths = path_commands_to_points("")
        assert len(subpaths) == 0

    def test_close_after_move_repeats_start(self) -> None:
        subpaths = path_commands_to_points("M 5 5 Z")
        # Z closes back to the Move start; but needs >= 2 points for a subpath
        assert len(subpaths) == 1
        assert subpaths[0][0] == (5.0, 5.0)
        assert subpaths[0][-1] == (5.0, 5.0)
