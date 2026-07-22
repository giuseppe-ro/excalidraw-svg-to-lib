from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ConvertOptions:
    normalize: bool = True
    add_label: bool = True
    id_factory: Callable[[], str] | None = None
    int_factory: Callable[[], int] | None = None
