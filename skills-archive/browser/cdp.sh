#!/bin/bash
# Inicia Chrome con CDP — auto-contenido en el skill browser
# Uso: ./cdp.sh [puerto] [data_dir] [profile]

PORT="${1:-9222}"
DATA_DIR="${2:-$HOME/apps/test-dec-2025}"
PROFILE="${3:-Profile 1}"

# Detectar display real (nunca asumir que $DISPLAY es correcto)
DISPLAY=""
for sock in /tmp/.X11-unix/X*; do
    [ -e "$sock" ] && DISPLAY=":${sock##*X}" && break
done
[ -z "$DISPLAY" ] && DISPLAY=":0"

export DISPLAY="$DISPLAY"

# Matar Chrome previo
pkill chrome 2>/dev/null
sleep 1

# Iniciar Chrome con debugging
google-chrome \
    --user-data-dir="$DATA_DIR" \
    --profile-directory="$PROFILE" \
    --remote-debugging-port="$PORT" \
    --disable-features=DownloadRestrictions \
    --no-first-run \
    --no-sandbox \
    &>/tmp/chrome-cdp.log &

# Esperar a que responda
for i in $(seq 1 10); do
    if curl -s "http://localhost:$PORT/json/version" >/dev/null 2>&1; then
        echo "✅ Chrome CDP listo en puerto $PORT (display $DISPLAY, perfil $PROFILE)"
        exit 0
    fi
    sleep 1
done

echo "❌ ERROR: Chrome no respondió en puerto $PORT" >&2
exit 1
