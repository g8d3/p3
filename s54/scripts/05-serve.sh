#!/usr/bin/env bash
# 05-serve.sh — Start dtale + static HTTP server
# Usage: ./05-serve.sh [csv-file]
#   Default: gh_search_results.csv
#
# Starts:
#   - D-Tale on port 8080 (CSV explorer)
#   - HTTP server on port 9090 (review page, READMEs)

set -euo pipefail
cd "$(dirname "$0")/.."

CSV="${1:-gh_search_results.csv}"
DTALE_PORT="${DTALE_PORT:-8080}"
HTTP_PORT="${HTTP_PORT:-9090}"

if [[ ! -f "$CSV" ]]; then
  echo "✗ CSV not found: $CSV"
  exit 1
fi

# Kill existing servers (with timeout to avoid hanging)
timeout 3 bash -c "kill \$(lsof -ti :$DTALE_PORT) 2>/dev/null" || true
timeout 3 bash -c "kill \$(lsof -ti :$HTTP_PORT) 2>/dev/null" || true
sleep 1

# Start D-Tale
echo "→ Starting D-Tale on port $DTALE_PORT ..."
DTALE_BIN=""
if command -v dtale &>/dev/null; then
  DTALE_BIN="dtale"
elif [ -f ".venv/bin/dtale" ]; then
  DTALE_BIN=".venv/bin/dtale"
fi

if [ -n "$DTALE_BIN" ]; then
  nohup "$DTALE_BIN" --csv-path "$CSV" --host 0.0.0.0 --port "$DTALE_PORT" &>/tmp/dtale.log &
  disown
  sleep 2
  if curl -s -o /dev/null -w '' http://localhost:$DTALE_PORT 2>/dev/null; then
    echo "  ✓ D-Tale: http://localhost:$DTALE_PORT"
  else
    echo "  ⚠ D-Tale may not be running (check /tmp/dtale.log)"
  fi
else
  echo "  ⚠ dtale not installed. Install with: uv pip install dtale"
  echo "    Or activate venv: source .venv/bin/activate"
fi

# Start HTTP server for review page
echo "→ Starting HTTP server on port $HTTP_PORT ..."
nohup python3 -m http.server "$HTTP_PORT" --bind 0.0.0.0 &>/tmp/httpserver.log &
disown
sleep 1
echo "  ✓ HTTP: http://localhost:$HTTP_PORT"
echo ""
echo "  Review page: http://localhost:$HTTP_PORT/review.html"
echo "  D-Tale:      http://localhost:$DTALE_PORT"
echo ""
echo "  Stop with: pkill -f 'dtale.*$DTALE_PORT'; pkill -f 'http.server $HTTP_PORT'"
