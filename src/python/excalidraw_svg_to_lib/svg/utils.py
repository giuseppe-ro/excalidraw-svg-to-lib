from __future__ import annotations

from typing import Any


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def parse_length(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    return float(value.replace("px", ""))


def is_url_ref(value: str | None) -> bool:
    """Return ``True`` if *value* is a ``url(#...)`` reference (gradient, pattern, etc.)."""
    return bool(value and value.strip().startswith("url("))


def normalize_color(color: str | None) -> str:
    if not color or color == "none":
        return "transparent"
    return color


def _map_dasharray(dasharray: str | None) -> str | None:
    """Map an SVG ``stroke-dasharray`` to an Excalidraw ``strokeStyle``.

    Returns ``"dashed"`` for simple dash patterns, ``"dotted"`` for very
    short dash + gap pairs, and ``None`` when no mapping is possible.
    """
    if not dasharray or dasharray == "none":
        return None
    parts = [float(n) for n in dasharray.replace(",", " ").split() if n]
    if not parts:
        return None
    # Dotted: very short dash with any gap (e.g. "1 4" or "2 2")
    if parts[0] <= 2 and all(p > 0 for p in parts):
        return "dotted"
    # Dashed: longer dashes with gaps
    if any(p > 2 for p in parts):
        return "dashed"
    return None


def inherit_style(parent_style: dict[str, Any], attributes: dict[str, str]) -> dict[str, Any]:
    style = dict(parent_style)

    if "fill" in attributes:
        style["fill"] = normalize_color(attributes["fill"])
    if "stroke" in attributes:
        style["stroke"] = normalize_color(attributes["stroke"])
    if "stroke-width" in attributes:
        style["stroke_width"] = float(attributes["stroke-width"])
    if "opacity" in attributes:
        style["opacity"] = float(attributes["opacity"]) * 100
    if "fill-rule" in attributes:
        style["fill_rule"] = attributes["fill-rule"]
    if "stroke-dasharray" in attributes:
        mapped = _map_dasharray(attributes["stroke-dasharray"])
        if mapped is not None:
            style["strokeStyle"] = mapped
    if "stroke-linecap" in attributes:
        style["stroke_linecap"] = attributes["stroke-linecap"]
    if "stroke-linejoin" in attributes:
        style["stroke_linejoin"] = attributes["stroke-linejoin"]

    return style
