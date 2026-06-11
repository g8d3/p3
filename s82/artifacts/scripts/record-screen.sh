#!/usr/bin/env bash
# record-screen.sh — Grabación de pantalla con ffmpeg
# Uso: ./record-screen.sh [duración_segundos] [output.mp4]
set -e

DURATION="${1:-30}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${2:-$SCRIPT_DIR/../videos/record-$(date +%s).mp4}"
SIZE="${3:-1280x720}"
FPS="${4:-15}"

echo "=== Screen Recording ==="
echo "Duration: ${DURATION}s"
echo "Output: $OUTPUT"
echo "Size: $SIZE @ ${FPS}fps"
echo ""
export DISPLAY="${DISPLAY:-:0}"
xdg-screensaver suspend "$DISPLAY" 2>/dev/null || true
echo "Recording in 3 seconds..."
sleep 3
echo "Recording... (Ctrl+C to stop early)"

ffmpeg -video_size "$SIZE" -framerate "$FPS" -f x11grab -i "${DISPLAY}+0,0" \
  -f pulse -i default \
  -c:v libx264 -preset ultrafast -crf 28 \
  -c:a aac -b:a 96k \
  -t "$DURATION" \
  -y "$OUTPUT" 2>/dev/null
xdg-screensaver resume "$DISPLAY" 2>/dev/null || true

echo "Done: $OUTPUT"
ls -lh "$OUTPUT"
