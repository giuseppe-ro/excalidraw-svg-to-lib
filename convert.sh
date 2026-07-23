#!/usr/bin/env bash
set -euo pipefail

# Defaults
INPUT="svg"
OUTPUT=""
APPEND=""

# Parse optional flags: -i (input folder), -o (output file), -a (append to existing library)
# Remaining args are passed through to the Python CLI (--no-scale, --stroke-width 2, etc.)
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) INPUT="$2"; shift 2 ;;
    -o) OUTPUT="$2"; shift 2 ;;
    -a) APPEND="$2"; shift 2 ;;
    -h|--help|-?)
      # Show Python CLI help and exit without converting
      SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
      source "$SCRIPT_DIR/scripts/common.sh"
      pip install -e "./src/python[dev]" --quiet 2>/dev/null
      python -m excalidraw_svg_to_lib --help
      exit 0
      ;;
    --*=*) EXTRA_ARGS+=("$1"); shift ;;            # --target-size=72 (value inline)
    --no-*) EXTRA_ARGS+=("$1"); shift ;;           # --no-label, --no-scale, --no-normalize (boolean flags)
    --version) EXTRA_ARGS+=("$1"); shift ;;
    --*)
      # Only consume next arg as a value if it doesn't look like a flag
      if [[ $# -gt 1 && "$2" != -* ]]; then
        EXTRA_ARGS+=("$1" "$2"); shift 2
      else
        EXTRA_ARGS+=("$1"); shift
      fi
      ;;
    *)  EXTRA_ARGS+=("$1"); shift ;;               # pass-through: positional paths, unknown flags, etc.
  esac
done

# Resolve output: user flag > append target > default
if [ -z "$OUTPUT" ]; then
  OUTPUT="${APPEND:-output.excalidrawlib}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/scripts/common.sh"

# Resolve relative paths to absolute before cd to project root
abs_path() { "$PYTHON" -c "import os, sys; print(os.path.abspath(sys.argv[1]))" "$1"; }
INPUT=$(abs_path "$INPUT")
OUTPUT=$(abs_path "$OUTPUT")
[ -n "$APPEND" ] && APPEND=$(abs_path "$APPEND")

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
