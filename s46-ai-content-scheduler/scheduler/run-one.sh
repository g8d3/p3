#!/bin/bash
# run-one.sh — Run a single content agent with full logging
# Launched via nohup so it persists beyond the parent session.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
TASKS_DIR="$SCRIPT_DIR/tasks"
OPENCODE="/home/vuos/.opencode/bin/opencode"
export TMPDIR="$PROJECT_DIR/tmp"

mkdir -p "$LOG_DIR" "$TMPDIR"

TASK_SCRIPT="${1:-$TASKS_DIR/01-project-spotlight.sh}"
DATE_TAG=$(date +%Y-%m-%d-%H%M%S)

# Source the prompt
TASK_PROMPT=""
source "$TASK_SCRIPT"

if [ -z "$TASK_PROMPT" ]; then
  echo "[$(date)] ERROR: No TASK_PROMPT in $TASK_SCRIPT"
  exit 1
fi

TASK_NAME=$(basename "$TASK_SCRIPT" .sh)
LOG_FILE="$LOG_DIR/solo-${TASK_NAME}-${DATE_TAG}.log"

echo "[$(date)] Starting: $TASK_NAME" | tee "$LOG_FILE"
echo "[$(date)] Model: opencode-go/deepseek-v4-flash" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

nice -n 19 \
  "$OPENCODE" run "$TASK_PROMPT" \
    --model "opencode-go/deepseek-v4-flash" \
    --dangerously-skip-permissions \
    --dir "$PROJECT_DIR" \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?
echo "" | tee -a "$LOG_FILE"
echo "[$(date)] Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "[$(date)] Done: $TASK_NAME" | tee -a "$LOG_FILE"
exit $EXIT_CODE
