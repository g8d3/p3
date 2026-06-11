#!/usr/bin/env bash
# autoheal.sh — System watchdog. Runs at OS level (tmux window or nohup).
# Every 30s checks that all components are alive, restarts dead ones.
# This ensures the system survives terminal closes, crashes, etc.

S82="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$S82/data/autoheal.log"
PIDFILE="$S82/data/autoheal.pid"

log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

# ── Components to watch ──
declare -A COMPONENTS
COMPONENTS["proxy_watchdog"]="python3 $(cd $S82/../s84/proxy && pwd)/proxy_watchdog.py"
COMPONENTS["helperd"]="python3 $S82/core/helperd.py foreground"
COMPONENTS["dashboard"]="python3 $S82/web/server.py"
COMPONENTS["supervisor"]="python3 $S82/core/supervisor.py foreground"
COMPONENTS["sequencer"]="python3 $S82/core/sequencer.py"
COMPONENTS["runner"]="python3 $S82/artifacts/trading/runner.py"

# Map component name to PID file
pidfile() { echo "$S82/data/$1.pid"; }

is_alive() {
  local pf=$(pidfile "$1")
  [ -f "$pf" ] || return 1
  local pid=$(cat "$pf" 2>/dev/null)
  [ -n "$pid" ] && [ -d "/proc/$pid" ] 2>/dev/null
}

start_comp() {
  local name="$1"
  local cmd="${COMPONENTS[$name]}"
  local pf=$(pidfile "$name")
  local lf="$S82/data/${name}-out.log"

  log "Starting $name: $cmd"
  nohup $cmd > "$lf" 2>&1 &
  echo $! > "$pf"
  log "$name started (PID=$!)"
}

stop_comp() {
  local name="$1"
  local pf=$(pidfile "$name")
  [ -f "$pf" ] || return
  local pid=$(cat "$pf" 2>/dev/null)
  kill "$pid" 2>/dev/null
  rm -f "$pf"
  log "$name stopped"
}

# ── Handle signals ──
# NOTE: SIGTERM only stops autoheal itself, NOT components.
# Components are independent and continue running.
# Use stop.sh for full shutdown.
cleanup() {
  log "Autoheal stopping (components continue running)"
  rm -f "$PIDFILE"
  exit 0
}
trap cleanup TERM INT

echo $$ > "$PIDFILE"
log "Autoheal started (PID=$$)"

# Startup: launch everything
for comp in "${!COMPONENTS[@]}"; do
  if ! is_alive "$comp"; then
    start_comp "$comp"
  else
    log "$comp already running"
  fi
done

# Monitor loop
while true; do
  for comp in "${!COMPONENTS[@]}"; do
    if ! is_alive "$comp"; then
      log "$comp DEAD, restarting"
      start_comp "$comp"
    fi
  done

  # Supervisor runs as background process (managed above by COMPONENTS)
  # No tmux window needed — autoheal handles lifecycle

  sleep 15
done
