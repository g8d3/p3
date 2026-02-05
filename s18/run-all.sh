#!/bin/bash

# Start both bootstrap.py and tui.py together
# This script opens two terminals

if [ "$1" = "--help" ]; then
    echo "Usage: ./run-all.sh [command]"
    echo ""
    echo "Commands:"
    echo "  none (default) - Start bootstrap.py and tui.py in separate terminals"
    echo "  --help         - Show this help message"
    echo ""
    echo "Requires: tmux or screen for terminal multiplexing"
    exit 0
fi

# Check for terminal multiplexer
if command -v tmux &> /dev/null; then
    echo "Starting with tmux..."
    tmux new-session -d -s agent -n bootstrap './bootstrap.py'
    tmux new-window -t agent -n tui './tui.py'
    tmux attach-session -t agent
elif command -v screen &> /dev/null; then
    echo "Starting with screen..."
    screen -dmS agent ./bootstrap.py
    screen -S agent -X screen -t tui ./tui.py
    screen -r agent
else
    echo "Error: Neither tmux nor screen found."
    echo "Please install one of them:"
    echo "  sudo apt install tmux"
    echo "  sudo apt install screen"
    echo ""
    echo "Or run manually in separate terminals:"
    echo "  Terminal 1: ./bootstrap.py"
    echo "  Terminal 2: ./tui.py"
    exit 1
fi
