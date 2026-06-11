#!/usr/bin/env bash
set -e
DURATION="${1:-30}"
OUTPUT="${2:-$PWD/artifacts/videos/recording-$(date +%s).mp4}"
SIZE="${3:-1280x720}"
FPS="${4:-15}"
NARRATION="${5:-}"  # texto opcional para narración TTS
mkdir -p "$(dirname "$OUTPUT")"
export DISPLAY="${DISPLAY:-:0}"

# Ensure visible content on :0 (session on tty2, no windows by default)
XTERM_PID=""
if ! xwininfo -root -tree 2>/dev/null | grep -qE 'xterm|XTerm'; then
  echo "[xterm] Opening xterm on $DISPLAY..."
  xterm -geometry 80x24 -e 'watch -n 1 date' &
  XTERM_PID=$!
  sleep 2
fi

xdg-screensaver suspend "$DISPLAY" 2>/dev/null || true
echo "=== Screen Recording ==="
echo "DISPLAY=$DISPLAY Duration=${DURATION}s Output=$OUTPUT"
sleep 1
echo "Recording..."
ffmpeg -video_size "$SIZE" -framerate "$FPS" -f x11grab -i "${DISPLAY}+0,0" \
  -f alsa -i default -c:v libx264 -preset ultrafast -crf 28 -c:a aac -b:a 96k \
  -t "$DURATION" -y "$OUTPUT" 2>&1 | tail -2
xdg-screensaver resume "$DISPLAY" 2>/dev/null || true

# Cleanup xterm
kill "$XTERM_PID" 2>/dev/null || true
echo "Done:"; ls -lh "$OUTPUT"
ffprobe "$OUTPUT" 2>&1 | grep -E "Duration|Stream"

# Optional: add narration
if [ -n "$NARRATION" ]; then
  NARRATED="${OUTPUT%.*}-narrated.mp4"
  echo "=== Adding Narration ==="
  bash "$(dirname "$0")/../artifacts/scripts/narrate.sh" "$OUTPUT" "$NARRATION" "$NARRATED"
fi
