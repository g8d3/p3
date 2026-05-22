#!/usr/bin/env bash
# setup-cubesandbox-permissions.sh
# Permisos completos para CubeSandbox en modo usuario
# Correr UNA VEZ. Pedirá sudo.

set -euo pipefail
BIN_DIR="$HOME/.local/bin"

echo "═══════════════════════════════════════════════"
echo "  CubeSandbox - Permisos completos"
echo "═══════════════════════════════════════════════"

# 1. Grupo kvm
echo "➤ Grupo kvm..."
sudo usermod -aG kvm "$USER" 2>/dev/null || true

# 2. Capacidades especiales para network-agent
echo "➤ Capacidades eBPF + red..."
sudo setcap cap_net_admin,cap_bpf,cap_perfmon+ep "$BIN_DIR/cube-network-agent" 2>/dev/null
sudo setcap cap_net_admin+ep "$BIN_DIR/cube-hypervisor" 2>/dev/null
sudo setcap cap_net_admin+ep "$BIN_DIR/cubelet" 2>/dev/null

# 3. Sudoers: permitir network-agent sin contraseña
echo "➤ Sudoers (NOPASSWD para network-agent)..."
echo "$USER ALL=(root) NOPASSWD: $BIN_DIR/cube-network-agent" | \
  sudo tee /etc/sudoers.d/cube-network-agent > /dev/null 2>&1 || true

# 4. Directorio de logs
sudo mkdir -p /data/log/network-agent 2>/dev/null || true
sudo chown "$USER:$USER" /data /data/log /data/log/network-agent 2>/dev/null || true

echo ""
echo "Verificación:"
getcap "$BIN_DIR/cube-network-agent" 2>/dev/null || true
getcap "$BIN_DIR/cube-hypervisor" 2>/dev/null || true
getcap "$BIN_DIR/cubelet" 2>/dev/null || true
echo ""

echo "═══════════════════════════════════════════════"
echo "Listo. Ahora podés correr ./start.sh sin que"
echo "pida contraseña para el network-agent."
echo "═══════════════════════════════════════════════"
