#!/bin/bash
# 📊 Dashboard en vivo - Muestra qué hace cada agente AHORA
# Usa: bash tools/dashboard.sh
# Requiere: tmux, jq

SCRIPT_DIR="/home/vuos/code/p3/s51"
REPORTES_DIR="$SCRIPT_DIR/reportes"
SESION="main"

# Colores
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
ROJO='\033[0;31m'
GRIS='\033[0;90m'
BLANCO='\033[1;37m'
NEGRITA='\033[1m'
NC='\033[0m'

# Limpiar y ocultar cursor
tput civis
trap 'tput cnorm; exit 0' INT TERM

extraer_ultima_accion() {
    local ventana="$1"
    local lineas=$(tmux capture-pane -t "$SESION:$ventana" -p -S -30 2>/dev/null | grep -v '^\s*$' | grep -v '────────────────' | grep -v '^~' | tail -15)
    echo "$lineas"
}

extraer_modelo() {
    local ventana="$1"
    local status=$(tmux display-message -t "$SESION:$ventana" -p '#{pane_title}' 2>/dev/null)
    # Intentar extraer de la barra de estado de pi
    local barra=$(tmux capture-pane -t "$SESION:$ventana" -p 2>/dev/null | grep -oP '↑[\d.]+k.*' | tail -1)
    echo "$barra"
}

extraer_contexto() {
    local ventana="$1"
    local barra=$(tmux capture-pane -t "$SESION:$ventana" -p 2>/dev/null | grep -oP '↑[\d.]+k.*R[\d.]+k.*\$[\d.]+.*\d+[%]/[\d.]+M' | tail -1)
    echo "$barra"
}

