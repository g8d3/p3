#!/usr/bin/env bash
# ============================================================================
# obs-lab.sh — Laboratorio interactivo de OBS + Xvfb + WebSocket
# ============================================================================
# Uso:  source obs-lab.sh   (hace 'source' para exportar DISPLAY)
# O mejor: ejecutar comandos manualmente en la terminal
# ============================================================================
# NOTA: NO usar set -e para poder hacer source del script sin riesgos

OBS_WS_PORT=4455
OBS_WS_PASS="SFT16WlCaNoupRwt"
XVFB_DISPLAY=":99"
XVFB_RES="1920x1080x24"
SCREENSHOT_DIR="/tmp/obs-lab-screenshots"
PIDFILE_OBS="/tmp/obs-lab-obs.pid"
PIDFILE_XVFB="/tmp/obs-lab-xvfb.pid"
PIDFILE_WM="/tmp/obs-lab-wm.pid"

mkdir -p "$SCREENSHOT_DIR"

# ─── 0. Información del sistema ───────────────────────────────────────────
info() {
    echo "=== Herramientas disponibles ==="
    which Xvfb xvfb-run obs xdotool xterm import scrot ffmpeg xdpyinfo 2>/dev/null || echo "(algunas no instaladas)"
    echo "---"
    echo "Versión OBS: $(obs --version 2>/dev/null || echo 'N/A')"
    echo "WebSocket pass: $OBS_WS_PASS (puerto $OBS_WS_PORT)"
    echo "WebSocket config: ~/.config/obs-studio/plugin_config/obs-websocket/config.json"
}

# ─── 1. Iniciar Xvfb (display virtual) ────────────────────────────────────
xvfb-start() {
    if [ -f "$PIDFILE_XVFB" ] && kill -0 "$(cat "$PIDFILE_XVFB")" 2>/dev/null; then
        echo "Xvfb ya está corriendo en :99 (PID $(cat "$PIDFILE_XVFB"))"
        return
    fi
    echo "🧪 Iniciando Xvfb en $XVFB_DISPLAY (${XVFB_RES})..."
    Xvfb "$XVFB_DISPLAY" -screen 0 "$XVFB_RES" -ac &
    echo $! > "$PIDFILE_XVFB"
    sleep 1
    export DISPLAY="$XVFB_DISPLAY"
    echo "✓ DISPLAY=$DISPLAY"
    # Verificar
    xdpyinfo -display "$DISPLAY" 2>/dev/null | head -5 || echo "⚠️  xdpyinfo falló, pero puede funcionar igual"
}

xvfb-stop() {
    if [ -f "$PIDFILE_XVFB" ]; then
        echo "Deteniendo Xvfb..."
        kill "$(cat "$PIDFILE_XVFB")" 2>/dev/null || true
        rm -f "$PIDFILE_XVFB"
        echo "✓ Xvfb detenido"
    fi
}

# ─── 1b. Iniciar Window Manager (openbox) para XComposite capture ──────────
#     Sin un WM, OBS no puede capturar ventanas individuales (XComposite).
openbox-start() {
    if [ -f "$PIDFILE_WM" ] && kill -0 "$(cat "$PIDFILE_WM")" 2>/dev/null; then
        echo "openbox ya está corriendo (PID $(cat "$PIDFILE_WM"))"
        return
    fi
    if [ -z "${DISPLAY:-}" ]; then
        echo "⚠️  DISPLAY no configurado. Ejecuta primero: xvfb-start"
        return 1
    fi
    echo "🪟 Iniciando openbox (window manager) en $DISPLAY..."
    openbox &
    echo $! > "$PIDFILE_WM"
    sleep 2
    echo "✓ openbox iniciado (PID $(cat "$PIDFILE_WM"))"
    echo "  (XComposite window capture ahora disponible en OBS)"
}

openbox-stop() {
    if [ -f "$PIDFILE_WM" ]; then
        echo "Deteniendo window manager..."
        kill "$(cat "$PIDFILE_WM")" 2>/dev/null || true
        rm -f "$PIDFILE_WM"
        echo "✓ Window manager detenido"
    fi
}

