#!/bin/bash
# Watchdog — mantiene a los agentes trabajando
# Revisa cada N segundos si están activos, los empuja si están idle

BUSY_FILE="/tmp/watchdog-busy.txt"
LAST_PUSH="/tmp/watchdog-last-push.txt"
WINDOWS=("s84" "evol-trading")
BRIDGE="/home/vuos/code/p3/s84/shared-bridge"

# Tiempo máximo sin actividad antes de empujar (segundos)
MAX_IDLE=30

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

is_busy() {
    local win="$1"
    local pane
    pane=$(tmux capture-pane -t "$win" -p 2>/dev/null)
    # Si está pensando (muestra indicador de carga)
    if echo "$pane" | grep -qE '⠙|⠹|⠸|⠼|⠴|⠦|⠧|Thinking|Preparing|Writing'; then
        return 0  # busy
    fi
    # Si está en prompt vacío (idle)
    if echo "$pane" | grep -qE '>:::|> Build|> orchestrator|> Plan'; then
        return 1  # idle
    fi
    return 0  # asumir busy si no podemos determinar
}

get_age() {
    local key="$1"
    if [ -f "$LAST_PUSH" ]; then
        local last=$(grep "^$key:" "$LAST_PUSH" 2>/dev/null | cut -d: -f2)
        echo $(( $(date +%s) - ${last:-0} ))
    else
        echo 999
    fi
}

mark_pushed() {
    local key="$1"
    if [ -f "$LAST_PUSH" ]; then
        sed -i "/^$key:/d" "$LAST_PUSH"
    fi
    echo "$key:$(date +%s)" >> "$LAST_PUSH"
}

remind_agent() {
    local win="$1" msg="$2"
    log "📢 Recordatorio a $win: $msg"
    tmux send-keys -t "$win" Enter
    sleep 0.3
    tmux send-keys -t "$win" "$msg" Enter
    mark_pushed "$win"
}

check_discoveries() {
    local new_discoveries
    new_discoveries=$(find "$BRIDGE/discoveries" -name "*.md" -newer "$BUSY_FILE" 2>/dev/null | wc -l)
    if [ "$new_discoveries" -gt 0 ]; then
        log "🔍 $new_discoveries descubrimientos nuevos encontrados"
        return 0
    fi
    return 1
}

# Inicializar
touch "$BUSY_FILE"
log "🐶 Watchdog iniciado — revisando cada 10s"

while true; do
    both_idle=true
    
    for win in "${WINDOWS[@]}"; do
        if is_busy "$win"; then
            both_idle=false
            log "  $win: ocupado"
        else
            local age=$(get_age "$win")
            log "  $win: idle (${age}s)"
            
            # Si está idle por más de MAX_IDLE segundos, empujar
            if [ "$age" -gt "$MAX_IDLE" ]; then
                if [ "$win" = "s84" ]; then
                    remind_agent "$win" "Revisa shared-bridge/discoveries/ y construye sobre lo que encuentres."
                elif [ "$win" = "evol-trading" ]; then
                    remind_agent "$win" "Hay descubrimientos nuevos. Revisa shared-bridge/ y mejora evolve.py."
                fi
            fi
        fi
    done

    # Si ambos están idle por mucho tiempo, iniciar interacción
    if [ "$both_idle" = true ]; then
        local age_s84=$(get_age "s84")
        local age_evol=$(get_age "evol-trading")
        if [ "$age_s84" -gt 60 ] && [ "$age_evol" -gt 60 ]; then
            log "🔄 Ambos idle por >60s — iniciando interacción"
            # s84 le pregunta a evol-trading qué ha hecho
            tmux send-keys -t evol-trading Enter
            sleep 0.3
            tmux send-keys -t evol-trading "¿Cómo va evolve.py? ¿Encontraste algo nuevo? Comparte en shared-bridge/." Enter
            mark_pushed "evol-trading"
            sleep 2
            # Luego s84 se pone a trabajar también
            remind_agent "s84" "Revisa los ultimos resultados en 04-evolucion-trading/resultados/ y mejora algo."
        fi
    fi

    # Nuevo descubrimiento: avisar al otro agente
    if check_discoveries; then
        remind_agent "evol-trading" "Nuevo descubrimiento disponible. Revisalo y construye encima."
    fi

    # Actualizar timestamp
    touch "$BUSY_FILE"
    sleep 10
done
