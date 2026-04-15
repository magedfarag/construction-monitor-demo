#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
  python -m venv "$ROOT_DIR/.venv"
fi

"$VENV_PYTHON" -m pip install -r "$ROOT_DIR/requirements.txt"
exec "$VENV_PYTHON" -m uvicorn app.main:app --reload
