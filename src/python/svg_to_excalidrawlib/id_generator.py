from __future__ import annotations

import random
import string

from svg_to_excalidrawlib.options import ConvertOptions


class IdGenerator:
    def __init__(self, options: ConvertOptions | None = None) -> None:
        self._options = options or ConvertOptions()
        self._random = random.Random(0)

    def random_id(self) -> str:
        if self._options.id_factory is not None:
            return self._options.id_factory()
        alphabet = string.ascii_letters + string.digits + "_-"
        return "".join(self._random.choice(alphabet) for _ in range(21))

    def random_int(self, maximum: int = 2**31) -> int:
        if self._options.int_factory is not None:
            return self._options.int_factory()
        return self._random.randrange(maximum)
