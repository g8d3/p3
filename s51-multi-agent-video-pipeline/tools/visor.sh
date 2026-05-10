#!/bin/bash
# Visor de reportes JSON - Muestra tablas en la terminal
# Dependencias: jq, column (vienen en termux)
#
# Uso:
#   bash tools/visor.sh              - Ver todos los reportes
#   bash tools/visor.sh director     - Ver solo un agente
#   bash tools/visor.sh --variaciones - Solo variaciones de video
#   bash tools/visor.sh --follow     - Modo live (refresca cada 5s)

REPORTES_DIR="/home/vuos/code/p3/s51/reportes"
SCRIPT_DIR="/home/vuos/code/p3/s51"

# Colores
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
ROJO='\033[0;31m'
GRIS='\033[0;90m'
NEGRITA='\033[1m'
NC='\033[0m' # No Color

mostrar_ayuda() {
    echo -e "${NEGRITA}Uso:${NC} bash tools/visor.sh [opciones]"
    echo ""
    echo "  bash tools/visor.sh                  Ver todos los reportes"
    echo "  bash tools/visor.sh director         Ver solo un agente"
    echo "  bash tools/visor.sh --variaciones    Solo variaciones de video"
    echo "  bash tools/visor.sh --follow         Modo live (refresca cada 5s)"
    echo "  bash tools/visor.sh --ayuda          Esta ayuda"
}

