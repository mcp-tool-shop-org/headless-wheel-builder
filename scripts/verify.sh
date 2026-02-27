#!/usr/bin/env bash
# verify.sh — Run all checks in one command (Shipcheck D.1)
set -euo pipefail

echo "=== Lint ==="
ruff check src tests

echo "=== Format check ==="
ruff format --check src tests

echo "=== Type check ==="
pyright src

echo "=== Tests ==="
pytest tests/unit -q

echo "=== Build ==="
python -m build --wheel --no-isolation 2>/dev/null || python -m build --wheel

echo ""
echo "All checks passed."
