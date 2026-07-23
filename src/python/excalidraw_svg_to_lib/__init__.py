from importlib.metadata import PackageNotFoundError, version

from excalidraw_svg_to_lib.library import make_v2_item
from excalidraw_svg_to_lib.options import ConvertOptions
from excalidraw_svg_to_lib.runner import (
    convert_input_to_library,
    convert_svg_to_library,
)

try:
    __version__ = version("excalidraw-svg-to-lib")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ConvertOptions",
    "__version__",
    "convert_input_to_library",
    "convert_svg_to_library",
    "make_v2_item",
]
