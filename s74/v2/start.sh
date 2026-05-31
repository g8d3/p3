#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"
echo "s74/v2 — starting..."
uv venv --python 3.12 "$VENV" 2>/dev/null || python3.12 -m venv "$VENV"
uv pip install --python "$VENV" httpx websockets 2>/dev/null || "$VENV/bin/pip" install -q httpx websockets
exec "$VENV/bin/python3" "$DIR/orchestrator.py"