# ─── 2. Iniciar OBS en el display virtual ─────────────────────────────────
obs-start() {
    if [ -f "$PIDFILE_OBS" ] && kill -0 "$(cat "$PIDFILE_OBS")" 2>/dev/null; then
        echo "OBS ya está corriendo (PID $(cat "$PIDFILE_OBS"))"
        return
    fi
    if [ -z "${DISPLAY:-}" ]; then
        echo "⚠️  DISPLAY no está configurado. Ejecuta primero: xvfb-start"
        return 1
    fi
    echo "🎬 Iniciando OBS Studio en $DISPLAY..."
    echo "   WebSocket: ws://localhost:$OBS_WS_PORT"
    obs &
    OBS_PID=$!
    echo $OBS_PID > "$PIDFILE_OBS"
    echo "✓ OBS iniciado (PID $OBS_PID)"

    # Auto-dismiss crash recovery dialog (aparece después de un crash previo)
    for i in $(seq 1 8); do
        CRASH=$(xdotool search --name "Crash" 2>/dev/null)
        if [ -n "$CRASH" ]; then
            sleep 1
            xdotool key --window "$CRASH" --clearmodifiers Return 2>/dev/null
            echo "   ✅ Crash recovery dialog dismissed"
            break
        fi
        sleep 1
    done

    echo "   Esperando a que WebSocket esté listo..."
    for i in $(seq 1 15); do
        if command -v ss &>/dev/null && ss -tlnp 2>/dev/null | grep -q ":$OBS_WS_PORT "; then
            echo "   ✅ WebSocket listo después de ${i}s"
            break
        elif command -v nc &>/dev/null && nc -z 127.0.0.1 $OBS_WS_PORT 2>/dev/null; then
            echo "   ✅ WebSocket listo después de ${i}s"
            break
        fi
        sleep 1
    done
}

obs-stop() {
    if [ -f "$PIDFILE_OBS" ]; then
        echo "Deteniendo OBS..."
        kill "$(cat "$PIDFILE_OBS")" 2>/dev/null || true
        rm -f "$PIDFILE_OBS"
        echo "✓ OBS detenido"
    fi
}

# ─── 3. Iniciar OBS con xvfb-run (todo-en-uno, efímero) ──────────────────
obs-xvfb() {
    echo "🎬 Iniciando OBS en Xvfb (sesión efímera)..."
    echo "   WebSocket: ws://localhost:$OBS_WS_PORT"
    echo "   Para interactuar: export DISPLAY=:99"
    echo ""
    xvfb-run --server-args="-screen 0 1920x1080x24" \
        obs --websocket "$OBS_WS_PORT" \
            --password "$OBS_WS_PASS" &
    # Nota: xvfb-run elige display automático, usualmente :99
    sleep 3
    # Intentar adivinar el display
    if command -v xdpyinfo &>/dev/null; then
        XVFB_DISP=$(xdpyinfo 2>/dev/null | grep -oP 'name of display:\s+\K:\d+') || \
        XVFB_DISP=$(ps aux | grep Xvfb | grep -oP ':\d+' | tail -1)
    else
        XVFB_DISP=$(ps aux | grep Xvfb | grep -oP ':\d+' | tail -1)
    fi
    echo "   ➡️  Xvfb corriendo en ${XVFB_DISP:-:99}"
    echo ""
    echo "   Comandos útiles:"
    echo "   export DISPLAY=${XVFB_DISP:-:99}"
    echo "   xterm &"
    echo "   xdotool search --name xterm windowmove 100 100 windowsize 800 600"
    echo "   openbox &    # para XComposite window capture"
}