mostrar_encabezado() {
    local texto="$1"
    local ancho=60
    local relleno=""
    for ((i=0; i<(ancho-${#texto}-2)/2; i++)); do relleno="$relleno─"; done
    echo ""
    echo -e "${NEGRITA}${CYAN}┌${relleno} ${texto} ${relleno}┐${NC}"
}

mostrar_resumen_agentes() {
    mostrar_encabezado " AGENTES - RESUMEN "
    printf "${NEGRITA}%-4s %-12s %-20s %-12s${NC}\n" "#" "Agente" "Sesión" "Estado"
    printf "${GRIS}%-4s %-12s %-20s %-12s${NC}\n" "---" "------------" "--------------------" "------------"
    
    local i=0
    for f in "$REPORTES_DIR"/*.json; do
        [ -f "$f" ] || continue
        i=$((i+1))
        local nombre=$(basename "$f" .json)
        local sesion=$(jq -r '.sesion // "—"' "$f")
        local estado=$(jq -r '.errores | if length > 0 then "❌ ERROR" else "✅ OK" end' "$f")
        printf "%-4s %-12s %-20s %-12s\n" "$i." "$nombre" "$sesion" "$estado"
    done
    
    if [ "$i" -eq 0 ]; then
        echo -e "${AMARILLO}  ⚠ No hay reportes aún. Esperando...${NC}"
    fi
    echo ""
}

mostrar_variaciones() {
    mostrar_encabezado " VARIACIONES DE VIDEO "
    
    printf "${NEGRITA}%-4s %-16s %-14s %-8s %-8s %-10s %-24s${NC}\n" "#" "Archivo" "Estilo" "Dur(s)" "FPS" "Calidad" "Cámara"
    printf "${GRIS}%-4s %-16s %-14s %-8s %-8s %-10s %-24s${NC}\n" "---" "----------------" "--------------" "--------" "--------" "----------" "------------------------"
    
    local i=0
    for f in "$REPORTES_DIR"/*.json; do
        [ -f "$f" ] || continue
        local grupo=$(jq -r '.grupo // "?"' "$f")
        local nombre=$(basename "$f" .json)
        
        # Intentar extraer variaciones
        jq -c '.variaciones[] // []' "$f" 2>/dev/null | while read -r var; do
            [ "$var" = "[]" ] || [ -z "$var" ] && continue
            i=$((i+1))
            local archivo=$(echo "$var" | jq -r '.id // "—"')
            local estilo=$(echo "$var" | jq -r '.estilo // "—"')
            local duracion=$(echo "$var" | jq -r '.duracion // "—"')
            local fps=$(echo "$var" | jq -r '.fps // "—"')
            local calidad=$(echo "$var" | jq -r '.puntuacion_calidad // "—"')
            local camaras=$(echo "$var" | jq -r '[.movimientos_camara[]] | join(", ") // "—"' | cut -c1-22)
            printf "%-4s %-16s %-14s %-8s %-8s %-10s %-24s\n" "$i." "$archivo" "$estilo" "$duracion" "$fps" "$calidad" "$camaras"
        done
    done
    
    # Si no hay variaciones estructuradas, mostrar métricas
    local tiene_variaciones=$(find "$REPORTES_DIR" -name "*.json" -exec jq '.variaciones | length' {} + 2>/dev/null | paste -sd+ | bc 2>/dev/null)
    if [ -z "$tiene_variaciones" ] || [ "$tiene_variaciones" -eq 0 ]; then
        echo -e "${AMARILLO}  ⚠ No hay variaciones estructuradas todavía.${NC}"
    fi
    echo ""
}

mostrar_agente() {
    local agente="$1"
    local f="$REPORTES_DIR/${agente}.json"
    
    if [ ! -f "$f" ]; then
        echo -e "${ROJO}✗ No se encontró reporte para '$agente'${NC}"
        echo "  Buscado: $f"
        echo "  Reportes disponibles:"
        ls -1 "$REPORTES_DIR"/*.json 2>/dev/null | sed 's/.*\///' | sed 's/\.json$//' | sed 's/^/  • /'
        return
    fi
    
    mostrar_encabezado " ${agente^^} - DETALLE "
    
    # Campos principales
    echo -e "${NEGRITA}Resumen:${NC}  $(jq -r '.resumen // "—"' "$f")"
    echo -e "${NEGRITA}Sesión:${NC}   $(jq -r '.sesion // "—"' "$f")"
    echo -e "${NEGRITA}Fecha:${NC}    $(jq -r '.fecha // "—"' "$f")"
    
    # Métricas
    echo ""
    echo -e "${NEGRITA}Métricas:${NC}"
    jq -r '.metricas | to_entries[] | "  • \(.key): \(.value)"' "$f" 2>/dev/null | head -10
    
    # Errores
    local errores=$(jq -r '.errores | if length > 0 then .[] else empty end' "$f" 2>/dev/null)
    if [ -n "$errores" ]; then
        echo ""
        echo -e "${ROJO}❌ Errores:${NC}"
        jq -r '.errores[] | "  • \(.)"' "$f" 2>/dev/null
    fi
    
    # Resultados / Escenas
    local escenas=$(jq -r '.resultados[] | select(.tipo == "escena") | "\(.id) | \(.descripcion) | \(.duracion_seg)s | \(.camara) | \(.iluminacion) | \(.transicion)"' "$f" 2>/dev/null)
    if [ -n "$escenas" ]; then
        echo ""
        echo -e "${NEGRITA}Escenas:${NC}"
        printf "  ${GRIS}%-3s %-30s %-6s %-20s %-16s %-18s${NC}\n" "ID" "Descripción" "Dur." "Cámara" "Iluminación" "Transición"
        printf "  ${GRIS}%-3s %-30s %-6s %-20s %-16s %-18s${NC}\n" "---" "------------------------------" "------" "--------------------" "----------------" "------------------"
        echo "$escenas" | while IFS="|" read -r id desc dur camara ilum trans; do
            printf "  %-3s %-30s %-6s %-20s %-16s %-18s\n" "$id" "$desc" "${dur}s" "$camara" "$ilum" "$trans"
        done
    fi
    
    # Variaciones (para grupos)
    local vars=$(jq -r '.variaciones[] | "\(.id) | \(.estilo) | \(.duracion)s | \(.fps)fps | \(.puntuacion_calidad)"' "$f" 2>/dev/null)
    if [ -n "$vars" ]; then
        echo ""
        echo -e "${NEGRITA}Variaciones producidas:${NC}"
        printf "  ${GRIS}%-20s %-18s %-8s %-6s %-6s${NC}\n" "Archivo" "Estilo" "Dur." "FPS" "Calif"
        printf "  ${GRIS}%-20s %-18s %-8s %-6s %-6s${NC}\n" "--------------------" "------------------" "--------" "------" "------"
        echo "$vars" | while IFS="|" read -r archivo estilo dur fps cal; do
            printf "  %-20s %-18s %-8s %-6s %-6s\n" "$archivo" "$estilo" "$dur" "$fps" "$cal"
        done
    fi
    
    echo ""
}

# --- MAIN ---

# Crear directorio si no existe
mkdir -p "$REPORTES_DIR"

# Sin argumentos → mostrar todo
if [ $# -eq 0 ]; then
    mostrar_resumen_agentes
    mostrar_variaciones
    exit 0
fi

case "$1" in
    --variaciones)
        mostrar_variaciones
        ;;
    --follow)
        echo -e "${VERDE}📡 Modo live — refresca cada 5s. Ctrl+C para salir.${NC}"
        while true; do
            clear
            mostrar_resumen_agentes
            mostrar_variaciones
            echo -e "${GRIS}Última actualización: $(date +%H:%M:%S) — esperando...${NC}"
            sleep 5
        done
        ;;
    --ayuda|-h|--help)
        mostrar_ayuda
        ;;
    *)
        # Asume que es un nombre de agente
        mostrar_agente "$1"
        ;;
esac
