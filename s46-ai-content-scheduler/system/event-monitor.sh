#!/bin/bash
# ============================================================
# event-monitor.sh — Event-based resource monitor
#
# NOT a polling script. This checks thresholds and ONLY
# produces output (logs, alerts) when something is WRONG.
# When all is well, it stays silent — reducing noise.
#
# Usage:
#   ./event-monitor.sh              # Check + alert if thresholds exceeded
#   ./event-monitor.sh --watch      # Watch mode (5s interval, loops)
#   ./event-monitor.sh --daemon     # Daemon mode (background, logs events)
#   ./event-monitor.sh --status     # Print current status once
#
# Thresholds:
#   CPU_LOAD_WARN  = 80% of cores
#   MEM_WARN       = 90%
#   DISK_WARN      = 85%
#   TEMP_WARN      = 80°C
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EVENT_LOG="$PROJECT_DIR/scheduler/logs/events.log"
DASHBOARD_DATA="$PROJECT_DIR/system/dashboard/current-state.json"

mkdir -p "$(dirname "$EVENT_LOG")" "$(dirname "$DASHBOARD_DATA")"

# ─── Thresholds ───
CPU_CORES=$(nproc)
CPU_LOAD_WARN=$(echo "$CPU_CORES * 0.8" | bc | cut -d. -f1)
[[ -z "$CPU_LOAD_WARN" || "$CPU_LOAD_WARN" -lt 1 ]] && CPU_LOAD_WARN=1
MEM_WARN=90
DISK_WARN=85
TEMP_WARN=80

# ─── Colors ───
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# ─── Event logging ───
log_event() {
  local severity="$1"  # INFO, WARN, CRITICAL
  local message="$2"
  local timestamp=$(date +%Y-%m-%dT%H:%M:%S%z)
  echo "{\"timestamp\":\"$timestamp\",\"severity\":\"$severity\",\"message\":\"$message\"}" >> "$EVENT_LOG"
  echo -e "[${severity}] ${message}"
}

# ─── Single check ───
do_check() {
  local alerts=0
  local state_json="{}"

  # CPU load
  local load
  load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
  local is_high=0
  if [ "$(echo "$load > $CPU_LOAD_WARN" | bc 2>/dev/null || echo 0)" = "1" ]; then
    log_event "WARN" "High CPU load: ${load} (threshold: ${CPU_LOAD_WARN})"
    alerts=$((alerts + 1))
    is_high=1
  fi

  # Memory
  local mem_pct
  mem_pct=$(free -m | awk '/^Mem:/ {printf "%.0f", $3/$2 * 100}')
  local is_mem_high=0
  if [ "$mem_pct" -gt "$MEM_WARN" ]; then
    log_event "WARN" "High memory: ${mem_pct}% (threshold: ${MEM_WARN}%)"
    alerts=$((alerts + 1))
    is_mem_high=1
  fi

  # Disk
  local disk_pct
  disk_pct=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
  local is_disk_high=0
  if [ "$disk_pct" -gt "$DISK_WARN" ]; then
    log_event "WARN" "Disk at ${disk_pct}% (threshold: ${DISK_WARN}%)"
    alerts=$((alerts + 1))
    is_disk_high=1
  fi

  # Temperature
  local temp=""
  local is_hot=0
  if command -v sensors &>/dev/null; then
    temp=$(sensors 2>/dev/null | grep -oP 'Package id 0:\s+\+\K[0-9.]+' | head -1)
    if [ -n "$temp" ] && [ "$(echo "$temp > $TEMP_WARN" | bc 2>/dev/null || echo 0)" = "1" ]; then
      log_event "WARN" "CPU temperature: ${temp}°C (threshold: ${TEMP_WARN}°C)"
      alerts=$((alerts + 1))
      is_hot=1
    fi
  fi

  # OpenCode processes
  local oc_count
  oc_count=$(pgrep -c opencode 2>/dev/null || echo 0)

  # Agent count
  local agent_count=0
  local pid_dir="$PROJECT_DIR/scheduler/.pids"
  if [ -d "$pid_dir" ]; then
    for pidfile in "$pid_dir"/*.pid; do
      [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null && agent_count=$((agent_count + 1))
    done
  fi

  # Save current state as JSON for dashboard
  local content_count
  content_count=$(find "$PROJECT_DIR/content/posts" -name '*.txt' 2>/dev/null | wc -l)
  local audio_count
  audio_count=$(find "$PROJECT_DIR/content/audio" -name '*.mp3' -o -name '*.wav' 2>/dev/null | wc -l)

  cat > "$DASHBOARD_DATA" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "cpu": { "load": $load, "cores": $CPU_CORES, "threshold": $CPU_LOAD_WARN, "alert": $is_high },
  "memory": { "percent": $mem_pct, "threshold": $MEM_WARN, "alert": $is_mem_high },
  "disk": { "percent": $disk_pct, "threshold": $DISK_WARN, "alert": $is_disk_high },
  "temperature": ${temp:-null},
  "thermal_alert": $is_hot,
  "opencode_processes": $oc_count,
  "active_agents": $agent_count,
  "content": { "posts": $content_count, "audio": $audio_count },
  "alerts": $alerts
}
EOF

  return $alerts
}

# ─── Modes ───
case "${1:-}" in
  --watch)
    echo "Event monitor — watching every 5s (Ctrl+C to stop)"
    echo "Only shows output when thresholds are exceeded."
    echo "CPU threshold: ${CPU_LOAD_WARN}, MEM: ${MEM_WARN}%, DISK: ${DISK_WARN}%"
    echo "---"
    while true; do
      do_check > /dev/null 2>&1  # Silent check
      local alerts=$?
      if [ "$alerts" -gt 0 ]; then
        echo "[$(date +%H:%M:%S)] ALERTS: ${alerts} — re-checking..."
        do_check  # Show the alerts
      fi
      sleep 5
    done
    ;;
  --daemon)
    echo "Event monitor starting in daemon mode (PID: $$)"
    echo "Log: $EVENT_LOG"
    while true; do
      do_check > /dev/null 2>&1
      local alerts=$?
      if [ "$alerts" -gt 0 ]; then
        do_check  # Log the alerts
      fi
      sleep 30
    done
    ;;
  --status)
    do_check
    alerts=$?
    echo ""
    echo "System health: $( [ "$alerts" -eq 0 ] 2>/dev/null && echo '✅ OK' || echo "⚠️  ${alerts} alert(s)")"
    echo "Active agents: $(cat "$DASHBOARD_DATA" 2>/dev/null | grep -o '"active_agents": [0-9]*' | cut -d' ' -f2 || echo 0)"
    exit $alerts
    ;;
  *)
    do_check
    alerts=$?
    exit $alerts
    ;;
esac
