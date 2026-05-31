#!/usr/bin/env bash
# s74 — Human-in-the-Loop System
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"

echo "╭──────────────────────────────────────────────╮"
echo "│  s74 • Human-in-the-Loop System              │"
echo "╰──────────────────────────────────────────────╯"
echo ""

# Create venv with uv (evita PEP 668 / ensurepip issues)
if [ ! -f "$VENV/bin/python" ]; then
    echo "→ Creating venv..."
    uv venv --python 3.12 "$VENV" 2>/dev/null || python3.12 -m venv "$VENV"
fi

# Install deps
echo "→ Installing deps..."
uv pip install --python "$VENV" httpx websockets 2>/dev/null || \
    "$VENV/bin/pip" install -q httpx websockets 2>/dev/null || true

echo "→ Starting server..."
echo ""
echo "  Config via env vars:"
echo "    BENCHMARK_INTERVAL  (default 600s, 0=disable)"
echo "    BENCHMARK_MODELS    (comma-separated, empty=all)"
echo ""
exec "$VENV/bin/python3" "$DIR/server.py"
