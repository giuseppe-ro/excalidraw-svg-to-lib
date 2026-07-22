from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from svg_to_excalidrawlib.constants import DEFAULT_TARGET_ICON_SIZE


@dataclass(frozen=True)
class ConvertOptions:
    normalize: bool = True
    add_label: bool = True
    scale_to_target: bool = True
    target_icon_size: float = DEFAULT_TARGET_ICON_SIZE
    id_factory: Callable[[], str] | None = None
    int_factory: Callable[[], int] | None = None
