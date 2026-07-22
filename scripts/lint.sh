#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

cd "$PROJECT_ROOT/src/python"

flake8 . --count --show-source --statistics
