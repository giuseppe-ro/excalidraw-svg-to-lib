#!/usr/bin/env bash
set -euo pipefail

# --- Install project dependencies ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

cd "$PROJECT_ROOT"
pip install -e "./src/python[dev]" --quiet
