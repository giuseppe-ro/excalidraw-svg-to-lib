#!/usr/bin/env bash
set -euo pipefail

# --- Shared helpers (source from other scripts) ---
# Use BASH_SOURCE[0] so PROJECT_ROOT is correct whether this file is
# sourced from scripts/ siblings or from the project root (convert.sh).
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"

# Detect python — prefer python, fall back to python3
if command -v python &>/dev/null; then
  PYTHON=python
elif command -v python3 &>/dev/null; then
  PYTHON=python3
else
  echo "ERROR: Neither 'python' nor 'python3' found. Please install Python >= 3.11." >&2
  exit 1
fi

# Setup venv locally; skip on CI (GITHUB_ACTIONS env var is set by GitHub runner)
if [[ -z "${GITHUB_ACTIONS:-}" ]]; then
  if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
    echo "Creating virtual environment (.venv)..."
    "$PYTHON" -m venv "$PROJECT_ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.venv/bin/activate"
fi
