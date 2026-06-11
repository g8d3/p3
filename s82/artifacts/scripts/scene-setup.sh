#!/usr/bin/env bash
# scene-setup.sh — Arrange xterm windows on :0 for recording
# Uso: ./scene-setup.sh [setup|cleanup]
set -e
export DISPLAY="${DISPLAY:-:0}"
ACTION="${1:-setup}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$ACTION" = "cleanup" ]; then
  echo "[scene] Cleaning up xterms..."
  pkill -f "xterm.*watch-\|xterm.*tmux\|xterm.*tail" 2>/dev/null || true
  exit 0
fi

echo "[scene] Setting up display layout on $DISPLAY..."
pkill -f "xterm.*watch-\|xterm.*tmux" 2>/dev/null || true
sleep 1

# Window 1: Top-left - system clock
xterm -geometry 50x8+0+0 -T "System" -e 'watch -n 2 "date +%H:%M:%S && uptime | cut -d, -f1"' &
sleep 1

# Window 2: Top-right - tmux layout
xterm -geometry 50x8+640+0 -T "Tmux" -e 'watch -n 2 "tmux list-windows -t main 2>/dev/null || echo waiting..."' &
sleep 1

# Window 3: Middle-left - proxy health
xterm -geometry 50x18+0+150 -T "Proxy Health" -e "$SCRIPT_DIR/watch-proxy.sh" &
sleep 1

# Window 4: Middle-right - supervisor log
xterm -geometry 50x10+640+150 -T "Supervisor" -e 'watch -n 3 "tail -5 /home/vuos/code/p3/s82/data/supervisor.log 2>/dev/null || echo no log"' &
sleep 1

# Window 5: Bottom-left - helperd log
xterm -geometry 50x10+0+450 -T "Helperd" -e 'watch -n 3 "tail -5 /home/vuos/code/p3/s82/data/helperd.log 2>/dev/null || echo no log"' &
sleep 1

# Window 6: Bottom-right - dashboard
xterm -geometry 50x10+640+450 -T "Dashboard" -e "$SCRIPT_DIR/watch-dashboard.sh" &
sleep 2

echo "[scene] Layout ready — 6 windows on $DISPLAY"
echo "Windows: System | Tmux | Proxy Health | Supervisor | Helperd | Dashboard"