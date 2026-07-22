# SVG to Excalidraw Library

Convert SVG icons into Excalidraw `.excalidrawlib` files.

## Project layout

```
src/python/      Python converter (package + tests)
svg/             Source icons
```

## Quick start

The `convert.sh` script creates a virtual environment, installs dependencies, and runs the converter in one step:

```bash
# Default: convert svg/ → library.excalidrawlib
./convert.sh

# Custom input and output
./convert.sh -i svg/ -o my-icons.excalidrawlib
```

## Python

```bash
cd src/python
pip install -e ".[dev]"
pytest
python -m excalidraw_svg_to_lib ../../svg/ -o ../../icons.excalidrawlib
```

## Inputs

Each CLI accepts:

- individual files (`.svg`)
- a directory (all supported icons in that folder, non-recursive)

Examples:

```bash

# Python (from src/python)
python -m excalidraw_svg_to_lib ../../svg/ -o ../../aws-icons.excalidrawlib
```
