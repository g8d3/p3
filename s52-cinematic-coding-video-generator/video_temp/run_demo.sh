#!/usr/bin/env bash
set -e

cd /home/vuos/code/p3/s52
mkdir -p video_temp

WINDOW="demo"
OUTPUT_VIDEO="video_temp/demo_raw.mp4"
CAPTURE_REGION="640x480"
CAPTURE_OFFSET="+200,150"

# Disable tmux status bar during demo for smoother rendering
tmux set -g status off 2>/dev/null || true

# Reset the demo window
tmux send-keys -t $WINDOW C-c C-u 2>/dev/null
sleep 0.3
tmux send-keys -t $WINDOW "clear" Enter
sleep 0.5
tmux send-keys -t $WINDOW "export PS1='$ '" Enter
sleep 0.5
tmux send-keys -t $WINDOW "clear" Enter
sleep 0.5

# Start ffmpeg recording
ffmpeg -y -f x11grab -video_size "$CAPTURE_REGION" -i ":0.0$CAPTURE_OFFSET" \
    -t 20 -c:v libx264 -preset ultrafast -crf 28 \
    "$OUTPUT_VIDEO" 2>/dev/null &
FFMPEG_PID=$!
sleep 1

# ===== SCENE 1: "Antes" =====
sleep 1.5

# Send entire command at once — tmux renders it instantly, no flicker
COMMAND='find . -name "*.ts" -not -path "*/node_modules/*" | xargs wc -l 2>/dev/null'
tmux send-keys -t $WINDOW -l "$COMMAND"
sleep 0.3
tmux send-keys -t $WINDOW Enter
sleep 3

# ===== SCENE 2: "Ahora" =====
tmux send-keys -t $WINDOW C-c
sleep 0.3
tmux send-keys -t $WINDOW "clear" Enter
sleep 1

NLPROMPT='cuántas líneas de TypeScript hay'
tmux send-keys -t $WINDOW -l "$NLPROMPT"
sleep 0.2
tmux send-keys -t $WINDOW Enter
sleep 4

# Stop recording
sleep 1
kill "$FFMPEG_PID" 2>/dev/null || true
wait "$FFMPEG_PID" 2>/dev/null || true

# Restore tmux status bar
tmux set -g status on 2>/dev/null || true

echo "=== Done ==="
ls -lh "$OUTPUT_VIDEO"
