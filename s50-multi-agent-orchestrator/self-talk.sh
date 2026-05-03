#!/usr/bin/env bash
set -euo pipefail

# self-talk.sh - Fork this session, send a prompt, capture output
# Usage: ./self-talk.sh "prompt message"
#
# The fork has full context of the parent session.

SESSION_DIR="$HOME/.pi/agent/sessions/--home-vuos-code-p3-s49-scratch--"
LATEST_SESSION=$(ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | head -1)

if [[ -z "$LATEST_SESSION" ]]; then
    echo "Error: No session found" >&2
    exit 1
fi

PROMPT="${1:-Hello from yourself. What are we working on?}"

pi --fork "$LATEST_SESSION" -p "$PROMPT" 2>/dev/null
