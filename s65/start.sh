#!/usr/bin/env bash
# start-cubesandbox.sh
# Levanta todo el stack de CubeSandbox.
# Solo pide sudo para el network-agent (eBPF).
# Correr UNA VEZ. Si ya está corriendo, no pasa nada.

set -euo pipefail

BIN=$HOME/.local/bin
LOG=$HOME/.local/state/cube-sandbox/log
mkdir -p "$LOG" /tmp/cube /tmp/cube-network-state

echo "═══════════════════════════════════════════"
echo "  CubeSandbox - Inicio del stack"
echo "═══════════════════════════════════════════"

# 1. MySQL (si no está corriendo)
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q cube-mysql; then
  echo "➤ MySQL..."
  docker rm -f cube-mysql 2>/dev/null
  docker run -d --name cube-mysql \
    -e MYSQL_ROOT_PASSWORD=rootpass \
    -e MYSQL_USER=cube \
    -e MYSQL_PASSWORD=cube_pass \
    -e MYSQL_DATABASE=cube_mvp \
    -p 3307:3306 mysql:8.0 > /dev/null 2>&1
  echo "  esperando MySQL..."
  for i in $(seq 1 15); do
    mysql -h127.0.0.1 -P3307 -ucube -pcube_pass cube_mvp -e "SELECT 1" 2>/dev/null && break
    sleep 2
  done
  echo "  MySQL OK"
fi

# 2. Redis (si no está corriendo)
redis-cli ping > /dev/null 2>&1 || {
  echo "➤ Redis..."
  sudo service redis-server start 2>/dev/null || redis-server --daemonize > /dev/null 2>&1 || true
  echo "  Redis OK"
}

# 3. CubeMaster
if pgrep -f "cubemaster$" > /dev/null; then
  echo "➤ CubeMaster ya corriendo"
else
  echo "➤ CubeMaster..."
  CUBE_MASTER_CONFIG_PATH=$HOME/.config/cube-sandbox/cubemaster.yaml \
    nohup "$BIN/cubemaster" > "$LOG/cubemaster.log" 2>&1 &
  sleep 2
  echo "  PID $(pgrep -f cubemaster)"
fi

# 4. cube-api
if pgrep -f "cube-api$" > /dev/null; then
  echo "➤ cube-api ya corriendo"
else
  echo "➤ cube-api..."
  nohup "$BIN/cube-api" --bind 0.0.0.0:3000 --cubemaster-url http://127.0.0.1:8089 \
    > "$LOG/cube-api.log" 2>&1 &
  sleep 1
  echo "  PID $(pgrep -f cube-api)"
fi

# 5. network-agent (ESTE NECESITA SUDO por eBPF)
if pgrep -f "cube-network-agent" > /dev/null; then
  echo "➤ network-agent ya corriendo"
else
  echo "➤ network-agent (sudo)..."
  sudo sh -c 'nohup /home/vuos/.local/bin/cube-network-agent \
    -eth-name wlp3s0 \
    -listen unix:///tmp/cube/network-agent.sock \
    -grpc-listen unix:///tmp/cube/network-agent-grpc.sock \
    -health-listen 127.0.0.1:19090 \
    -state-dir /tmp/cube-network-state \
    > /home/vuos/.local/state/cube-sandbox/log/network-agent.log 2>&1 &'
  sleep 2
  echo "  PID $(pgrep -f cube-network-agent)"
fi

# 6. Cubelet
if pgrep -f "cubelet$" > /dev/null; then
  echo "➤ Cubelet ya corriendo"
else
  echo "➤ Cubelet..."
  CUBE_SANDBOX_NODE_IP=$(ip -br addr show wlp3s0 | awk '{print $3}' | cut -d/ -f1) \
    nohup "$BIN/cubelet" > "$LOG/cubelet.log" 2>&1 &
  sleep 2
  echo "  PID $(pgrep -f cubelet)"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Verificación:"
echo "  CubeMaster:  $(curl -sf http://127.0.0.1:8089/notify/health && echo OK || echo FAIL)"
echo "  cube-api:    $(curl -sf http://127.0.0.1:3000/health && echo OK || echo FAIL)"
echo "  network-agent: $(curl -sf http://127.0.0.1:19090/healthz && echo OK || echo FAIL)"
echo "═══════════════════════════════════════════"
echo ""
echo "Comandos útiles:"
echo "  Ver logs:  tail -f $LOG/*.log"
echo "  Detener:   pkill -f 'cubemaster|cube-api|cubelet' && sudo pkill -f cube-network-agent"
