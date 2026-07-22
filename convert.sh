#!/usr/bin/env bash
set -euo pipefail

# Resolve project root (directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Defaults
INPUT="svg"
OUTPUT="library.excalidrawlib"

# Parse optional flags: -i (input folder) and -o (output file)
while getopts "i:o:" opt; do
  case "$opt" in
    i) INPUT="$OPTARG" ;;
    o) OUTPUT="$OPTARG" ;;
    *) echo "Usage: $0 [-i input_folder] [-o output_file]"; exit 1 ;;
  esac
done

# 1. Create .venv if not present
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

# 2. Activate .venv
source .venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies..."
pip install -e "src/python[dev]" --quiet

# 4. Run the converter
echo "Converting '$INPUT' → '$OUTPUT' ..."
python -m excalidraw_svg_to_lib "$INPUT" -o "$OUTPUT"

echo "Done — output written to $OUTPUT"
