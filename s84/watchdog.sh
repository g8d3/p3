#!/bin/bash
# Watchdog via LLM Proxy — detecta estado por actividad de API
PROXY_HEALTH="http://localhost:9098/health"
LOG_FILE="/tmp/watchdog.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

remind() {
    local w=$1 msg=$2
    log "→ $w: $msg"
    tmux send-keys -t "$w" Enter
    sleep 0.3
    tmux send-keys -t "$w" "$msg" Enter
}

log "Watchdog v3 (proxy) iniciado — ciclo 10s"

while true; do
    # Consultar proxy para estado de cada agente
    state=$(curl -s "$PROXY_HEALTH" 2>/dev/null || echo "{}")
    
    # Extraer idle states
    s84_idle=$(echo "$state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('opencode',{}).get('idle',False))" 2>/dev/null)
    evol_idle=$(echo "$state" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('crush',{}).get('idle',False))" 2>/dev/null)
    
    log "  s84 idle=$s84_idle | evol idle=$evol_idle"
    
    if [ "$s84_idle" = "True" ] && [ "$evol_idle" = "True" ]; then
        log "🔄 Ambos idle — conectando"
        tmux send-keys -t evol-trading "Revisa shared-bridge/ y continua trabajando." Enter
        sleep 1
        remind s84 "El otro agente sigue trabajando. Revisa shared-bridge/."
    elif [ "$s84_idle" = "True" ]; then
        remind s84 "Sigue trabajando. Revisa shared-bridge/."
    elif [ "$evol_idle" = "True" ]; then
        remind evol-trading "Sigue trabajando. Revisa shared-bridge/."
    fi
    
    sleep 10
done
