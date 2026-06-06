#!/bin/bash
# Grabación REAL de pantalla con X11
set -e

cd /home/vuos/code/p3/s84/a2a_test

# 1. Launch A2A agents
for p in 9001 9002; do fuser -k ${p}/tcp 2>/dev/null; done
for w in a2a-alpha a2a-beta; do tmux kill-window -t "$w" 2>/dev/null; done

venv_py="$PWD/../.venv/bin/python3"
tmux new-window -d -n a2a-alpha "DISPLAY=:0 $venv_py agent_alpha.py 2>&1"
tmux new-window -d -n a2a-beta "DISPLAY=:0 $venv_py agent_beta.py 2>&1"

for port in 9001 9002; do
    for i in $(seq 1 30); do
        curl -s "http://localhost:$port/.well-known/agent.json" >/dev/null 2>&1 && break
        sleep 0.3
    done
done
echo "Agentes listos."

# 2. Get display info
echo "Display: $DISPLAY"
echo "Resolución real: $(xdpyinfo -display :0 2>/dev/null | grep dimensions | awk '{print $2}' || echo 'desconocida')"

# 3. Launch ffmpeg recording of :0
rm -f /tmp/real-demo.mp4
ffmpeg -y -video_size 1920x1080 -framerate 15 -f x11grab -i :0.0 \
  -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
  /tmp/real-demo.mp4 &
FFPID=$!
echo "ffmpeg PID: $FFPID"
sleep 2

# 4. Launch xterm running the test
export DISPLAY=:0
xterm -geometry 140x40 +sb -fg green -bg black -fa 'Monospace' -fs 14 \
  -title "A2A Demo - Grabacion Real" \
  -e "python3 monitor_test.py; echo ''; echo '--- FIN ---'; sleep 3" &
XTERM_PID=$!

# 5. Wait for test to finish
wait $XTERM_PID 2>/dev/null || true
sleep 2

# 6. Stop recording
kill $FFPID 2>/dev/null || true
sleep 1

# 7. Verify
ls -lh /tmp/real-demo.mp4 2>/dev/null
echo "Hecho."