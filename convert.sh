#!/usr/bin/env bash
set -euo pipefail

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
    --*=*) EXTRA_ARGS+=("$1"); shift ;;            # --target-size=72 (value inline)
    --no-*) EXTRA_ARGS+=("$1"); shift ;;           # --no-label, --no-scale, --no-normalize (boolean flags)
    --*) EXTRA_ARGS+=("$1" "$2"); shift 2 ;;      # --target-size 72 (value separate)
    *)  echo "Usage: $0 [-i input_folder] [-o output_file] [-a append_library] [--extra-flags...]"; exit 1 ;;
  esac
done

# Resolve output: user flag > append target > default
if [ -z "$OUTPUT" ]; then
  OUTPUT="${APPEND:-output.excalidrawlib}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/scripts/common.sh"

cd "$PROJECT_ROOT"

# Install dependencies
echo "Installing dependencies..."
pip install -e "./src/python[dev]" --quiet

# Build the command
CMD=(python -m excalidraw_svg_to_lib "$INPUT")
if [ -n "$APPEND" ]; then
  CMD+=(--append "$APPEND")
fi
CMD+=(-o "$OUTPUT")
if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
  CMD+=("${EXTRA_ARGS[@]}")
fi

# Run the converter
echo "Converting '$INPUT' → '$OUTPUT' ..."
"${CMD[@]}"

echo "Done — output written to $OUTPUT"
