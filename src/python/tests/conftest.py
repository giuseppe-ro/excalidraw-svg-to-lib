import random
from pathlib import Path

import pytest

from excalidraw_svg_to_lib.id_generator import IdGenerator

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SVG_DIR = REPO_ROOT / "svg"


@pytest.fixture
def fixed_ids() -> IdGenerator:
    return IdGenerator(rng=random.Random(42))
