#!/usr/bin/env bash
# ElohimOS Development Sanity Checks
# Runs import validation and backend tests before committing changes

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Running import validation..."
cd "$ROOT_DIR"
python3 scripts/check_imports.py

echo
echo "==> Running backend tests..."
cd "$ROOT_DIR/apps/backend"
export PYTHONPATH="$ROOT_DIR/packages:$ROOT_DIR/apps/backend:${PYTHONPATH:-}"
"$ROOT_DIR/venv/bin/python3" -m pytest tests/

echo
echo "✅ All dev checks passed!"
