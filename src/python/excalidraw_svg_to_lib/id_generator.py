from __future__ import annotations

import random
import string


class IdGenerator:
    """Generate random IDs and integers for Excalidraw elements.

    Accepts a seeded ``random.Random`` instance for deterministic output
    (useful in tests).  Falls back to a fresh unseeded generator when
    ``rng`` is *None*.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._random = rng if rng is not None else random.Random()

    def random_id(self) -> str:
        alphabet = string.ascii_letters + string.digits + "_-"
        return "".join(self._random.choice(alphabet) for _ in range(21))

    def random_int(self, maximum: int = 2**31) -> int:
        return self._random.randrange(maximum)
