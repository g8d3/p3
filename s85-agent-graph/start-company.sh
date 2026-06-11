#!/usr/bin/env bash
set -e

# ── Config ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_SCRIPT="/home/vuos/code/p3/s84/proxy/proxy_watchdog.py"
PULSE_SCRIPT="$SCRIPT_DIR/pulse.py"
PROXY_PORT=9098
PULSE_INTERVAL=15
STUCK_AFTER=25

# Default: 3 agents (workers) + 1 watcher
NUM_WORKERS=${1:-3}
TOTAL=$((NUM_WORKERS + 1))

echo "=== 🏢 Company Startup ==="
echo "Workers: $NUM_WORKERS"
echo "Watcher: 1"
echo "Total windows: $TOTAL"

# ── 1. Proxy ──
if ! curl -sf http://localhost:$PROXY_PORT/health > /dev/null 2>&1; then
    echo "[proxy] Starting..."
    nohup python3 "$PROXY_SCRIPT" > /tmp/company-proxy.log 2>&1 &
    sleep 3
    if curl -sf http://localhost:$PROXY_PORT/health > /dev/null 2>&1; then
        echo "[proxy] OK (PID $(pgrep -f proxy_watchdog | head -1))"
    else
        echo "[proxy] FAILED to start"
        exit 1
    fi
else
    echo "[proxy] Already running"
fi

# ── 2. Worker windows ──
WORKER_NAMES=()
WATCHER_WIN=$TOTAL

for i in $(seq 1 $NUM_WORKERS); do
    WIN=$i
    NAME="worker-$i"
    WORKER_NAMES+=("$NAME")
    echo "[$NAME] Creating window $WIN..."

    tmux new-window -n "$NAME" -d "cd $SCRIPT_DIR && exec zsh"
    sleep 0.5

    # Start opencode
    tmux send-keys -t $WIN "opencode" Enter
    sleep 6

    # Switch to proxy model
    tmux send-keys -t $WIN C-p
    sleep 1.5
    tmux send-keys -t $WIN "switch model"
    sleep 1
    tmux send-keys -t $WIN Enter
    sleep 1
    tmux send-keys -t $WIN "proxy"
    sleep 1
    tmux send-keys -t $WIN Enter
    sleep 2

    echo "[$NAME] Ready (proxy model)"
done

# ── 3. Watcher window ──
echo "[watcher] Creating window $WATCHER_WIN..."
tmux new-window -n "watcher" -d "cd $SCRIPT_DIR && exec zsh"
sleep 0.5
tmux send-keys -t $WATCHER_WIN "opencode" Enter
sleep 6
tmux send-keys -t $WATCHER_WIN C-p
sleep 1.5
tmux send-keys -t $WATCHER_WIN "switch model"
sleep 1
tmux send-keys -t $WATCHER_WIN Enter
sleep 1
tmux send-keys -t $WATCHER_WIN "proxy"
sleep 1
tmux send-keys -t $WATCHER_WIN Enter
sleep 2

INSTRUCTIONS="Eres el watcher del equipo. Tus compañeros:"
SEPARATOR=""
for NAME in "${WORKER_NAMES[@]}"; do
    INSTRUCTIONS+="$SEPARATOR $NAME"
    SEPARATOR=", "
done
INSTRUCTIONS+=". Cuando recibas [PULSO], revisa el proxy (curl -s http://localhost:9098/health) y sus paneles con tmux capture-pane. Si alguien está trabado (sin actividad + pantalla congelada), ayúdalo con Escape o un mensaje. Si no, ignora."

tmux send-keys -t $WATCHER_WIN "$INSTRUCTIONS" Enter
sleep 3
echo "[watcher] Ready"

# ── 4. Pulse ──
NAMES_STR=""
for i in $(seq 1 $NUM_WORKERS); do
    NAMES_STR+="$i:worker-$i,"
done
NAMES_STR="${NAMES_STR%,}"

nohup python3 "$PULSE_SCRIPT" \
    --watch "$(seq -s, 1 $NUM_WORKERS)" \
    --watcher $WATCHER_WIN \
    --names "$NAMES_STR" \
    --interval $PULSE_INTERVAL \
    --stuck-after $STUCK_AFTER \
    > /tmp/company-pulse.log 2>&1 &
PULSE_PID=$!

echo "[pulse] Started (PID $PULSE_PID)"

# ── Summary ──
echo ""
echo "=== 🏢 Company Running ==="
echo "Workers:"
for i in $(seq 1 $NUM_WORKERS); do
    echo "  Window $i: worker-$i (opencode + proxy)"
done
echo "  Window $WATCHER_WIN: watcher (opencode + proxy)"
echo "Pulse: PID $PULSE_PID"
echo "Proxy: http://localhost:$PROXY_PORT"
echo ""
echo "tmux select-window -t 0  # back to main"
echo "========================="
