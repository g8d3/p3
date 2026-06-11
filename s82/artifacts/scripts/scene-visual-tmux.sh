#!/usr/bin/env bash
# scene-visual-tmux.sh — Shows tmux windows on :0
export DISPLAY="${DISPLAY:-:0}"
while true; do
  clear
  echo "=== TMUX WINDOWS ==="
  echo ""
  tmux list-windows -t main 2>/dev/null || echo "(no tmux session 'main')"
  echo ""
  echo "=== WORKER STATUS ==="
  echo ""
  for w in supervisor worker-1 worker-2 watcher; do
    out=$(tmux capture-pane -t "$w" -p 2>/dev/null | tail -3 | tr -d '\n' | head -c 80)
    echo "  $w: ${out:- (no output)}"
  done
  echo ""
  echo "=== $(date +%H:%M:%S) ==="
  sleep 3
done