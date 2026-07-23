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
# Default: convert svg/ → output.excalidrawlib (v2 format, searchable)
./convert.sh

# Custom input and output
./convert.sh -i svg/ -o my-icons.excalidrawlib

# Append new icons to an existing library
./convert.sh -i new-icons/ -a my-icons.excalidrawlib
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
- a directory (all `.svg` files in that folder, non-recursive)

Files with unsupported extensions are **skipped with a warning** — the converter
continues processing any valid `.svg` files in the same batch.

```bash
# Mix of valid and invalid files — valid SVGs are converted, others warned
python -m excalidraw_svg_to_lib icon.svg logo.png data.json -o icons.excalidrawlib
# WARN: skipping unsupported file 'logo.png'
# WARN: skipping unsupported file 'data.json'
# Converted icon.svg -> 5 element(s)
# Wrote icons.excalidrawlib (1 library item(s))
```

## Appending to an existing library

Use `--append` to add new icons to an existing `.excalidrawlib` without replacing it:

```bash
# Append new-icons/ to an existing library (writes back to the same file)
python -m excalidraw_svg_to_lib new-icons/ --append icons.excalidrawlib

# Append and write to a different file
python -m excalidraw_svg_to_lib new-icons/ --append icons.excalidrawlib -o merged.excalidrawlib
```

Works with both v1 and v2 library formats, including cross-format merges.

## CLI Options

| Flag | Default | Description |
|---|---|---|
| `-o`, `--output` | auto | Output `.excalidrawlib` file path |
| `--append` | — | Append to an existing library file |
| `--no-normalize` | normalize | Keep original SVG coordinates |
| `--no-label` | add labels | Skip filename labels below icons |
| `--no-scale` | scale to target | Keep original icon dimensions |
| `--target-size` | `64` | Scale icons to this max dimension |
| `--v1` | v2 | Use legacy v1 library format |

### Shell script

The `convert.sh` script supports passing extra flags through:

```bash
./convert.sh -i svg/ -o icons.excalidrawlib --no-scale --no-label
```

## Output formats

### v2 — Searchable library items (default)

By default, the tool outputs Excalidraw's v2 `libraryItems` format. Each icon gets a
`name` field derived from the filename, making icons **searchable by name** in the
Excalidraw library panel:

```json
{
  "type": "excalidrawlib",
  "version": 2,
  "libraryItems": [
    {
      "id": "...",
      "status": "published",
      "name": "lambda",
      "elements": [...]
    }
  ]
}
```

### v1 — Legacy format

Use `--v1` to produce the older `library` array format (no per-item names):

```bash
python -m excalidraw_svg_to_lib svg/ -o icons.excalidrawlib --v1
```