# ─── 4. Crear ventanas de prueba en Xvfb ─────────────────────────────────
window-create() {
    if [ -z "${DISPLAY:-}" ]; then
        echo "⚠️  DISPLAY no configurado. Ejecuta: export DISPLAY=:99"
        return 1
    fi
    echo "🪟 Creando ventanas de prueba..."

    # Ventana 1 (xclock)
    xclock -geometry 400x400+50+50 &
    sleep 0.5

    # Ventana 2 (otro xclock)
    xclock -geometry 400x400+800+50 &
    sleep 0.5

    # Ventana 3 (xterm)
    xterm -geometry 100x30+200+500 -T "Terminal-1" -e "watch -n2 date" &
    sleep 0.5

    echo "✓ 3 ventanas creadas"
    echo ""
    echo "Para listar ventanas: xdotool search --name Terminal"
    echo "Para mover/redimensionar: xdotool ... windowmove ... windowsize ..."
}

# ─── 5. Comandos xdotool para ventanas ────────────────────────────────────
# Uso directo (sin función):
#   xdotool search --name "Termil-1" windowmove 100 100 windowsize 800 600
#   xdotool search --name "Terminal" windowactivate --sync type "ls -la"
#   xdotool click 1   # click izquierdo en posición actual del mouse
#   xdotool mousemove 500 500 click 1
#   xdotool key alt+F4  # cerrar ventana activa

window-list() {
    echo "=== Ventanas en $DISPLAY ==="
    xdotool search . 2>/dev/null | while read -r id; do
        name=$(xdotool getwindowname "$id" 2>/dev/null || echo "?")
        geo=$(xdotool getwindowgeometry "$id" 2>/dev/null | grep -E "Position|Geometry" | tr '\n' ' ')
        echo "  [$id] $name  $geo"
    done
}

window-arrange() {
    echo "🪟 Organizando ventanas en mosaico..."
    # Listar ventanas xclock y terminal
    local all_ids
    all_ids=$(xdotool search --name "xclock" 2>/dev/null; xdotool search --name "Terminal" 2>/dev/null)
    local i=0
    for id in $all_ids; do
        case $i in
            0) xdotool windowmove "$id" 50   50   windowsize "$id" 600 480 ;;
            1) xdotool windowmove "$id" 700  50   windowsize "$id" 600 480 ;;
            2) xdotool windowmove "$id" 50   560  windowsize "$id" 1250 460 ;;
        esac
        i=$((i+1))
    done
    if [ "$i" -eq 0 ]; then
        echo "⚠️  No se encontraron ventanas. Ejecuta primero: window-create"
        return 1
    fi
    echo "✓ $i ventanas organizadas"
}

# ─── 6. Capturar pantalla del display virtual ────────────────────────────
screenshot() {
    if [ -z "${DISPLAY:-}" ]; then
        echo "⚠️  DISPLAY no configurado"
        return 1
    fi
    local fname="$SCREENSHOT_DIR/xvfb-shot-$(date +%Y%m%d-%H%M%S).png"
    echo "📸 Capturando $DISPLAY → $fname"

    # Opción 1: ImageMagick (import)
    if which import &>/dev/null; then
        import -display "$DISPLAY" -window root "$fname"
        echo "✓ Capturado con import (ImageMagick)"
    # Opción 2: scrot
    elif which scrot &>/dev/null; then
        scrot "$fname"
        echo "✓ Capturado con scrot"
    # Opción 3: ffmpeg
    elif which ffmpeg &>/dev/null; then
        ffmpeg -y -f x11grab -video_size 1920x1080 -i "$DISPLAY" -vframes 1 "$fname" 2>/dev/null
        echo "✓ Capturado con ffmpeg"
    fi
    echo "   Archivo: $fname"
    echo "   Para ver: xdg-open $fname  (o ábrelo manualmente)"
}

# ─── 7. Grabar video del display virtual ─────────────────────────────────
record-start() {
    local outfile="${1:-$SCREENSHOT_DIR/xvfb-record-$(date +%Y%m%d-%H%M%S).mp4}"
    echo "🎥 Grabando $DISPLAY → $outfile"
    echo "   Presiona Ctrl+C para detener"
    ffmpeg -y -f x11grab -video_size 1920x1080 -framerate 30 \
        -i "$DISPLAY" -c:v libx264 -preset ultrafast -crf 28 "$outfile"
}

