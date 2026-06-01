#!/usr/bin/env bash
# setup-gh-agents.sh — Autentica gh + crea repo privado + sube .agents
set -euo pipefail

echo "╔══════════════════════════════════════════════════╗"
echo "║  Setup: gh auth + repo privado ~/.agents         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Autenticar gh (flujo de dispositivo)
echo "==> PASO 1: Autenticar gh CLI"
echo "    Elige: 'Login with a web browser'"
echo "    Te dará una URL como: https://github.com/login/device"
echo "    y un código tipo: ABCD-1234"
echo "    Abre la URL en tu navegador (móvil) e ingresa el código."
echo ""
unset GITHUB_TOKEN
gh auth login --hostname github.com

echo ""
echo "==> PASO 2: Crear repo privado y subir .agents"
echo ""

cd ~/.agents

# Renombrar branch a main (convención moderna)
git branch -m master main 2>/dev/null || true

# Intentar crear repo + push
if gh repo create g8d3/agents --private --push --source . 2>/dev/null; then
    echo ""
    echo "✅ Repo creado y subido: https://github.com/g8d3/agents"
else
    echo ""
    echo "⚠️  El repo g8d3/agents ya existe. Haciendo push manual..."
    git remote add origin git@github.com:g8d3/agents.git 2>/dev/null || true
    git push -u origin main
    echo ""
    echo "✅ Push completado a https://github.com/g8d3/agents"
fi
