#!/bin/bash
# ============================================================
# run-task.sh — Autonomous OpenCode Go Task Runner
#
# Picks a task from the queue, executes it via opencode run,
# logs the result. Designed for cron scheduling.
#
# Usage:
#   ./run-task.sh                    # Run next task from queue
#   ./run-task.sh --once <task.sh>   # Run specific task
#   ./run-task.sh --list             # List available tasks
#   ./run-task.sh --serve            # Start headless server + run loop
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TASKS_DIR="$SCRIPT_DIR/tasks"
LOG_DIR="$SCRIPT_DIR/logs"
COUNTER_FILE="$TASKS_DIR/.counter"
OPENCODE="/home/vuos/.opencode/bin/opencode"
DEFAULT_MODEL="opencode-go/deepseek-v4-flash"

# Redirect temp files to local tmp/ to avoid /tmp/ permission prompts
export TMPDIR="$PROJECT_DIR/tmp"

mkdir -p "$LOG_DIR" "$TMPDIR"
mkdir -p "$TASKS_DIR"

DATE_TAG=$(date +%Y-%m-%d-%H%M%S)

# --- Help ---
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: $0 [--once <task>] [--list] [--serve]"
  echo ""
  echo "  (no args)   Run next task from queue (round-robin)"
  echo "  --once t    Run a specific task script once"
  echo "  --list      List all available tasks"
  echo "  --serve     Start headless opencode server + run loop"
  exit 0
fi

# --- List tasks ---
if [ "${1:-}" = "--list" ]; then
  echo "Available tasks:"
  for t in "$TASKS_DIR"/*.sh; do
    name=$(basename "$t" .sh)
    desc=$(head -5 "$t" | grep '^#' | head -1 | sed 's/^# //')
    echo "  $name  — ${desc:-no description}"
  done
  exit 0
fi

# --- Run task function ---
run_task() {
  local task_script="$1"
  local task_name=$(basename "$task_script" .sh)
  local log_file="$LOG_DIR/${task_name}-${DATE_TAG}.log"

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting task: $task_name" | tee -a "$log_file"

  # Source the task to get the TASK_PROMPT variable
  TASK_PROMPT=""
  source "$task_script"

  if [ -z "$TASK_PROMPT" ]; then
    echo "[ERROR] Task $task_name did not set \$TASK_PROMPT" | tee -a "$log_file"
    return 1
  fi

  # Write prompt to temp file for reference
  echo "$TASK_PROMPT" > "$LOG_DIR/${task_name}-${DATE_TAG}.prompt.txt"

  # Execute via opencode run
  # Using --dangerously-skip-permissions for fully autonomous execution
  # This is safe because we control the prompts being sent
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running opencode..." | tee -a "$log_file"

  cd "$PROJECT_DIR"
  $OPENCODE run "$TASK_PROMPT" \
    --model "$DEFAULT_MODEL" \
    --dangerously-skip-permissions \
    --dir "$PROJECT_DIR" \
    2>&1 | tee -a "$log_file"

  local exit_code=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Task complete. Exit code: $exit_code" | tee -a "$log_file"
  return $exit_code
}

# --- Run specific task ---
if [ "${1:-}" = "--once" ] && [ -n "${2:-}" ]; then
  task_file="$TASKS_DIR/$2"
  if [ ! -f "$task_file" ]; then
    # Try as full path
    task_file="$2"
    if [ ! -f "$task_file" ]; then
      echo "Task not found: $2"
      echo "Available tasks:"
      ls "$TASKS_DIR"/*.sh 2>/dev/null | xargs -n1 basename
      exit 1
    fi
  fi
  run_task "$task_file"
  exit $?
fi

# --- Serve mode: start headless server + run loop ---
if [ "${1:-}" = "--serve" ]; then
  PORT="${2:-4096}"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting headless opencode server on port $PORT..." | tee -a "$LOG_DIR/server-${DATE_TAG}.log"

  # Start server in background
  $OPENCODE serve --port "$PORT" --hostname "127.0.0.1" \
    >> "$LOG_DIR/server-${DATE_TAG}.log" 2>&1 &
  SERVER_PID=$!
  echo "Server PID: $SERVER_PID" | tee -a "$LOG_DIR/server-${DATE_TAG}.log"

  # Wait for server to be ready
  for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
      echo "Server ready after ${i}s" | tee -a "$LOG_DIR/server-${DATE_TAG}.log"
      break
    fi
    sleep 1
  done

  # Trap to clean up
  trap "kill $SERVER_PID 2>/dev/null; echo 'Server stopped'" EXIT

  # Run loop
  while true; do
    echo "" | tee -a "$LOG_DIR/server-${DATE_TAG}.log"
    echo "=== Run at $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOG_DIR/server-${DATE_TAG}.log"

    # Pick next task
    if [ ! -f "$COUNTER_FILE" ]; then
      echo 0 > "$COUNTER_FILE"
    fi
    COUNTER=$(cat "$COUNTER_FILE")
    TASKS=($(ls "$TASKS_DIR"/*.sh 2>/dev/null | sort))
    TOTAL=${#TASKS[@]}

    if [ $TOTAL -eq 0 ]; then
      echo "No tasks. Sleeping 1 hour..." | tee -a "$LOG_DIR/server-${DATE_TAG}.log"
      sleep 3600
      continue
    fi

    NEXT=$((COUNTER % TOTAL))
    echo $((NEXT + 1)) > "$COUNTER_FILE"
    TASK="${TASKS[$NEXT]}"
    TASK_NAME=$(basename "$TASK" .sh)

    echo "Selected task: $TASK_NAME" | tee -a "$LOG_DIR/server-${DATE_TAG}.log"

    # Source task to get prompt
    TASK_PROMPT=""
    source "$TASK"

    if [ -n "$TASK_PROMPT" ]; then
      $OPENCODE run "$TASK_PROMPT" \
        --model "$DEFAULT_MODEL" \
        --dangerously-skip-permissions \
        --attach "http://127.0.0.1:$PORT" \
        --dir "$PROJECT_DIR" \
        2>&1 | tee -a "$LOG_DIR/server-${DATE_TAG}.log"
    fi

    # Sleep between tasks (configurable)
    SLEEP_HOURS="${OPENCODE_TASK_INTERVAL:-4}"
    echo "Sleeping ${SLEEP_HOURS}h until next task..." | tee -a "$LOG_DIR/server-${DATE_TAG}.log"
    sleep $((SLEEP_HOURS * 3600))
  done
fi

# --- Default: run next task from queue (round-robin) ---
if [ ! -f "$COUNTER_FILE" ]; then
  echo 0 > "$COUNTER_FILE"
fi
COUNTER=$(cat "$COUNTER_FILE")
TASKS=($(ls "$TASKS_DIR"/*.sh 2>/dev/null | sort))
TOTAL=${#TASKS[@]}

if [ $TOTAL -eq 0 ]; then
  echo "No task scripts found in $TASKS_DIR"
  echo "Create .sh files that set \$TASK_PROMPT"
  exit 0
fi

NEXT=$((COUNTER % TOTAL))
echo $((NEXT + 1)) > "$COUNTER_FILE"
TASK="${TASKS[$NEXT]}"

run_task "$TASK"
exit $?
