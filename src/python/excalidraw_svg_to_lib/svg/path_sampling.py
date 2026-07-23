from __future__ import annotations

from svg.path import Arc, Close, CubicBezier, Line, Move, Path, QuadraticBezier, parse_path

from excalidraw_svg_to_lib.constants import CURVE_SAMPLES
from excalidraw_svg_to_lib.elements import Point


def _complex_to_point(value: complex) -> Point:
    return (value.real, value.imag)


def _sample_cubic(
    start: Point,
    control1: Point,
    control2: Point,
    end: Point,
    samples: int = CURVE_SAMPLES,
) -> list[Point]:
    points: list[Point] = []
    for index in range(1, samples + 1):
        t = index / samples
        mt = 1 - t
        x = (
            mt**3 * start[0]
            + 3 * mt**2 * t * control1[0]
            + 3 * mt * t**2 * control2[0]
            + t**3 * end[0]
        )
        y = (
            mt**3 * start[1]
            + 3 * mt**2 * t * control1[1]
            + 3 * mt * t**2 * control2[1]
            + t**3 * end[1]
        )
        points.append((x, y))
    return points


def _sample_quadratic(
    start: Point,
    control: Point,
    end: Point,
    samples: int = CURVE_SAMPLES,
) -> list[Point]:
    points: list[Point] = []
    for index in range(1, samples + 1):
        t = index / samples
        mt = 1 - t
        x = mt**2 * start[0] + 2 * mt * t * control[0] + t**2 * end[0]
        y = mt**2 * start[1] + 2 * mt * t * control[1] + t**2 * end[1]
        points.append((x, y))
    return points


def path_commands_to_points(path_data: str) -> list[list[Point]]:
    parsed_path: Path = parse_path(path_data)
    subpaths: list[list[Point]] = []
    current: list[Point] = []
    cursor: Point = (0.0, 0.0)

    def push_current() -> None:
        nonlocal current
        if len(current) >= 2:
            subpaths.append(current)
        current = []

    for segment in parsed_path:
        if isinstance(segment, Move):
            push_current()
            cursor = _complex_to_point(segment.end)
            current.append(cursor)
        elif isinstance(segment, Line):
            cursor = _complex_to_point(segment.end)
            current.append(cursor)
        elif isinstance(segment, CubicBezier):
            sampled = _sample_cubic(
                cursor,
                _complex_to_point(segment.control1),
                _complex_to_point(segment.control2),
                _complex_to_point(segment.end),
            )
            current.extend(sampled)
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, QuadraticBezier):
            sampled = _sample_quadratic(
                cursor,
                _complex_to_point(segment.control),
                _complex_to_point(segment.end),
            )
            current.extend(sampled)
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, Arc):
            for index in range(1, CURVE_SAMPLES + 1):
                point = segment.point(index / CURVE_SAMPLES)
                current.append(_complex_to_point(point))
            cursor = _complex_to_point(segment.end)
        elif isinstance(segment, Close):
            if current:
                current.append(current[0])

    push_current()
    return subpaths
