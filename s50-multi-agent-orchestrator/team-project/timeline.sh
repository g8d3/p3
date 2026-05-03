#!/usr/bin/env bash
set -euo pipefail

# Timeline en tiempo real - se actualiza mientras los agentes trabajan
# Uso: ./timeline.sh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMELINE="$PROJECT_DIR/.timeline"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

declare -A ICONS=(
    [START]="🚀"
    [WORKING]="⚙️"
    [DONE]="✅"
    [ERROR]="❌"
    [STOPPED]="🛑"
)

declare -A AGENT_COLORS=(
    [html]="\033[38;5;208m"   # naranja
    [css]="\033[38;5;39m"     # azul
    [js]="\033[38;5;226m"     # amarillo
    [tests]="\033[38;5;135m"  # violeta
    [docs]="\033[38;5;46m"    # verde
)

trap 'echo -e "\n${YELLOW}Timeline detenido${NC}"; exit 0' INT

# Limpiar pantalla y mostrar timeline
render() {
    clear
    
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           ⏱️  TIMELINE EN TIEMPO REAL                        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [[ ! -f "$TIMELINE" ]] || [[ ! -s "$TIMELINE" ]]; then
        echo -e "  ${DIM}Esperando agentes...${NC}"
        echo ""
        echo -e "  Ejecuta ${BOLD}./launch.sh start${NC} para comenzar"
        return
    fi
    
    # Leer timeline y agrupar por agente
    declare -A AGENT_STATUS
    declare -A AGENT_START
    declare -A AGENT_END
    declare -A AGENT_LAST_MSG
    
    local first_ts=""
    
    while IFS='|' read -r ts time_str agent status msg; do
        [[ -z "$ts" ]] && continue
        
        if [[ -z "$first_ts" ]]; then
            first_ts="$ts"
        fi
        
        AGENT_STATUS["$agent"]="$status"
        AGENT_LAST_MSG["$agent"]="$msg"
        
        if [[ "$status" == "START" ]]; then
            AGENT_START["$agent"]="$ts"
        fi
        AGENT_END["$agent"]="$ts"
    done < "$TIMELINE"
    
    # Calcular tiempo total
    local now
    now=$(date +%s%N | cut -c1-13)
    local elapsed=$(( (now - first_ts) / 1000 ))
    
    echo -e "  ${DIM}Tiempo transcurrido: ${elapsed}s${NC}"
    echo ""
    
    # Barra de progreso visual
    local bar_width=50
    
    for agent in html css js tests docs; do
        local status="${AGENT_STATUS[$agent]:-idle}"
        local msg="${AGENT_LAST_MSG[$agent]:-}"
        local color="${AGENT_COLORS[$agent]}"
        local start_ts="${AGENT_START[$agent]:-}"
        local end_ts="${AGENT_END[$agent]:-}"
        
        # Calcular duración
        local duration=""
        if [[ -n "$start_ts" ]] && [[ -n "$end_ts" ]]; then
            duration="$(( (end_ts - start_ts) / 1000 ))s"
        fi
        
        # Icono según estado
        local icon
        case "$status" in
            START)    icon="🚀" ;;
            WORKING)  icon="⚙️" ;;
            DONE)     icon="✅" ;;
            ERROR)    icon="❌" ;;
            STOPPED)  icon="🛑" ;;
            *)        icon="⚪" ;;
        esac
        
        # Barra de progreso
        local bar=""
        if [[ "$status" == "WORKING" ]]; then
            # Animación de progreso
            local pos=$(( (elapsed % 10) * bar_width / 10 ))
            for ((i=0; i<bar_width; i++)); do
                if [[ $i -eq $pos ]]; then
                    bar+="█"
                elif [[ $(( (i + 2) % 5 )) -eq 0 ]]; then
                    bar+="░"
                else
                    bar+="─"
                fi
            done
        elif [[ "$status" == "DONE" ]]; then
            bar=$(printf '█%.0s' $(seq 1 $bar_width))
        elif [[ "$status" == "ERROR" ]]; then
            bar=$(printf '▓%.0s' $(seq 1 $bar_width))
        else
            bar=$(printf '─%.0s' $(seq 1 $bar_width))
        fi
        
        # Mostrar línea del agente
        echo -e "  ${color}${BOLD}$icon $agent${NC}"
        echo -e "  ${color}  │${bar}│${NC}"
        echo -e "  ${DIM}  │  $msg${NC}"
        [[ -n "$duration" ]] && echo -e "  ${DIM}  │  ⏱️ $duration${NC}"
        echo ""
    done
    
    # Resumen
    local done_count=0
    local running_count=0
    local error_count=0
    
    for agent in html css js tests docs; do
        case "${AGENT_STATUS[$agent]:-}" in
            DONE) ((done_count++)) ;;
            WORKING|START) ((running_count++)) ;;
            ERROR) ((error_count++)) ;;
        esac
    done
    
    echo -e "  ${CYAN}────────────────────────────────────────────────${NC}"
    echo -e "  Completados: ${GREEN}$done_count${NC}  │  En progreso: ${YELLOW}$running_count${NC}  │  Errores: ${RED}$error_count${NC}"
    echo ""
    echo -e "  ${DIM}Ctrl+C para salir${NC}"
}

# Loop principal
while true; do
    render
    sleep 1
done
