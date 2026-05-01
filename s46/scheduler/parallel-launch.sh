#!/bin/bash
# ============================================================
# parallel-launch.sh — Burst-mode content generation
#
# Launches N content tasks in parallel with hardware-aware
# resource limits. Designed to consume OpenCode Go credits
# efficiently while keeping the PC usable.
#
# Usage:
#   ./parallel-launch.sh [count]    # Launch N parallel agents (default: 3)
#   ./parallel-launch.sh --max      # Launch as many as resources allow
#   ./parallel-launch.sh --status   # Check current agent status
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TASKS_DIR="$SCRIPT_DIR/tasks"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/.pids"
OPENCODE="/home/vuos/.opencode/bin/opencode"
DEFAULT_MODEL="opencode-go/deepseek-v4-flash"

# Redirect temp files to local tmp/ to avoid /tmp/ permission prompts
export TMPDIR="$PROJECT_DIR/tmp"

mkdir -p "$LOG_DIR" "$PID_DIR" "$TMPDIR"
DATE_TAG=$(date +%Y-%m-%d-%H%M%S)

# --- Resource Limits ---
# Max parallel agents (adjust based on your PC)
MAX_AGENTS=3
# Max memory per agent (MB)
MAX_MEM_PER_AGENT=1024
# CPU niceness (19 = lowest priority, won't starve other processes)
NICE_LEVEL=19

# --- Help ---
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0 [count|--max|--status]"
  echo ""
  echo "  [count]    Launch N agents in parallel (default: 3)"
  echo "  --max      Launch as many as available memory allows"
  echo "  --status   Show running agents and resource usage"
  exit 0
fi

# --- Status ---
if [ "${1:-}" = "--status" ]; then
  echo "=== Running Agents ==="
  if [ -d "$PID_DIR" ]; then
    for pidfile in "$PID_DIR"/*.pid; do
      [ -f "$pidfile" ] || continue
      pid=$(cat "$pidfile")
      name=$(basename "$pidfile" .pid)
      if kill -0 "$pid" 2>/dev/null; then
        echo "  ✅ $name (PID: $pid)"
      else
        echo "  ❌ $name (PID: $pid — DEAD)"
        rm -f "$pidfile"
      fi
    done
  fi
  echo ""
  echo "=== Resource Usage ==="
  echo "CPU load: $(uptime | awk -F'load average:' '{print $2}')"
  echo "Memory:"
  free -h | head -2
  echo "OpenCode processes:"
  pgrep -c opencode 2>/dev/null || echo "  0"
  exit 0
fi

# --- Resource check function ---
check_resources() {
  local needed_mem_mb=$1

  # Check available memory
  local avail_mem_mb
  avail_mem_mb=$(free -m | awk '/^Mem:/ {print $7}')

  if [ "$avail_mem_mb" -lt "$needed_mem_mb" ]; then
    echo "WARNING: Only ${avail_mem_mb}MB available, need ${needed_mem_mb}MB"
    return 1
  fi

  # Check max agents already running
  local running
  running=$(pgrep -c opencode 2>/dev/null || echo 0)
  if [ "$running" -ge "$MAX_AGENTS" ]; then
    echo "WARNING: Already $running agents running (max: $MAX_AGENTS)"
    return 1
  fi

  return 0
}

# --- Launch a single agent ---
launch_agent() {
  local task_script="$1"
  local task_name=$(basename "$task_script" .sh)
  local agent_id="${task_name}-${DATE_TAG}-$$"
  local log_file="$LOG_DIR/agent-${agent_id}.log"

  # Source the task to get TASK_PROMPT
  TASK_PROMPT=""
  source "$task_script"

  if [ -z "$TASK_PROMPT" ]; then
    echo "[$(date '+%H:%M:%S')] [FAIL] $task_name — no TASK_PROMPT" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
    return 1
  fi

  # Write prompt
  echo "$TASK_PROMPT" > "$LOG_DIR/prompt-${agent_id}.txt"

  # Launch opencode in background with resource limits
  # Note: ulimit -v is NOT set — Node.js needs large virtual address space
  # for V8/JIT. Instead we rely on nice + Node's own memory flag.
  local agent_log="$LOG_DIR/agent-${agent_id}.log"
  (
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent starting: $task_name" > "$agent_log"
    nice -n "$NICE_LEVEL" \
      "$OPENCODE" run "$TASK_PROMPT" \
        --model "$DEFAULT_MODEL" \
        --dangerously-skip-permissions \
        --dir "$PROJECT_DIR" \
        2>&1 | tee -a "$agent_log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent exit code: $?" >> "$agent_log"
  ) &

  local pid=$!
  echo "$pid" > "$PID_DIR/${agent_id}.pid"

  echo "[$(date '+%H:%M:%S')] [LAUNCH] $task_name (PID: $pid)" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
  return 0
}

# --- Set agent count ---
AGENT_COUNT=3
if [ "${1:-}" = "--max" ]; then
  # Calculate max agents based on available memory
  avail_mem=$(free -m | awk '/^Mem:/ {print $7}')
  AGENT_COUNT=$((avail_mem / (MAX_MEM_PER_AGENT + 256)))
  AGENT_COUNT=$((AGENT_COUNT > MAX_AGENTS ? MAX_AGENTS : AGENT_COUNT))
  AGENT_COUNT=$((AGENT_COUNT < 1 ? 1 : AGENT_COUNT))
  echo "Auto-scaling: ${avail_mem}MB available → ${AGENT_COUNT} agents"
elif [ -n "${1:-}" ] && [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  AGENT_COUNT=$1
fi

# Cap at MAX_AGENTS
if [ "$AGENT_COUNT" -gt "$MAX_AGENTS" ]; then
  echo "Capping at MAX_AGENTS=$MAX_AGENTS (requested: $AGENT_COUNT)"
  AGENT_COUNT=$MAX_AGENTS
fi

echo "=== Burst Mode: Launching ${AGENT_COUNT} agents ===" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "Date: $(date)" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "Model: $DEFAULT_MODEL" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "Nice level: $NICE_LEVEL" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"

# Collect available tasks (skip example-task.sh)
TASKS=($(ls "$TASKS_DIR"/*.sh 2>/dev/null | grep -v example-task | sort))
TOTAL_TASKS=${#TASKS[@]}

if [ $TOTAL_TASKS -eq 0 ]; then
  echo "ERROR: No task scripts found in $TASKS_DIR"
  exit 1
fi

# Launch agents
LAUNCHED=0
for i in $(seq 1 "$AGENT_COUNT"); do
  # Check resources before each launch
  if ! check_resources "$MAX_MEM_PER_AGENT"; then
    echo "Resource check failed, stopping launch at $LAUNCHED agents"
    break
  fi

  # Pick task round-robin
  task_idx=$(( (i - 1) % TOTAL_TASKS ))
  task="${TASKS[$task_idx]}"

  if launch_agent "$task"; then
    LAUNCHED=$((LAUNCHED + 1))
  fi

  # Small stagger between launches to avoid thundering herd
  sleep 2
done

echo "" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "=== Launched ${LAUNCHED} agents in parallel ===" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "Monitor with: $0 --status" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"
echo "View logs: ls $LOG_DIR/agent-*.log" | tee -a "$LOG_DIR/burst-${DATE_TAG}.log"

# Wait briefly and show status
sleep 3
echo ""
echo "=== Initial Status ==="
"$0" --status
