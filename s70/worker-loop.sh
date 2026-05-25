#!/usr/bin/env bash
# Worker agent — watches for tasks, executes with Crush, reports back
# Usage: ./worker-loop.sh
# Communication:
#   /home/vuos/code/p3/s70/bus/task.md   ← write task here
#   /home/vuos/code/p3/s70/bus/done.md   ← result appears here
#   /home/vuos/code/p3/s70/bus/status.md ← current status

set -e
BUS=/home/vuos/code/p3/s70/bus
mkdir -p "$BUS"

echo "idle" > "$BUS/status.md"
echo "ready" > "$BUS/done.md"

while true; do
  if [ -f "$BUS/task.md" ]; then
    TASK=$(cat "$BUS/task.md" 2>/dev/null || echo "")
    if [ -n "$TASK" ]; then
      echo "running" > "$BUS/status.md"
      echo "⏳ Running: $(echo "$TASK" | head -1)" > "$BUS/status.md"
      
      # Execute the task via Crush in single-prompt mode
      OPENAI_API_KEY="$OPENAI_API_KEY" \
      /home/vuos/.local/share/pi-node/current/bin/crush \
        -p "Eres un worker agent de implementación. Ejecuta EXACTAMENTE esta tarea y nada más. No te desvíes. Esta es la tarea: $TASK" \
        --yes 2>&1 | tee "$BUS/last_output.log"
      
      # Mark as done
      echo "✅ Done at $(date -Iseconds)" > "$BUS/done.md"
      echo "idle" > "$BUS/status.md"
      rm "$BUS/task.md"
    fi
  fi
  sleep 5
done
