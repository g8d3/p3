#!/usr/bin/env bash
# fix-cubelet.sh — Config completa + arranque del Cubelet

LOGFILE="/home/vuos/.local/state/cube-sandbox/log/fix-cubelet.log"
exec > "$LOGFILE" 2>&1

echo "═══════════════════════════════════════════"
echo "  Fix Cubelet - Config completo + arranque"
echo "  Log: $LOGFILE"
echo "═══════════════════════════════════════════"

# 1. Matar Cubelet si está corriendo
CUBELET_PID=$(pgrep -x cubelet 2>/dev/null || true)
if [ -n "$CUBELET_PID" ]; then
  sudo kill -9 "$CUBELET_PID" 2>/dev/null || true
  sleep 1
fi

# 2. Crear directorios
echo "➤ Directorios..."
sudo mkdir -p /usr/local/services/cubetoolbox/Cubelet/config
sudo mkdir -p /usr/local/services/cubetoolbox/Cubelet/dynamicconf
sudo mkdir -p /usr/local/services/cubetoolbox/network-agent/state
sudo chown -R vuos:vuos /usr/local/services/cubetoolbox 2>/dev/null || true

# 3. Config principal (TOML)
echo "➤ Config principal (config.toml)..."
cat > /usr/local/services/cubetoolbox/Cubelet/config/config.toml << 'EOF'
[common]
common_timeout = "10s"
enable_network_agent = true
network_agent_endpoint = "grpc+unix:///tmp/cube/network-agent-grpc.sock"
disable_host_cgroup = true
[meta_server_config]
meta_server_endpoint = "127.0.0.1:8089"
status_update_frequency = "10s"
[host]
scheduler_label = "default-cluster"
[host.quota]
mcpu_limit = 0
mem_limit = ""
mvm_limit = 0
creation_concurrent_num = 0
EOF

# 4. Config dinámico (YAML)
echo "➤ Config dinámico (conf.yaml)..."
cat > /usr/local/services/cubetoolbox/Cubelet/dynamicconf/conf.yaml << 'EOF'
common:
  common_timeout: 10s
  enable_network_agent: true
  network_agent_endpoint: "grpc+unix:///tmp/cube/network-agent-grpc.sock"
  disable_host_cgroup: true
meta_server_config:
  meta_server_endpoint: "127.0.0.1:8089"
  status_update_frequency: 10s
host:
  scheduler_label: "default-cluster"
  quota:
    mcpu_limit: 0
    mem_limit: ""
    mvm_limit: 0
    creation_concurrent_num: 0
EOF

# 5. Fix socket
echo "➤ Socket..."
sudo chmod 777 /tmp/cube/network-agent-grpc.sock 2>/dev/null || true

# 6. Arrancar Cubelet
echo "➤ Arrancando Cubelet..."
sudo CUBE_SANDBOX_NODE_IP=192.168.0.31 \
    /home/vuos/.local/bin/cubelet \
    --config /usr/local/services/cubetoolbox/Cubelet/config/config.toml \
    --log-level debug \
    --address 127.0.0.1:9999 \
    > /home/vuos/.local/state/cube-sandbox/log/cubelet.log 2>&1 &

sleep 4

# 7. Verificar
PID=$(pgrep -f "cubelet --config" 2>/dev/null || echo "no corre")
echo ""
echo "PID: $PID"
echo "Log: $(wc -c < /home/vuos/.local/state/cube-sandbox/log/cubelet.log 2>/dev/null) bytes"
tail -5 /home/vuos/.local/state/cube-sandbox/log/cubelet.log 2>/dev/null || true
echo "Puerto 9999:"
ss -tlnp | grep 9999 || echo "no escucha"
echo ""
echo "═══════════════════════════════════════════"
