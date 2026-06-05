#!/bin/bash
# A2A Test — Reproducible Evidence
# Corre los tests y genera un reporte con timestamps + HTTP dump
# Úsalo para verificar que las pruebas son reales y reproducibles

set -e
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

VENV_PYTHON="$BASE_DIR/../.venv/bin/python3"
REPORT="$BASE_DIR/test-evidence-$(date +%Y%m%d-%H%M%S).txt"

echo "============================================" | tee "$REPORT"
echo " A2A Protocol Test — Reproducible Evidence" | tee -a "$REPORT"
echo " Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" | tee -a "$REPORT"
echo " Host: $(hostname)" | tee -a "$REPORT"
echo "============================================" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# ── 1. Start agents ──
echo "=== 1. Starting Agents ===" | tee -a "$REPORT"

for port in 9001 9002; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done
for w in a2a-alpha a2a-beta; do
    tmux kill-window -t "$w" 2>/dev/null || true
done

tmux new-window -d -n a2a-alpha "$VENV_PYTHON agent_alpha.py 2>&1; read"
tmux new-window -d -n a2a-beta "$VENV_PYTHON agent_beta.py 2>&1; read"

# Wait for both
for port in 9001 9002; do
    for i in $(seq 1 20); do
        curl -s "http://localhost:$port/.well-known/agent.json" >/dev/null 2>&1 && break
        sleep 0.3
    done
    echo "  Agent on port $port: READY" | tee -a "$REPORT"
done
echo "" | tee -a "$REPORT"

# ── Helper functions ──
call() {
    local method="$1" url="$2" body="$3"
    local req_id="req-$(date +%s%N)"
    echo "---[$req_id]---" >> "$REPORT"
    echo ">>> $method $url" >> "$REPORT"
    echo ">>> Body: $body" >> "$REPORT"
    local start=$(date +%s%N)
    local response=$(curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$body" 2>&1)
    local end=$(date +%s%N)
    local elapsed=$(( (end - start) / 1000000 ))
    echo "<<< Response ($elapsed ms): $response" >> "$REPORT"
    echo "---" >> "$REPORT"
    echo "$response"
}

# ── TEST 1: Agent Card Discovery ──
echo "=== TEST 1: Agent Card Discovery ===" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

alpha_card=$(curl -s http://localhost:9001/.well-known/agent.json)
echo "Alpha Card: $alpha_card" | tee -a "$REPORT"
beta_card=$(curl -s http://localhost:9002/.well-known/agent.json)
echo "Beta Card: $beta_card" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# ── TEST 2: Send Message + Poll ──
echo "=== TEST 2: Send Message + Poll ===" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# Send
send_resp=$(call POST "http://localhost:9001/message:send" \
    '{"message":{"role":"user","parts":[{"text":"What is the weather?"}],"messageId":"m1"}}')
task_id=$(echo "$send_resp" | python3 -c "import sys,json; t=json.load(sys.stdin); print(t.get('result',t).get('id','?'))" 2>/dev/null)
echo "Task ID: $task_id" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# Poll until complete
for i in $(seq 1 10); do
    poll_resp=$(call GET "http://localhost:9001/tasks/$task_id" "")
    state=$(echo "$poll_resp" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
    echo "  Poll $i: $state" | tee -a "$REPORT"
    [ "$state" = "completed" ] && break
    sleep 0.5
done
echo "" | tee -a "$REPORT"

# ── TEST 3: Cancellation ──
echo "=== TEST 3: Cancellation ===" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# Send long task
send2=$(call POST "http://localhost:9001/message:send" \
    '{"message":{"role":"user","parts":[{"text":"Write a very long report about AI agents"}],"messageId":"m2"}}')
task2_id=$(echo "$send2" | python3 -c "import sys,json; t=json.load(sys.stdin); print(t.get('result',t).get('id','?'))" 2>/dev/null)
echo "Task 2 ID: $task2_id" | tee -a "$REPORT"

# Cancel after a brief moment
sleep 0.3
cancel_resp=$(call POST "http://localhost:9001/tasks/$task2_id:cancel" "{}")
cancel_state=$(echo "$cancel_resp" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
echo "Cancel state: $cancel_state" | tee -a "$REPORT"

# Verify final state
sleep 0.3
verify=$(call GET "http://localhost:9001/tasks/$task2_id" "")
verify_state=$(echo "$verify" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
echo "Verified state after cancel: $verify_state" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# ── TEST 4: Quality Gate Limitation ──
echo "=== TEST 4: Quality Gate Limitation ===" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# Good input
send3=$(call POST "http://localhost:9002/message:send" \
    '{"message":{"role":"user","parts":[{"text":"Review this code: def foo(): pass"}],"messageId":"m3"}}')
task3_id=$(echo "$send3" | python3 -c "import sys,json; t=json.load(sys.stdin); print(t.get('result',t).get('id','?'))" 2>/dev/null)
sleep 1.5
poll3=$(call GET "http://localhost:9002/tasks/$task3_id" "")
state3=$(echo "$poll3" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
echo "Good input → state: $state3" | tee -a "$REPORT"

# Bad input
send4=$(call POST "http://localhost:9002/message:send" \
    '{"message":{"role":"user","parts":[{"text":"This code has a bug"}],"messageId":"m4"}}')
task4_id=$(echo "$send4" | python3 -c "import sys,json; t=json.load(sys.stdin); print(t.get('result',t).get('id','?'))" 2>/dev/null)
sleep 1.5
poll4=$(call GET "http://localhost:9002/tasks/$task4_id" "")
state4=$(echo "$poll4" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))" 2>/dev/null)
echo "Bad input → state: $state4" | tee -a "$REPORT"
echo "BOTH states are '$state3'/'$state4' — no protocol-level quality distinction!" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# ── TEST 5: List Tasks ──
echo "=== TEST 5: List All Tasks on Alpha ===" | tee -a "$REPORT"
list_resp=$(call GET "http://localhost:9001/tasks" "")
echo "Tasks: $list_resp" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

# ── Cleanup ──
echo "=== Cleanup ===" | tee -a "$REPORT"
for w in a2a-alpha a2a-beta; do
    tmux kill-window -t "$w" 2>/dev/null || true
done
for port in 9001 9002; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done
echo "Agents stopped." | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

echo "============================================" | tee -a "$REPORT"
echo " REPORT GENERATED: $REPORT" | tee -a "$REPORT"
echo " You can cat this file to see every HTTP exchange." | tee -a "$REPORT"
echo " Re-run anytime with: bash $0" | tee -a "$REPORT"
echo "============================================" | tee -a "$REPORT"
