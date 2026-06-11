#!/usr/bin/env bash
# scene-visual-proxy.sh — Shows proxy health on :0
export DISPLAY="${DISPLAY:-:0}"
while true; do
  clear
  echo "=== PROXY HEALTH :9098 ==="
  echo ""
  curl -s http://localhost:9098/health 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for a,i in d.get('agents',{}).items():
    ls=i.get('last_s',0)
    idle=i.get('idle',False)
    st=i.get('status','?')
    pid=i.get('pid',0)
    cpu=i.get('cpu',0)
    mem=i.get('mem_pct',0)
    print(f'  {a:20s} last_s={ls:<4s} idle={str(idle):5s} cpu={str(cpu):>5s}% mem={str(mem):>4s}%')
" 2>/dev/null || echo "  (proxy unavailable)"
  echo ""
  echo "=== $(date +%H:%M:%S) ==="
  sleep 3
done