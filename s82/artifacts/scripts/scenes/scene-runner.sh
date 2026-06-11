#!/usr/bin/env bash
# scene-runner.sh — Graba una escena individual con su narración específica
# Uso: ./scene-runner.sh <scene_name> <duration> <setup_cmd> <narration_text> <output_dir>
set -e
export DISPLAY="${DISPLAY:-:0}"
SCENE="$1"
DURATION="$2"
SETUP_CMD="$3"
NARRATION="$4"
OUTDIR="${5:-/home/vuos/code/p3/s82/artifacts/videos/scenes}"

mkdir -p "$OUTDIR" "$(dirname "$0")/logs"

RAW="$OUTDIR/${SCENE}-raw.mp4"
NARR="$OUTDIR/${SCENE}-narration.mp3"
FINAL="$OUTDIR/${SCENE}.mp4"

echo "=== Escena: $SCENE (${DURATION}s) ==="
echo "Setup: $SETUP_CMD"

# Clean previous xterms
pkill -f "xterm.*scene-" 2>/dev/null || true
sleep 1

# Run setup
if [ -n "$SETUP_CMD" ]; then
  echo "[setup] $SETUP_CMD"
  eval "$SETUP_CMD"
  sleep 2
fi

# Record
echo "[record] ${DURATION}s → $RAW"
xdg-screensaver suspend "$DISPLAY" 2>/dev/null || true
ffmpeg -video_size 1280x720 -framerate 15 -f x11grab -i "${DISPLAY}+0,0" \
  -f alsa -i default -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 96k \
  -t "$DURATION" -y "$RAW" 2>/dev/null
xdg-screensaver resume "$DISPLAY" 2>/dev/null || true

# Narrate
echo "[narrate] → $NARR"
edge-tts --voice es-MX-DaliaNeural --text "$NARRATION" --write-media "$NARR" 2>/dev/null

# Combine
echo "[combine] → $FINAL"
ffmpeg -i "$RAW" -i "$NARR" -c:v copy -c:a aac -map 0:v -map 1:a -shortest -y "$FINAL" 2>&1 | tail -1

# Verify
python3 -c "
from PIL import Image
im = Image.open('/dev/stdin' if False else '$(ffmpeg -y -i "$RAW" -vframes 1 -f image2pipe - 2>/dev/null)')
" 2>/dev/null || true
CENTER=$(ffmpeg -y -i "$RAW" -vframes 1 -f rawvideo -pix_fmt rgb24 - 2>/dev/null | python3 -c "
import sys; data=sys.stdin.buffer.read(1280*720*3); r,g,b=data[640*720*3+640*3:640*720*3+640*3+3]; print(f'center=({r},{g},{b})')
" 2>/dev/null || echo "check manually")
echo "Scene $SCENE: $(ls -lh "$FINAL" | awk '{print $5}') $CENTER"