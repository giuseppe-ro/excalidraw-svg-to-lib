# SVG to Excalidraw Library

Convert SVG icons into Excalidraw `.excalidrawlib` files.

## Project layout

```
src/python/      Python converter (package + tests)
svg/             Source SVG icons
scripts/         Shell helpers (setup, lint, test)
.github/         CI/CD workflows
```

## Quick start

**1. Put your SVG files in a folder.** The default location is the `svg/`
folder at the repo root — drop your `.svg` files there, in subfolders if you
like (the folder is scanned recursively).

**2. Run the converter from the repo root:**

```bash
./convert.sh
```

That's it. `convert.sh` sets up the environment, converts every `.svg` in
`svg/`, and writes **`output.excalidrawlib`** to the repo root. Import that
file in Excalidraw (Library panel → `⋯` → *Import library*) and the icons are
ready to use.

To convert a different folder, or control the output file:

```bash
./convert.sh -i path/to/your-icons/ -o my-icons.excalidrawlib
```

See [CLI Options](#cli-options) for the full flag list.

### Using the Python CLI directly

```bash
cd src/python
pip install -e ".[dev]"
pytest                                  # run the test suite
python -m excalidraw_svg_to_lib ../../svg/ -o ../../icons.excalidrawlib
```

## Inputs

Files with unsupported extensions are **skipped with a single aggregated
warning per run** — the converter continues processing any valid `.svg`
files in the same batch. Dotfiles and build artifacts (`.DS_Store`,
`Thumbs.db`, `package-lock.json`, etc.) are silently ignored.

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

All flags work with both `convert.sh` and `python -m excalidraw_svg_to_lib`:

| Flag | Default | Description |
|---|---|---|
| `inputs` | — | `.svg` files and/or directories (directories scanned recursively) |
| `-o`, `--output` | `output.excalidrawlib` (via `convert.sh`) / derived from input | Output `.excalidrawlib` file path |
| `--append` | — | Append converted icons to an existing `.excalidrawlib` |
| `--no-normalize` | normalize | Keep original SVG coordinates |
| `--no-label` | add labels | Skip filename labels below icons |
| `--no-scale` | scale to target | Keep original icon dimensions |
| `--target-size` | `64` | Scale icons so largest dimension matches this size |
| `--v1` | v2 | Use legacy v1 library format (no searchable names) |
| `--stroke-width` | from SVG | Override stroke width for all elements |

> **Note:** `convert.sh` also has shorthand `-i FOLDER` (input) and `-a FILE` (append),
> which it translates to `inputs` and `--append`. Use those when going through the script.

## Output formats

### v2 — Searchable library items (default)

By default, the tool outputs Excalidraw's v2 `libraryItems` format. Each icon gets a
`name` field derived from the filename, making icons **searchable by name** in the
Excalidraw library panel:

```json
{
  "type": "excalidrawlib",
  "version": 2,
  "source": "https://excalidraw.com",
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
