# Build Vibe Coding — from scratch, zero infra

## Goal
A multi-platform (phone + desktop) voice coding app: user speaks, AI builds code and reports back in audio + text. Works on spotty connections.

## Architecture (no LiveKit, no Docker, no WebRTC)

**Tap-to-talk**: User taps mic button → records audio → releases → sends via WebSocket → server processes (STT → LLM → TTS) → streams response back → browser plays audio + shows transcript + code.

**Single `python server.py`** — no Docker, no LiveKit, no ICE, no TURN. Just a WebSocket server.

**Single `index.html`** — no React build step. Just vanilla HTML/JS served by the Python server.

## What the server needs

### WebSocket server (Python, `asyncio` + `websockets`)

One file: `server.py` (~400 lines)
- Serves `index.html` on HTTP GET
- Accepts WebSocket connections
- Message protocol: JSON

### Messages

**Client → Server:**
```json
{"type": "audio", "data": "<base64 wav bytes>"}
```

**Server → Client:**
```json
{"type": "transcript", "text": "what the user said"}
{"type": "thinking", "text": "optional thinking message"}
{"type": "response_chunk", "text": "partial LLM response..."}
{"type": "audio_chunk", "data": "<base64 pcm/wav bytes>", "format": "wav"}
{"type": "audio_end"}
{"type": "code", "code": "...", "summary": "what it does"}
{"type": "error", "message": "..."}
```

### Processing pipeline (sequential, one user turn at a time)
1. Receive audio bytes (WebSocket binary or base64 JSON)
2. **STT**: Deepgram Nova-3 — POST `https://api.deepgram.com/v1/listen` with `Authorization: Token DEEPGRAM_API_KEY`
   - Returns JSON with `results.channels[0].alternatives[0].transcript`
3. **LLM**: z.ai coding plan — POST `https://api.z.ai/api/coding/paas/v4/chat/completions` with `Authorization: Bearer ZAI_API_KEY`
   - Model: `glm-4.5-air`
   - System prompt: "You are a vibe coding assistant..."
   - Stream response tokens as `response_chunk` messages
   - Detect when user asks for code → call OpenCode
4. **Code gen**: `opencode --no-tui --non-interactive --execute "<task>"` in `/tmp/opencode-workspace/`
   - Capture output, send as `code` message (truncate to 2000 chars)
5. **TTS**: Chutes Kokoro — POST `https://chutes-kokoro.chutes.ai/speak` with `Authorization: Bearer CHUTES_API_TOKEN`
   - Body: `{"text": "...", "speed": 1, "voice": "af_heart"}`
   - Response: WAV bytes -> send as `audio_chunk`
   - For long responses, split into sentences, TTS each, stream as separate `audio_chunk` messages

### LLM System Prompt
"You are a vibe coding assistant. Help users build software through conversation. When the user asks you to write or modify code, use the `opencode` tool. Keep responses conversational. After code generation, summarize the results."

### Streaming approach
- LLM response is streamed token-by-token from z.ai API
- Each token sent as `response_chunk` so UI shows typing effect
- When LLM finishes a sentence, that sentence is sent to TTS
- TTS audio sent as `audio_chunk` immediately playable in browser
- Code blocks extracted from LLM response sent as separate `code` message

## What the client needs

Single file: `index.html` (~400 lines, vanilla HTML/CSS/JS, no build step)

### UI
- **Login screen**: Room name input, Start Coding button, theme toggle (light/dark)
- **Main screen**: 
  - Mic button (big circle, tap to record, shows recording state)
  - Transcript display (chat-like bubbles, user + AI)
  - Code panel (shown when code is generated, hidden otherwise)
  - Status/connection indicator
  - Model label showing current LLM provider/model

### Mobile-first
- Full viewport height, no scroll unless needed
- Mic button at bottom center, easily tappable
- Tabs or swipeable panels for conversation vs code
- Dark/light theme via CSS variables on `<html>` attribute
- Touch-friendly tap targets (min 48px)

### Audio recording
- `MediaRecorder` with `audio/webm;codecs=opus` mime type
- On recording end: convert to WAV (or send raw webm)
- Send via WebSocket as binary message

### Audio playback
- Receive audio chunks, decode and play via `AudioContext` / `decodeAudioData`
- Queue chunks for sequential playback
- Auto-play (user must have tapped mic first = user gesture)

### WebSocket
- Connect to `ws://{host}:8765` (or same origin)
- Reconnect on disconnect with exponential backoff
- Handle all message types

## Environment variables (set in environment)
```
ZAI_API_KEY=          # set in environment
DEEPGRAM_API_KEY=     # set in environment
CHUTES_API_TOKEN=     # set in environment
OPENAI_API_KEY=       # set in environment
OPENROUTER_API_KEY=   # set in environment
CEREBRAS_API_KEY=     # set in environment
DEEPSEEK_API_KEY=     # set in environment
```

## Already tested and working
- **Chutes Kokoro TTS**: `curl -X POST https://chutes-kokoro.chutes.ai/speak -H "Authorization: Bearer $CHUTES_API_TOKEN" -H "Content-Type: application/json" -d '{"text":"hello","speed":1,"voice":"af_heart"}'` returns WAV audio (24kHz, mono, 16-bit PCM)
- **z.ai LLM**: `curl POST https://api.z.ai/api/coding/paas/v4/chat/completions` with Bearer token works
- **Deepgram STT**: `curl POST https://api.deepgram.com/v1/listen` with Token auth works
- **OpenCode CLI**: available at `opencode` in PATH

## Project location
`/home/vuos/code/p3/s47/`

Create:
- `server.py` — Python WebSocket server
- `simple/index.html` — client
- `start.sh` — starts server

The previous s47/ directory has LiveKit cruft (docker-compose.yml, agent/, client/) — ignore those, build clean in s47/ root or a s47/simple/ subdir.

## Run
```bash
cd /home/vuos/code/p3/s47
source ~/.zshrc
python server.py
```

Access from phone via Tailscale: `https://100.102.52.59:8765` (or whatever port)
Access from desktop: `http://localhost:8765`

## Tailscale access
- PC has Tailscale IP `100.102.52.59`
- Phone (`poco-x7-pro`) has direct Tailscale connection
- For HTTPS on phone: use a self-signed cert (like `/tmp/vibe-cert.pem`) or just serve HTTP (Tailscale tunnel is encrypted).
- **Note**: `getUserMedia` requires HTTPS on non-localhost origins. So serve HTTPS with self-signed cert, or use `https://100.102.52.59:8765` with cert bypass on phone.
- To generate a self-signed cert: `openssl req -x509 -newkey rsa:2048 -keyout /tmp/key.pem -out /tmp/cert.pem -days 30 -nodes -subj "/CN=100.102.52.59"`

## Key learnings from previous attempt (LiveKit)
- WebRTC + Docker = endless ICE candidate / networking nightmare
- Don't use LiveKit for a simple voice app — it's designed for multi-participant video conferencing with complex SFU clustering
- Simple WebSocket + HTTP API calls is more reliable for spotty connections
- Deepgram STT, z.ai GLM, and Chutes Kokoro TTS all work well with simple REST APIs
- Keep it simple: one file server, one file client, no build step
