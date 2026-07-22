#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=common.sh
source "$(dirname "$0")/common.sh"

cd "$PROJECT_ROOT/src/python"

echo "Upgrading pip..."
"$PYTHON" -m pip install --upgrade pip

echo "Installing dependencies..."
pip install -e ".[dev]"
pip install flake8

echo "Done — dependencies installed"
