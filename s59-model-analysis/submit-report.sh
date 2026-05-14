#!/bin/zsh
# submit-report.sh — Prepara todo y crea el issue en GitHub
# Funciona desde SSH (no necesita navegador en el servidor remoto)

set -e

DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO="earendil-works/pi-mono"
REPORT_FILE="$DIR/report-github.md"
TITLE="Screen jumping in Termux via SSH + tmux due to fullRender loop and \\x1b[3J"

echo "══════════════════════════════════════════════════"
echo "  Reporte de bug para pi-tui — $REPO"
echo "══════════════════════════════════════════════════"
echo ""

# --- 1. Verificar/instalar gh ---
if ! command -v gh &>/dev/null; then
  echo "[1/4] Instalando GitHub CLI (gh)..."
  sudo apt update -qq && sudo apt install gh -y
  echo "  ✓ gh instalado"
else
  echo "[1/4] ✓ gh ya instalado ($(gh --version 2>&1 | head -1))"
fi

# --- 2. Verificar autenticación ---
echo ""
echo "[2/4] Verificando autenticación con GitHub..."
echo ""
if gh auth status &>/dev/null; then
  echo "  ✓ Ya estás autenticado como $(gh auth status 2>&1 | grep -oP 'account \K\S+' || gh auth status 2>&1 | grep -o 'Logged in to [^ ]*' | head -1)"
else
  echo "  ⚠ Necesitas autenticarte."
  echo ""
  echo "  Como estás por SSH, usaremos el flujo de 'código de dispositivo':"
  echo ""
  echo "  1. Ejecuta: gh auth login --web"
  echo "  2. Te aparecerá un código como:  ABCD-1234"
  echo "  3. En tu navegador LOCAL (o celular) abre:"
  echo "     https://github.com/login/device"
  echo "  4. Ingresa el código y autoriza"
  echo "  5. Vuelve aquí y continua"
  echo ""
  echo "  ¿Ejecuto 'gh auth login --web' ahora? (s/n)"
  read -r answer
  if [[ "$answer" == "s" || "$answer" == "S" || "$answer" == "y" || "$answer" == "Y" ]]; then
    gh auth login --web
    echo "  ✓ Autenticación completada"
  else
    echo "  ⏸ Omite autenticación. Puedes hacerlo luego manualmente con:"
    echo "     gh auth login --web"
    echo "  Y luego vuelve a ejecutar este script."
  fi
fi

# --- 3. Verificar que existe el reporte ---
echo ""
echo "[3/4] Verificando archivo de reporte..."
if [[ ! -f "$REPORT_FILE" ]]; then
  echo "  ✗ No se encuentra $REPORT_FILE"
  echo "  Buscando en $DIR..."
  ls "$DIR"/*.md 2>/dev/null || echo "  (sin archivos .md)"
  exit 1
fi
echo "  ✓ Reporte encontrado ($(wc -c < "$REPORT_FILE") bytes)"

# --- 4. Verificar autenticación antes de crear issue ---
echo ""
if ! gh auth status &>/dev/null; then
  echo "  ⚠ No estás autenticado. Crea el issue manualmente:"
  echo "  1. Ve a https://github.com/$REPO/issues/new"
  echo "  2. Título: $TITLE"
  echo "  3. Copia y pega el contenido de:"
  echo "     $REPORT_FILE"
  exit 1
fi

echo "[4/4] Creando issue en GitHub..."
echo ""
gh issue create \
  -R "$REPO" \
  --title "$TITLE" \
  --body "$(cat "$REPORT_FILE")" \
  --label "bug"

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Issue creado exitosamente!"
echo "  Puedes verlo en: https://github.com/$REPO/issues"
echo "══════════════════════════════════════════════════"
