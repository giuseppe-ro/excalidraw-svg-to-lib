#!/usr/bin/env bash
set -euo pipefail

# Resolve project root (directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Defaults
INPUT="svg"
OUTPUT=""
APPEND=""

# Parse optional flags: -i (input folder), -o (output file), -a (append to existing library)
# Remaining args are passed through to the Python CLI (--stroke-width 1, --no-scale, etc.)
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) INPUT="$2"; shift 2 ;;
    -o) OUTPUT="$2"; shift 2 ;;
    -a) APPEND="$2"; shift 2 ;;
    --*=*) EXTRA_ARGS+=("$1"); shift ;;            # --stroke-width=1 (value inline)
    --no-*) EXTRA_ARGS+=("$1"); shift ;;           # --no-label, --no-scale, --no-normalize (boolean flags)
    --*) EXTRA_ARGS+=("$1" "$2"); shift 2 ;;      # --stroke-width 1 (value separate)
    *)  echo "Usage: $0 [-i input_folder] [-o output_file] [-a append_library] [--extra-flags...]"; exit 1 ;;
  esac
done

# Resolve output: user flag > append target > default
if [ -z "$OUTPUT" ]; then
  OUTPUT="${APPEND:-output.excalidrawlib}"
fi

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

# 4. Build the command
CMD=(python -m excalidraw_svg_to_lib "$INPUT")
if [ -n "$APPEND" ]; then
  CMD+=(--append "$APPEND")
fi
CMD+=(-o "$OUTPUT")
CMD+=("${EXTRA_ARGS[@]:-}")

# 5. Run the converter
echo "Converting '$INPUT' → '$OUTPUT' ..."
"${CMD[@]}"

echo "Done — output written to $OUTPUT"
