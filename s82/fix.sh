#!/usr/bin/env bash
# fix.sh - Restaura conectividad si el proxy muere
set -e

echo "=== 1. Matar proxy ==="
sudo pkill -f "mitm.py" 2>/dev/null || true
fuser -k 8443/tcp 2>/dev/null || true

echo "=== 2. Eliminar reglas iptables ==="
sudo iptables -t nat -F 2>/dev/null
sudo ip6tables -t nat -F 2>/dev/null
sudo nft flush ruleset 2>/dev/null

echo "=== 3. Reiniciar DNS ==="
sudo systemctl restart systemd-resolved 2>/dev/null || true

echo "=== 4. Verificar ==="
curl -s -o /dev/null -w "HTTP %{http_code} - OK\n" https://www.google.com --max-time 5
echo ""
echo "✓ Internet restaurado. Para reiniciar el proxy:"
echo "  ./mitm.py --iptables-add && sudo python3 mitm.py"
