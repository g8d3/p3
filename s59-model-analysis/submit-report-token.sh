#!/bin/zsh
# submit-report-token.sh — Crear issue con token de GitHub
# 1. Genera token en: https://github.com/settings/tokens (scope: repo)
# 2. Ejecuta: ./submit-report-token.sh TU_TOKEN

set -e
DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO="earendil-works/pi-mono"
REPORT_FILE="$DIR/report-github.md"
TITLE="Screen jumping in Termux via SSH + tmux due to fullRender loop and \\x1b[3J"

TOKEN="${1:-}"

if [[ -z "$TOKEN" ]]; then
  echo "Uso: $0 <github_token>"
  echo ""
  echo "1. Genera un token en https://github.com/settings/tokens"
  echo "   Scope necesario: repo"
  echo "2. Ejecuta: $0 ghp_tu_token_aqui"
  exit 1
fi

if [[ ! -f "$REPORT_FILE" ]]; then
  echo "✗ No se encuentra $REPORT_FILE"
  exit 1
fi

echo "Creando issue en $REPO..."
echo ""

# Usar el token directamente con la API de GitHub
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(cat <<ENDOFJSON
{
  "title": "$TITLE",
  "body": $(cat "$REPORT_FILE" | jq -Rs .)
}
ENDOFJSON
)" \
  "https://api.github.com/repos/$REPO/issues" \
  | jq '{ url: .html_url, number: .number, title: .title, state: .state }'

echo ""
echo "✓ Si no hay errores, el issue está creado."
