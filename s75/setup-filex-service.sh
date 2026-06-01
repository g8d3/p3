#!/usr/bin/env bash
# setup-filex-service.sh — Instala y arranca filex como servicio systemd --user
set -euo pipefail

echo "==> Activando lingering para $USER..."
loginctl enable-linger "$USER" 2>&1 || true

echo "==> Copiando servicio..."
mkdir -p ~/.config/systemd/user
cp /home/vuos/code/filex/serve_md.py ~/code/filex/serve_md.py

# Asegurar que el archivo de servicio existe
if [ ! -f ~/.config/systemd/user/filex.service ]; then
    echo "❌ No se encuentra ~/.config/systemd/user/filex.service"
    echo "   Debería haber sido creado por el agente."
    exit 1
fi

echo "==> Instalando servicio..."
systemctl --user daemon-reload
systemctl --user enable filex.service
systemctl --user start filex.service

echo ""
echo "==> Estado:"
systemctl --user status filex.service --no-pager 2>&1 | head -12

echo ""
echo "✅ filex corriendo en http://localhost:9090"
echo "   Para ver logs: journalctl --user -u filex -f"
echo "   Para reiniciar: systemctl --user restart filex"
