# SVG to Excalidraw Library

Convert SVG and image icons into Excalidraw `.excalidrawlib` files.

## Project layout

```
src/python/      Python converter (package + tests)
svg/             Source icons
```

## Python

```bash
cd src/python
pip install -e ".[dev]"
pytest
python -m svg_to_excalidrawlib ../../svg/ -o ../../aws-icons.excalidrawlib
```

## Inputs

Each CLI accepts:

- individual files (`.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`)
- a directory (all supported icons in that folder, non-recursive)

Examples:

```bash

# Python (from src/python)
python -m svg_to_excalidrawlib ../../svg/ -o ../../aws-icons.excalidrawlib
```
