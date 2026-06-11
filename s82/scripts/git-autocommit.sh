#!/usr/bin/env bash
# Auto-commit runtime data every 30 minutes
cd /home/vuos/code/p3
git add s82/data/trading_log.csv s82/data/live_signals.json s82/progress/ 2>/dev/null
git add s82/artifacts/ 2>/dev/null
# Only commit if there are changes
git diff --cached --quiet || git commit -m "s82: auto-update $(date +%H:%M)"

# Also touch coordinator heartbeat to show I'm alive
touch /home/vuos/code/p3/s82/data/coordinator.heartbeat
