#!/bin/bash
# netmon.sh — Monitor de red para crush (ventana 1)
# Uso: ./netmon.sh
# Muestra conexiones en tiempo real.

WINDOW=1
SHELL_PID=$(tmux list-panes -t :${WINDOW} -F '#{pane_pid}')

# Buscar crush recursivamente en el árbol de procesos
find_pid() {
    local pid="$1"
    local comm
    comm=$(ps -p "$pid" -o comm= 2>/dev/null)
    case "$comm" in crush|node) echo "$pid"; return;; esac
    for child in $(pgrep -P "$pid" 2>/dev/null); do
        found=$(find_pid "$child")
        [ -n "$found" ] && echo "$found" && return
    done
}
TARGET_PID=$(find_pid "$SHELL_PID")
[ -z "$TARGET_PID" ] && TARGET_PID="$SHELL_PID"

TMPDIR=/tmp/netmon.$$
mkdir -p "$TMPDIR"
cleanup() { kill $(jobs -p) 2>/dev/null; rm -rf "$TMPDIR"; exit; }
trap cleanup INT TERM

echo "╔══════════════════════════════════════════════╗"
echo "║  netmon — crush PID $TARGET_PID  ║"
echo "║  Esperando actividad de red...               ║"
echo "║  (envía un mensaje en la ventana 1)          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Monitor de conexiones (ss) ───
watch_ss() {
    local prev=""
    while true; do
        curr=$(ss -tnp 2>/dev/null | grep "pid=$TARGET_PID")
        if [ -n "$curr" ] && [ "$curr" != "$prev" ]; then
            echo ""
            echo "✦ Conexión [$(date +%H:%M:%S)]"
            echo "$curr" | while IFS= read -r c; do
                state=$(echo "$c" | awk '{print $1}')
                src=$(echo "$c" | awk '{print $4}')
                dst=$(echo "$c" | awk '{print $5}')
                echo "  $src  →  $dst  ($state)"
            done
            prev="$curr"
        elif [ -z "$curr" ] && [ -n "$prev" ]; then
            echo ""
            echo "✧ Conexión cerrada [$(date +%H:%M:%S)]"
            prev=""
        fi
        sleep 1
    done
}

# ─── Captura de tráfico (tcpdump) ───
capture() {
    hosts=$(ss -tnp 2>/dev/null | grep "pid=$TARGET_PID" | awk '{print $5}' | cut -d: -f1 | sort -u)
    filter="tcp"
    for h in $hosts; do
        [ "$filter" != "tcp" ] && filter="$filter or "
        filter="${filter}host $h"
    done

    # Capturar en modo quiet, mostrar solo resumen de paquetes con datos
    sudo tcpdump -i any -nn -tttt -q "$filter" 2>/dev/null | grep --line-buffered -E '(In|Out)' | while IFS= read -r line; do
        case "$line" in
            *length\ [1-9][0-9]*)
                dir="⬇"
                echo "$line" | grep -q 'Out ' && dir="⬆"
                ts=$(echo "$line" | sed 's/^[0-9-]* //' | grep -oE '^[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+')
                info=$(echo "$line" | grep -oE 'IP[^,]+(length [0-9]+|\[[A-Z.]+\])')
                echo "  $dir $ts $info"
                ;;
        esac
    done
}

# ─── Iniciar ───
watch_ss &
sleep 2
capture
