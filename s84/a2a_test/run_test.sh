#!/bin/bash
# A2A Test: launches agents in tmux and runs the client
# Usage: ./run_test.sh

set -e
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

VENV_PYTHON="$BASE_DIR/../.venv/bin/python3"

echo "=== A2A Protocol Test ==="
echo ""

# 1. Kill any existing agents on these ports
for port in 9001 9002; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill $pid 2>/dev/null && echo "Killed old process on port $port (pid $pid)"
done

# 2. Close old tmux windows if they exist
for w in a2a-alpha a2a-beta a2a-client; do
    tmux kill-window -t "$w" 2>/dev/null || true
done

# 3. Launch Alpha agent (port 9001)
echo "Starting Alpha agent on port 9001..."
tmux new-window -d -n a2a-alpha \
    "$VENV_PYTHON agent_alpha.py 2>&1; echo 'Alpha exited'; read"

# 4. Launch Beta agent (port 9002)
echo "Starting Beta agent on port 9002..."
tmux new-window -d -n a2a-beta \
    "$VENV_PYTHON agent_beta.py 2>&1; echo 'Beta exited'; read"

# 5. Wait for both to be ready
echo "Waiting for agents to start..."
for port in 9001 9002; do
    for i in $(seq 1 20); do
        curl -s "http://localhost:$port/.well-known/agent.json" >/dev/null 2>&1 && break
        sleep 0.3
    done
    echo "  Port $port ready"
done

# 6. Show Agent Cards
echo ""
echo "=== Alpha Agent Card ==="
curl -s http://localhost:9001/.well-known/agent.json | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9001/.well-known/agent.json
echo ""
echo "=== Beta Agent Card ==="
curl -s http://localhost:9002/.well-known/agent.json | python3 -m json.tool 2>/dev/null || curl -s http://localhost:9002/.well-known/agent.json

# 7. Run the client (in foreground, visible)
echo ""
echo "=== Running Client Tests ==="
$VENV_PYTHON client.py http://localhost:9001 http://localhost:9002

echo ""
echo "=== Done ==="
echo "Agent windows: a2a-alpha (9001), a2a-beta (9002)"
echo "To view: tmux select-window -t a2a-alpha"
echo "To stop: tmux kill-window -t a2a-alpha; tmux kill-window -t a2a-beta"
