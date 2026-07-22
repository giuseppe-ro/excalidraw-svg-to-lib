from __future__ import annotations

import math
import re
from typing import Any

# 2D affine transform stored as (a, b, c, d, e, f).
# Applied to a point (x, y):
#   x' = a*x + c*y + e
#   y' = b*x + d*y + f
#
# Matrix form:
#   [ a  c  e ]
#   [ b  d  f ]
#   [ 0  0  1 ]
Transform = tuple[float, float, float, float, float, float]
IDENTITY: Transform = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_number_list(text: str) -> list[float]:
    """Parse comma- or space-separated numbers from a transform argument string."""
    return [float(n) for n in re.split(r"[,\s]+", text.strip()) if n]


def _make_transform(a: float, b: float, c: float, d: float, e: float, f: float) -> Transform:
    return (a, b, c, d, e, f)


def _parse_transform_func(func: str, args_str: str) -> Transform | None:
    """Parse a transform function name and its arguments into a matrix."""
    func = func.strip().lower()

    if func == "translate":
        vals = _parse_number_list(args_str)
        tx = vals[0] if len(vals) > 0 else 0.0
        ty = vals[1] if len(vals) > 1 else 0.0
        return _make_transform(1, 0, 0, 1, tx, ty)

    elif func == "scale":
        vals = _parse_number_list(args_str)
        sx = vals[0] if len(vals) > 0 else 1.0
        sy = vals[1] if len(vals) > 1 else sx
        return _make_transform(sx, 0, 0, sy, 0, 0)

    elif func == "rotate":
        vals = _parse_number_list(args_str)
        angle = math.radians(vals[0])
        cx = vals[1] if len(vals) > 1 else 0.0
        cy = vals[2] if len(vals) > 2 else 0.0
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # rotate(angle, cx, cy) = translate(cx, cy) ∘ rotate(angle) ∘ translate(-cx, -cy)
        return _make_transform(
            cos_a, sin_a,
            -sin_a, cos_a,
            cx - cx * cos_a + cy * sin_a,
            cy - cx * sin_a - cy * cos_a,
        )

    elif func == "matrix":
        vals = _parse_number_list(args_str)
        if len(vals) < 6:
            return None
        return _make_transform(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5])

    elif func == "skewx":
        vals = _parse_number_list(args_str)
        angle = math.radians(vals[0]) if vals else 0.0
        return _make_transform(1, 0, math.tan(angle), 1, 0, 0)

    elif func == "skewy":
        vals = _parse_number_list(args_str)
        angle = math.radians(vals[0]) if vals else 0.0
        return _make_transform(1, math.tan(angle), 0, 1, 0, 0)

    return None  # Unknown transform function


def _parse_single_transform(text: str) -> Transform | None:
    """Parse a single transform function like ``translate(10, 20)``."""
    paren_idx = text.index("(")
    func = text[:paren_idx]
    args_str = text[paren_idx + 1:].rstrip(")")
    return _parse_transform_func(func, args_str)


# Regex to match individual transform functions like "translate(10, 20)"
_TRANSFORM_FUNC_RE = re.compile(r"(\w+)\s*\(([^)]*)\)")


def parse_transform(value: str) -> Transform | None:
    """Parse an SVG ``transform`` attribute into a composed transform matrix.

    Supports ``translate``, ``scale``, ``rotate``, ``matrix``, ``skewX``,
    and ``skewY``.  Multiple functions are composed left-to-right as per
    the SVG spec (the leftmost transform is applied first to the coordinate
    system, meaning it is the *outer* transform in the final composition).
    """
    if not value or not value.strip():
        return None

    transforms: list[Transform] = []
    for match in _TRANSFORM_FUNC_RE.finditer(value):
        t = _parse_transform_func(match.group(1), match.group(2))
        if t is not None:
            transforms.append(t)

    if not transforms:
        return None

    # SVG spec: transforms are applied left-to-right, which means
    # the leftmost is the outermost in composition.
    # compose(outer, inner) applies inner first, then outer.
    result = transforms[0]
    for t in transforms[1:]:
        result = compose(result, t)
    return result


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def compose(t1: Transform, t2: Transform) -> Transform:
    """Compose two transforms: result = t1 ∘ t2.

    ``t2`` is applied first, then ``t1``.
    """
    a1, b1, c1, d1, e1, f1 = t1
    a2, b2, c2, d2, e2, f2 = t2
    return _make_transform(
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


# ---------------------------------------------------------------------------
# Apply to points
# ---------------------------------------------------------------------------


def apply_to_point(transform: Transform, x: float, y: float) -> tuple[float, float]:
    """Apply a transform to a single point."""
    a, b, c, d, e, f = transform
    return (a * x + c * y + e, b * x + d * y + f)


# ---------------------------------------------------------------------------
# Apply to elements
# ---------------------------------------------------------------------------


def apply_transform_to_element(transform: Transform, element: dict[str, Any]) -> None:
    """Apply a transform to an Excalidraw element in-place.

    Transforms the element's position and dimensions by mapping the
    bounding box corners through the transform and recomputing the AABB.
    For line elements with a ``points`` array, each absolute point is
    transformed and the relative points are recomputed.
    """
    if transform == IDENTITY:
        return

    x = element["x"]
    y = element["y"]
    w = element["width"]
    h = element["height"]

    # Transform all four corners of the bounding box
    corners = [
        apply_to_point(transform, x, y),
        apply_to_point(transform, x + w, y),
        apply_to_point(transform, x, y + h),
        apply_to_point(transform, x + w, y + h),
    ]

    new_min_x = min(p[0] for p in corners)
    new_min_y = min(p[1] for p in corners)
    new_max_x = max(p[0] for p in corners)
    new_max_y = max(p[1] for p in corners)

    element["x"] = new_min_x
    element["y"] = new_min_y
    element["width"] = new_max_x - new_min_x
    element["height"] = new_max_y - new_min_y

    # Transform points array for line elements
    points = element.get("points")
    if points:
        absolute = [(x + px, y + py) for px, py in points]
        transformed = [apply_to_point(transform, ax, ay) for ax, ay in absolute]
        element["points"] = [
            [tx - new_min_x, ty - new_min_y] for tx, ty in transformed
        ]
