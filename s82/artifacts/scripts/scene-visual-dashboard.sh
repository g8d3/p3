#!/usr/bin/env bash
# scene-visual-dashboard.sh — Shows dashboard API on :0
export DISPLAY="${DISPLAY:-:0}"
while true; do
  clear
  echo "=== DASHBOARD API :9093 ==="
  echo ""
  curl -s http://localhost:9093/api/team 2>/dev/null | python3 -m json.tool 2>/dev/null | head -35
  echo ""
  echo "=== $(date +%H:%M:%S) ==="
  sleep 3
done