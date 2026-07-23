from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from excalidraw_svg_to_lib.constants import DEFAULT_TARGET_ICON_SIZE


@dataclass(frozen=True)
class ConvertOptions:
    normalize: bool = True
    add_label: bool = True
    scale_to_target: bool = True
    target_icon_size: float = DEFAULT_TARGET_ICON_SIZE
    format_version: Literal[1, 2] = 2
    stroke_width_override: float | None = None

    def __post_init__(self) -> None:
        if self.format_version not in (1, 2):
            raise ValueError(
                f"format_version must be 1 or 2, got {self.format_version}"
            )
