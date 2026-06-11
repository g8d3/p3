#!/usr/bin/env bash
set -e

# Launch test agents to verify the cooperative cycle
S82="$(cd "$(dirname "$0")" && pwd)"
NUM=${1:-2}
BASE_WIN=${2:-5}  # start from window 5 to avoid conflicts

echo "=== Launching $NUM test agents ==="

for i in $(seq 1 $NUM); do
  NAME="worker-$i"
  WIN=$((BASE_WIN + i - 1))
  echo "[$NAME] Window $WIN"

  tmux new-window -d -n "$NAME" "cd $S82 && exec zsh"
  sleep 1

  # Set env for X-Agent-ID and start opencode with proxy model
  tmux send-keys -t "$WIN" "export X_AID=$NAME && export OPENCODE_DEFAULT_PROVIDER=proxy && opencode" Enter
  sleep 8  # wait for opencode to initialize

  echo "[$NAME] Ready"
done

# Echo the watcher/helperd status
echo ""
echo "=== Agents launched ==="
echo "Windows: $(seq -s, $BASE_WIN $((BASE_WIN + NUM - 1)))"
echo ""
echo "Run this to verify proxy sees them:"
echo "  curl -s http://localhost:9098/health | python3 -m json.tool | grep -A5 'worker-'"
echo ""
echo "Dashboard: http://localhost:9093"
echo ""
echo "To stuck a worker (test helperd):"
echo "  tmux send-keys -t $BASE_WIN 'sleep 60' Enter"
echo ""
echo "To see helperd react:"
echo "  tail -f $S82/data/helperd.log"
echo "  tail -f $S82/data/helperd-out.log"
