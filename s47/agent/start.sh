#!/usr/bin/env bash
set -euo pipefail

# Source env vars from ~/.zshrc
source /home/vuos/.zshrc

export LIVEKIT_URL="${LIVEKIT_URL:-ws://localhost:7880}"
export LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-}"
export LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET:-}"
export DEEPGRAM_API_KEY="${DEEPGRAM_API_KEY:-}"
export ZAI_API_KEY="${ZAI_API_KEY:-}"
export CHUTES_API_TOKEN="${CHUTES_API_TOKEN:-}"

# Start the agent
uv run python main.py start
