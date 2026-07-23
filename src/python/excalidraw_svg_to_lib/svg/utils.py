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


def normalize_color(color: str | None) -> str:
    if not color or color == "none":
        return "transparent"
    return color


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

    return style
