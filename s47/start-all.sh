#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
source /home/vuos/.zshrc

TS_DOMAIN="vuos-hcar5000mi.tail6918b0.ts.net"
LIVEKIT_PORT=7880
CLIENT_PORT=5173

# ── Clean up any previous tailscale serve config ──────────────────────────
tailscale serve reset 2>/dev/null || true

# ── 1. Start LiveKit SFU + Redis ─────────────────────────────────────────
echo "=== Starting LiveKit SFU + Redis ==="
cd "$DIR"
docker compose up -d livekit-sfu redis 2>&1 || docker compose up -d redis livekit-sfu 2>&1
echo "Waiting for LiveKit SFU..."
sleep 3

# ── 2. Start Token Server ─────────────────────────────────────────────────
echo "=== Starting Token Server ==="
cd "$DIR/agent"
TOKEN_PORT=7882 uv run python token_server.py &
TOKEN_PID=$!
echo "Token server: PID $TOKEN_PID (port $TOKEN_PORT)"

# ── 3. Start Agent ────────────────────────────────────────────────────────
echo "=== Starting Voice Agent ==="
cd "$DIR/agent"
LIVEKIT_URL=ws://localhost:$LIVEKIT_PORT \
LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-}" \
LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET:-}" \
ZAI_API_KEY="$ZAI_API_KEY" \
DEEPGRAM_API_KEY="$DEEPGRAM_API_KEY" \
CHUTES_API_TOKEN="$CHUTES_API_TOKEN" \
OPENAI_API_KEY="$OPENAI_API_KEY" \
  uv run python main.py start &
AGENT_PID=$!
echo "Agent: PID $AGENT_PID"

# ── 4. Start Client Dev Server ───────────────────────────────────────────
echo "=== Starting Client Dev Server ==="
cd "$DIR/client"
npm install --silent 2>/dev/null
npx vite --host 0.0.0.0 --port $CLIENT_PORT &
CLIENT_PID=$!
echo "Client: PID $CLIENT_PID"

# ── 5. Tailscale Serve ────────────────────────────────────────────────────
echo "=== Configuring Tailscale Serve ==="
# Make Vite available at https://domain.ts.net/
tailscale serve --bg $CLIENT_PORT 2>/dev/null
# Make LiveKit WS available at https://domain.ts.net/livekit
tailscale serve --bg --set-path /livekit http://localhost:$LIVEKIT_PORT 2>/dev/null
# Make Token server available at https://domain.ts.net/token
tailscale serve --bg --set-path /token http://localhost:7882 2>/dev/null

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Vibe Coding — Running                      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ Client:  https://$TS_DOMAIN                              ║"
echo "║ LiveKit: wss://$TS_DOMAIN/livekit                          ║"
echo "║ Token:   https://$TS_DOMAIN/token?room=my-room              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop all"

trap "echo ''; echo 'Shutting down...'; kill $TOKEN_PID $AGENT_PID $CLIENT_PID 2>/dev/null; wait; tailscale serve reset 2>/dev/null; docker compose stop 2>/dev/null; echo 'Done.'" EXIT
wait
