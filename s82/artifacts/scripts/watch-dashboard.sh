#!/usr/bin/env bash
# watch-dashboard.sh — Muestra team del dashboard
export DISPLAY="${DISPLAY:-:0}"
while true; do
  clear
  echo "=== Dashboard Team ==="
  curl -s http://localhost:9093/api/team 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for a in d.get('team',[]):
    print(f'  {a[\"name\"]:20s} last_s={a[\"last_s\"]:4s} status={a[\"status\"]}')
" 2>/dev/null || echo "  (dashboard unavailable)"
  sleep 3
done