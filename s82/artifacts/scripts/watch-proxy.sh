#!/usr/bin/env bash
# watch-proxy.sh — Muestra estado del proxy health
export DISPLAY="${DISPLAY:-:0}"
while true; do
  clear
  echo "=== Proxy Health ==="
  curl -s http://localhost:9098/health 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for a,i in d.get('agents',{}).items():
    s=i.get('status','?')
    ls=i.get('last_s','?')
    idle=i.get('idle','?')
    print(f'  {a:20s} last_s={ls:4s} idle={str(idle):5s} status={s}')
" 2>/dev/null || echo "  (proxy unavailable)"
  sleep 3
done