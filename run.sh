#!/bin/sh
# Run PV-Calc Pro using the project virtual environment.
# This ensures the correct Python and dependencies (imgui-bundle, numpy, etc.).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py"
