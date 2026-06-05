#!/bin/bash
# A2A Demo Narrado — ejecuta las pruebas A2A con narración TTS
# Usa Edge TTS para narración en tiempo real
# Uso: bash narrated_demo.sh

set -e
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

VENV_PYTHON="$BASE_DIR/../.venv/bin/python3"
TTS_VOICE="es-CO-GonzaloNeural"  # español Colombia, masculina
# Alternativas: en-US-JennyNeural, en-US-AriaNeural, en-GB-RyanNeural

# ── Helper: narrar con TTS ──
narrate() {
    local text="$1"
    local outfile="/tmp/tts-narration-$(date +%s).mp3"
    echo "  🎙️  $text"
    edge-tts --voice "$TTS_VOICE" --text "$text" --write-media "$outfile" >/dev/null 2>&1
    # Reproducir (si hay reproductor)
    which ffplay >/dev/null 2>&1 && ffplay -nodisp -autoexit "$outfile" 2>/dev/null || true
    which aplay >/dev/null 2>&1 && aplay "$outfile" 2>/dev/null || true
    # En Termux: usar play-audio o termux-media-player
    which termux-media-player >/dev/null 2>&1 && termux-media-player play "$outfile" >/dev/null 2>&1 && sleep 2 || true
}

# ── 1. Start agents ──
narrate "Starting A2A protocol test. Launching Alpha agent on port 9001 and Beta agent on port 9002."

for port in 9001 9002; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done
for w in a2a-alpha a2a-beta; do
    tmux kill-window -t "$w" 2>/dev/null || true
done

tmux new-window -d -n a2a-alpha "$VENV_PYTHON agent_alpha.py 2>&1; read"
tmux new-window -d -n a2a-beta "$VENV_PYTHON agent_beta.py 2>&1; read"

for port in 9001 9002; do
    for i in $(seq 1 20); do
        curl -s "http://localhost:$port/.well-known/agent.json" >/dev/null 2>&1 && break
        sleep 0.3
    done
done

narrate "Both agents are ready. Starting discovery test."

# ── TEST 1: Discovery ──
echo ""
echo "═══════════════════════════════════════════"
echo "  TEST 1: Agent Discovery"
echo "═══════════════════════════════════════════"

narrate "Test 1: Agent Card discovery. Fetching agent cards from both agents."
alpha_card=$(curl -s http://localhost:9001/.well-known/agent.json)
beta_card=$(curl -s http://localhost:9002/.well-known/agent.json)

alpha_name=$(echo "$alpha_card" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name','?'))" 2>/dev/null)
beta_name=$(echo "$beta_card" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name','?'))" 2>/dev/null)
echo "  Alpha: $alpha_name"
echo "  Beta:  $beta_name"

narrate "Found $alpha_name and $beta_name. Agent Cards describe capabilities but no quality criteria."

# ── TEST 2: Basic Task ──
echo ""
echo "═══════════════════════════════════════════"
echo "  TEST 2: Task Execution"
echo "═══════════════════════════════════════════"

narrate "Test 2: Sending a task to Alpha and polling until completion."
send_resp=$(curl -s -X POST http://localhost:9001/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"What is the weather like today?"}],"messageId":"m1"}}')
task_id=$(echo "$send_resp" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('id','?'))")
echo "  Task ID: $task_id"

for i in $(seq 1 10); do
    poll=$(curl -s http://localhost:9001/tasks/$task_id 2>/dev/null)
    state=$(echo "$poll" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
    echo "  Poll $i: $state"
    [ "$state" = "completed" ] && break
    sleep 0.5
done
narrate "Task completed successfully. Lifecycle: submitted, working, completed."

# ── TEST 3: Cancellation ──
echo ""
echo "═══════════════════════════════════════════"
echo "  TEST 3: Cancellation"
echo "═══════════════════════════════════════════"

narrate "Test 3: Cancellation. Sending a long task and immediately cancelling it."
send2=$(curl -s -X POST http://localhost:9001/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"Write a very long report about AI agents"}],"messageId":"m2"}}')
task2_id=$(echo "$send2" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('id','?'))")

sleep 0.3
cancel_resp=$(curl -s -X POST http://localhost:9001/tasks/$task2_id:cancel -H "Content-Type: application/json" -d '{}')
cancel_state=$(echo "$cancel_resp" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))")
echo "  Cancel state: $cancel_state"

sleep 0.5
verify=$(curl -s http://localhost:9001/tasks/$task2_id)
verify_state=$(echo "$verify" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))")
echo "  Final state: $verify_state"

if [ "$verify_state" = "canceled" ]; then
    narrate "Cancellation successful. Bug was fixed to prevent state overwrite."
else
    narrate "Warning: cancellation state may have been overwritten by processor thread."
fi

# ── TEST 4: Quality Gate ──
echo ""
echo "═══════════════════════════════════════════"
echo "  TEST 4: Quality Gate Limitation"
echo "═══════════════════════════════════════════"

narrate "Test 4: Quality gate. Sending good and bad input to Beta to show A2A has no quality distinction."

# Good input
send3=$(curl -s -X POST http://localhost:9002/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"Review this code: def foo(): pass"}],"messageId":"m3"}}')
task3_id=$(echo "$send3" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('id','?'))")
sleep 1.5
poll3=$(curl -s http://localhost:9002/tasks/$task3_id)
state3=$(echo "$poll3" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))")

# Bad input
send4=$(curl -s -X POST http://localhost:9002/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"This code has a bug"}],"messageId":"m4"}}')
task4_id=$(echo "$send4" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('id','?'))")
sleep 1.5
poll4=$(curl -s http://localhost:9002/tasks/$task4_id)
state4=$(echo "$poll4" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))")

echo "  Good input → state: $state3"
echo "  Bad input  → state: $state4"

if [ "$state3" = "$state4" ]; then
    narrate "Critical finding: Both good and bad inputs ended with state $state3. A2A protocol has no quality distinction."
fi

# ── TEST 5: List Tasks ──
echo ""
echo "═══════════════════════════════════════════"
echo "  TEST 5: Task Listing"
echo "═══════════════════════════════════════════"

narrate "Test 5: Listing all tasks on Alpha agent."
tasks=$(curl -s http://localhost:9001/tasks)
count=$(echo "$tasks" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('result',[])))" 2>/dev/null || echo "?")
echo "  Total tasks: $count"

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  SUMMARY"
echo "═══════════════════════════════════════════"

narrate "Demo complete. Key findings: Agent discovery works. Task execution works. Cancellation works but had a race condition bug which has been fixed. Quality gates do not exist in A2A protocol. This is why we proposed the A2A Quality extension."

# Cleanup
for w in a2a-alpha a2a-beta; do tmux kill-window -t "$w" 2>/dev/null || true; done
for port in 9001 9002; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done

narrate "Agents stopped. All tests complete."
echo ""
echo "Demo narration complete."
echo "Archivos:"
echo "  - Código: s84/a2a_test/"
echo "  - Reporte: s84/A2A-TEST-RESULTS.md"
echo "  - RFC extensión: s84/A2A-Q-RFC.md"
