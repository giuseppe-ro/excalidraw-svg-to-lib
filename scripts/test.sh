#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

cd "$PROJECT_ROOT/src/python"

pytest -v -ra --strict-config --strict-markers
