#!/usr/bin/env bash
# This script types out the demo with precise timing

WINDOW="demo"  # tmux window name

# Clean up function
cleanup() {
    tmux send-keys -t demo C-c
    tmux send-keys -t demo C-c
    tmux send-keys -t demo C-d
    tmux send-keys -t demo "exit" Enter
}
# trap cleanup EXIT

# Wait for window to be ready
sleep 1.5

# ===== SCENE 1: "Antes" =====
# Type the complex command character by character
COMMAND='find . -name "*.ts" -not -path "*/node_modules/*" | xargs wc -l 2>/dev/null'

# Type each character with delay and enter at end
for (( i=0; i<${#COMMAND}; i++ )); do
    char="${COMMAND:$i:1}"
    tmux send-keys -t demo -l "$char"
    sleep 0.08
done
# Wait a bit then press Enter
sleep 0.3
tmux send-keys -t demo Enter

# Wait for command to execute
sleep 3

# ===== SCENE 2: "Ahora" =====
# Clear screen
tmux send-keys -t demo C-c
sleep 0.5
tmux send-keys -t demo "clear" Enter
sleep 1

# Type the simple natural language prompt
NLPROMPT='cuántas líneas de TypeScript hay'
for (( i=0; i<${#NLPROMPT}; i++ )); do
    char="${NLPROMPT:$i:1}"
    tmux send-keys -t demo -l "$char"
    sleep 0.05
done
tmux send-keys -t demo Enter

# Wait for the demo to show result (mock - we just show a quick result)
sleep 4

# End
echo "DEMO FINISHED"
