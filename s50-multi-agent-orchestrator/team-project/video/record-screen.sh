#!/usr/bin/env bash
set -euo pipefail

# Graba la pantalla mientras los agentes trabajan
# Uso: ./record-screen.sh start|stop

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RECORDING_DIR="$PROJECT_DIR/recordings"
mkdir -p "$RECORDING_DIR"

PID_FILE="$PROJECT_DIR/.record.pid"
OUTPUT="$RECORDING_DIR/screen-$(date +%Y%m%d-%H%M%S).mp4"

start_recording() {
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Ya hay una grabación en curso"
        return
    fi
    
    echo "🔴 Iniciando grabación de pantalla..."
    
    # Obtener resolución de pantalla
    RES=$(xdpyinfo | grep dimensions | awk '{print $2}')
    WIDTH=$(echo "$RES" | cut -dx -f1)
    HEIGHT=$(echo "$RES" | cut -dx -f2)
    
    # Grabar con ffmpeg (x11grab)
    ffmpeg -y \
        -f x11grab \
        -video_size "${WIDTH}x${HEIGHT}" \
        -framerate 15 \
        -i :0.0 \
        -c:v libx264 \
        -preset ultrafast \
        -crf 28 \
        -pix_fmt yuv420p \
        "$OUTPUT" &
    
    echo $! > "$PID_FILE"
    echo "📹 Grabando → $OUTPUT"
    echo "   PID: $(cat "$PID_FILE")"
}

stop_recording() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo "No hay grabación activa"
        return
    fi
    
    local pid
    pid=$(cat "$PID_FILE")
    
    if kill -0 "$pid" 2>/dev/null; then
        echo "⏹️ Deteniendo grabación (PID $pid)..."
        kill -INT "$pid" 2>/dev/null || true
        sleep 2
        kill "$pid" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    echo "✅ Grabación guardada"
}

case "${1:-}" in
    start) start_recording ;;
    stop)  stop_recording ;;
    *)     echo "Uso: $0 {start|stop}" ;;
esac