dashboard() {
    clear
    
    local fecha=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLANCO}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLANCO}║${NC}  🎬  DASHBOARD DE PRODUCCIÓN DE VIDEO  ${GRIS}${fecha}${NC}              ${BLANCO}║${NC}"
    echo -e "${BLANCO}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Ventanas de agentes (1-7)
    for i in 1 2 3 4 5 6 7; do
        local nombre=$(tmux display-message -t "$SESION:$i" -p '#W' 2>/dev/null)
        [ -z "$nombre" ] && continue
        
        # Detectar si pi está activo
        local barra=$(extraer_contexto "$i")
        local modelo=$(echo "$barra" | grep -oP 'deepseek-\S+' || echo "—")
        local tokens=$(echo "$barra" | grep -oP '↑[\d.]+k' || echo "—")
        local costo=$(echo "$barra" | grep -oP '\$[\d.]+' || echo "—")
        local contexto=$(echo "$barra" | grep -oP '\d+[%]/[\d.]+M' || echo "—")
        
        # Últimas líneas de acción (resumidas)
        local acciones=$(extraer_ultima_accion "$i" | head -6)
        local accion_resumida=$(echo "$acciones" | tr -s ' ' | sed 's/^ *//' | tail -3)
        
        # Buscar reporte JSON
        local reporte="$REPORTES_DIR/${nombre,,}.json"
        local reporte_existe=""
        local ultima_actualizacion=""
        if [ -f "$reporte" ]; then
            reporte_existe="${VERDE}📄${NC}"
            ultima_actualizacion=$(date -r "$reporte" '+%H:%M:%S' 2>/dev/null)
        else
            reporte_existe="${GRIS}⏳${NC}"
            ultima_actualizacion="—"
        fi
        
        # Icono según ventana
        case $i in
            1) icono="🎬";;
            2) icono="🎞️";;
            3) icono="🤖";;
            4) icono="🔊";;
            5) icono="⚡";;
            6) icono="✂️";;
            7) icono="✅";;
            *) icono=" ";;
        esac
        
        echo -e "${BLANCO}┌── ${icono} ${NEGRITA}${nombre}${NC} ${GRIS}(tokens:${tokens} costo:${costo} ctx:${contexto})${NC} ${reporte_existe} ${GRIS}reporte:${ultima_actualizacion}${NC}"
        echo -e "${BLANCO}│${NC}"
        
        if [ -z "$acciones" ]; then
            echo -e "${BLANCO}│${NC}  ${GRIS}⌛ Iniciando...${NC}"
        else
            echo "$accion_resumida" | while IFS= read -r linea; do
                [ -z "$linea" ] && continue
                # Truncar a ~80 chars
                linea="${linea:0:80}"
                # Detectar si es input del usuario o respuesta del agente
                if echo "$linea" | grep -qiE '(leyendo|ejecutando|buscando|generando|creando|escribiendo|renderizando|procesando|analizando|revisando|aplicando|editando|instalando|descargando)'; then
                    echo -e "${BLANCO}│${NC}  ${CYAN}⚡${NC} $linea"
                elif echo "$linea" | grep -qiE '(error|fallo|fracasó|no encontrado)'; then
                    echo -e "${BLANCO}│${NC}  ${ROJO}✗${NC} $linea"
                elif echo "$linea" | grep -qiE '(completado|listo|terminado|hecho|✅|éxito)'; then
                    echo -e "${BLANCO}│${NC}  ${VERDE}✓${NC} $linea"
                elif echo "$linea" | grep -qiE '(herramienta|tool|bash|read|write|edit)'; then
                    echo -e "${BLANCO}│${NC}  ${GRIS}🔧${NC} $linea"
                else
                    echo -e "${BLANCO}│${NC}  ${GRIS}  ${NC} $linea"
                fi
            done
        fi
        
        echo -e "${BLANCO}│${NC}"
        
        # Si hay reporte, mostrar resumen
        if [ -f "$reporte" ]; then
            local resumen=$(jq -r '.resumen // empty' "$reporte" 2>/dev/null)
            local variaciones=$(jq -r '.variaciones | length // 0' "$reporte" 2>/dev/null)
            local errores=$(jq -r '.errores | length // 0' "$reporte" 2>/dev/null)
            if [ -n "$resumen" ]; then
                echo -e "${BLANCO}│${NC}  ${GRIS}📋 Reporte:${NC} $resumen"
                [ "$variaciones" -gt 0 ] && echo -e "${BLANCO}│${NC}  ${GRIS}   Variaciones:${NC} $variaciones"
                [ "$errores" -gt 0 ] && echo -e "${BLANCO}│${NC}  ${ROJO}   Errores:${NC} $errores"
            fi
        fi
        
        echo -e "${BLANCO}└${NC}${GRIS}────────────────────────────────────────────────────────────────${NC}"
        echo ""
    done
    
    # Verificar archivos clave
    local escenas_yaml="$SCRIPT_DIR/templates/escenas.yaml"
    local final_mp4="$SCRIPT_DIR/output/final.mp4"
    local renders=$(find "$SCRIPT_DIR/output/renders" -name "*.mp4" -o -name "*.wav" 2>/dev/null | wc -l)
    local reportes_count=$(find "$REPORTES_DIR" -name "*.json" 2>/dev/null | wc -l)
    
    echo -e "${GRIS}═══════════════════════ ARCHIVOS ═══════════════════════${NC}"
    [ -f "$escenas_yaml" ] && echo -e "  ${VERDE}📄 escenas.yaml${NC} $(wc -l < "$escenas_yaml") líneas" || echo -e "  ${GRIS}⏳ escenas.yaml${NC} — pendiente"
    echo -e "  ${AZUL}📁 renders:${NC} $renders archivos"
    echo -e "  ${AZUL}📁 reportes JSON:${NC} $reportes_count archivos"
    [ -f "$final_mp4" ] && echo -e "  ${VERDE}🎬 final.mp4${NC} listo" || echo -e "  ${GRIS}⏳ final.mp4${NC} — pendiente"
    echo ""
    
    # Pipeline status
    echo -e "${GRIS}═══════════════════════ PIPELINE ═══════════════════════${NC}"
    local status_director="⏳"
    local status_grupos="⏳"
    local status_quality="⏳"
    [ -f "$escenas_yaml" ] && status_director="${VERDE}✅${NC}"
    [ "$renders" -gt 0 ] && status_grupos="${VERDE}✅${NC} ($renders renders)"
    [ -f "$final_mp4" ] && status_quality="${VERDE}✅${NC}"
    
    echo -e "  ${status_director} Director  →  ${status_grupos} Grupos  →  ${status_quality} Quality"
    echo ""
    echo -e "${GRIS}═══ Ctrl+C para salir ═══ (refresca cada 3s) ═══${NC}"
}

while true; do
    dashboard
    sleep 3
done
