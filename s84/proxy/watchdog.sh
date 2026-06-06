#!/bin/bash
# Watchdog pasivo — solo monitorea y logea, no envía mensajes a tmux
PROXY_HEALTH="http://localhost:9098/health"
LOG_FILE="/tmp/watchdog.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "Watchdog pasivo iniciado — ciclo 10s"

while true; do
    state=$(curl -s "$PROXY_HEALTH" 2>/dev/null || echo "{}")

    s84_idle=$(echo "$state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('s84',{}).get('idle',d.get('opencode',{}).get('idle',False)))" 2>/dev/null)
    evol_idle=$(echo "$state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('evol-trading',{}).get('idle',d.get('crush',{}).get('idle',False)))" 2>/dev/null)

    log "s84 idle=$s84_idle | evol idle=$evol_idle"
    sleep 10
done
