#!/usr/bin/env bash
# scene-record.sh — Graba una escena individual
# Uso: ./scene-record.sh <scene_name> <duration> [setup_cmds...]
set -e
export DISPLAY="${DISPLAY:-:0}"
SCENE="$1"
DURATION="$2"
shift 2
OUTDIR="/home/vuos/code/p3/s82/artifacts/videos/scenes"
mkdir -p "$OUTDIR"

echo "=== Escena: $SCENE (${DURATION}s) ==="

# Kill old xterms
pkill -f "xterm.*scene-" 2>/dev/null || true
sleep 1

# Setup
if [ $# -gt 0 ]; then
  echo "[setup] $@"
  eval "$@"
  sleep 2
fi

RAW="$OUTDIR/${SCENE}.mp4"
echo "[record] ${DURATION}s → $RAW"
xdg-screensaver suspend "$DISPLAY" 2>/dev/null || true
ffmpeg -video_size 1280x720 -framerate 15 -f x11grab -i "${DISPLAY}+0,0" \
  -f alsa -i default -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 96k \
  -t "$DURATION" -y "$RAW" 2>/dev/null
xdg-screensaver resume "$DISPLAY" 2>/dev/null || true

# Cleanup
pkill -f "xterm.*scene-" 2>/dev/null || true

# Verify
python3 -c "
from PIL import Image
import subprocess, sys
r = subprocess.run(['ffmpeg', '-y', '-i', '$RAW', '-vframes', '1', '-f', 'image2pipe', '-'], capture_output=True)
im = Image.open(sys.stdin.buffer if False else open('/dev/stdin','rb'))
" 2>/dev/null
ffprobe "$RAW" 2>&1 | grep -E 'Duration|Stream'
ls -lh "$RAW"