# ─── 8. Limpieza total ─────────────────────────────────────────────────────
cleanup() {
    echo "🧹 Limpiando..."
    obs-stop
    openbox-stop
    xvfb-stop
    # Matar x11vnc si está corriendo
    pkill -f "x11vnc.*$DISPLAY" 2>/dev/null || true
    echo "✓ Todo detenido"
}

# ─── 9. Demo completa ─────────────────────────────────────────────────────
demo() {
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🎬  DEMO COMPLETA: OBS + Xvfb + WebSocket + Ventanas"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    xvfb-start
    sleep 1
    openbox-start       # necesario para XComposite window capture
    obs-start
    window-create
    sleep 1
    window-arrange
    sleep 1
    screenshot

    echo ""
    echo "✅ Demo completada"
    echo "   Captura: $(ls -t "$SCREENSHOT_DIR" | head -1)"
    echo "   Ahora puedes usar Python: python3 obs-lab.py"
    echo ""
    echo "   Para ver la pantalla en vivo:"
    echo "   vnc-start"
    echo ""
    echo "   Para detener todo: cleanup"
    echo ""
    echo "   ⚠️  Para display real :0 (no Xvfb):"
    echo "      export DISPLAY=:0"
    echo "      obs-start"
    echo "      python3 obs-lab.py"
}

# ─── 10. Iniciar servidor VNC para ver el display ─────────────────────────
vnc-start() {
    if [ -z "${DISPLAY:-}" ]; then
        echo "⚠️  DISPLAY no configurado"
        return 1
    fi
    echo "🔌 Iniciando x11vnc para $DISPLAY en puerto 5900..."
    x11vnc -display "$DISPLAY" -forever -shared -nopw &
    echo "✓ VNC en localhost:5900 (sin contraseña)"
    echo "  Conectar con: vncviewer localhost:5900"
    echo "  O en navegador: https://novnc.com (conectar a localhost:5900)"
}

# ─── HELP ──────────────────────────────────────────────────────────────────
help() {
    echo "═══ obs-lab.sh — Laboratorio OBS + Xvfb ═══"
    echo ""
    echo "COMANDOS DISPONIBLES:"
    echo "  info            — mostrar info del sistema"
    echo "  xvfb-start      — iniciar display virtual Xvfb"
    echo "  xvfb-stop       — detener Xvfb"
    echo "  openbox-start   — iniciar WM (necesario para XComposite)"
    echo "  openbox-stop    — detener WM"
    echo "  obs-start       — iniciar OBS en el Xvfb"
    echo "  obs-stop        — detener OBS"
    echo "  obs-xvfb        — iniciar OBS + Xvfb (todo-en-uno)"
    echo "  window-create   — crear 3 ventanas xterm de prueba"
    echo "  window-list     — listar ventanas activas"
    echo "  window-arrange  — organizar ventanas en mosaico"
    echo "  screenshot      — capturar pantalla virtual como PNG"
    echo "  record-start    — grabar video del display virtual"
    echo "  vnc-start       — ver pantalla en vivo vía VNC"
    echo "  demo            — ejecutar demo completa"
    echo "  cleanup         — detener todo"
    echo ""
    echo "EJEMPLO RÁPIDO (display virtual :99):"
    echo "  source obs-lab.sh"
    echo "  demo"
    echo "  python3 obs-lab.py"
    echo "  screenshot"
    echo "  cleanup"
    echo ""
    echo "EJEMPLO RÁPIDO (display real :0):"
    echo "  export DISPLAY=:0"
    echo "  obs-start                # auto-dismissa crash dialog"
    echo "  python3 obs-lab.py"
    echo "  obs-stop"
    echo ""
    echo "COMANDOS xdotool ÚTILES:"
    echo "  xdotool search --name Terminal"
    echo "  xdotool getwindowgeometry <WINDOW_ID>"
    echo "  xdotool windowmove <WID> X Y"
    echo "  xdotool windowsize <WID> W H"
    echo "  xdotool windowactivate --sync <WID> type 'comando'"
    echo "  xdotool mousemove X Y click 1"
    echo "  xdotool key Super+Right  # maximizar a la derecha"
}

# ─── Entry point ──────────────────────────────────────────────────────────
${1:-help}
