#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_SCRIPT="$SCRIPT_DIR/../s84/proxy/proxy_watchdog.py"
PROXY_PORT=9098
DASHBOARD_PORT=9093

echo "=== Multi-Agent System ==="
echo "Base: $SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/data" /tmp/agent-bus/{a1/in,a2/in,a3/in,history}

# ── 1. Proxy ──
if ! curl -sf http://localhost:$PROXY_PORT/health > /dev/null 2>&1; then
    echo "[proxy] Starting..."
    nohup python3 "$PROXY_SCRIPT" > "$SCRIPT_DIR/data/proxy-out.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/data/proxy.pid"
    sleep 3
    curl -sf http://localhost:$PROXY_PORT/health > /dev/null 2>&1 && echo "[proxy] OK" || echo "[proxy] FAILED"
else
    echo "[proxy] Already running"
fi

# ── 2. Helperd ──
kill $(cat "$SCRIPT_DIR/data/helperd.pid" 2>/dev/null) 2>/dev/null || true
nohup python3 "$SCRIPT_DIR/core/helperd.py" foreground > "$SCRIPT_DIR/data/helperd-out.log" 2>&1 &
echo $! > "$SCRIPT_DIR/data/helperd.pid"
echo "[helperd] PID $(cat $SCRIPT_DIR/data/helperd.pid)"

# ── 3. Dashboard ──
kill $(cat "$SCRIPT_DIR/data/dashboard.pid" 2>/dev/null) 2>/dev/null || true
nohup python3 "$SCRIPT_DIR/web/server.py" > "$SCRIPT_DIR/data/dashboard-out.log" 2>&1 &
echo $! > "$SCRIPT_DIR/data/dashboard.pid"
echo "[dashboard] http://localhost:$DASHBOARD_PORT"

# ── 4. Supervisor (autoheal manages it as background daemon) ──
# The autoheal script (step 5) will start and monitor the supervisor.
echo "[supervisor] Will be managed by autoheal"

# ── 5. Autoheal ──
kill $(cat "$SCRIPT_DIR/data/autoheal.pid" 2>/dev/null) 2>/dev/null || true
nohup bash "$SCRIPT_DIR/scripts/autoheal.sh" > "$SCRIPT_DIR/data/autoheal-out.log" 2>&1 &
echo $! > "$SCRIPT_DIR/data/autoheal.pid"
echo "[autoheal] PID $(cat $SCRIPT_DIR/data/autoheal.pid)"

# ── 6. Register agents in graph ──
python3 -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from core.graph import Graph
g = Graph()
for name in ['proxy','helperd','dashboard','supervisor','autoheal']:
    g.register_agent(name, {'type':'daemon','purpose':name})
g.register_agent('worker-1', {'type':'worker','purpose':'code'})
g.register_agent('worker-2', {'type':'worker','purpose':'code'})
print(f'Graph ready: {g.stats()}')
"

echo ""
echo "=== System Running ==="
echo "  Proxy:     :$PROXY_PORT"
echo "  Dashboard: :$DASHBOARD_PORT"
echo "  Helperd:   $(cat $SCRIPT_DIR/data/helperd.pid)"
echo "  Autoheal:  $(cat $SCRIPT_DIR/data/autoheal.pid)"
echo "  Supervisor: tmux window 'supervisor'"
echo "  Logs:      $SCRIPT_DIR/data/*.log"
echo ""
echo "Watch it: tail -f $SCRIPT_DIR/data/supervisor.log"
echo "Kill all: bash $SCRIPT_DIR/scripts/autoheal.sh (sends SIGTERM)"
