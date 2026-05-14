#!/bin/zsh
# submit-report-v2.sh — Crea issue en GitHub (modo debug)
# Uso: ./submit-report-v2.sh <token>

set -e

DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO="earendil-works/pi"
REPORT="$DIR/report-github.md"
TITLE="Screen jumping in Termux via SSH + tmux due to fullRender loop and ESC[3J"

TOKEN="${1:-}"

if [[ -z "$TOKEN" ]]; then
  echo "Uso: $0 <github_token>"
  echo ""
  echo "1. Ve a https://github.com/settings/tokens"
  echo "2. Crea un token con scope 'repo'"
  echo "3. Ejecuta: $0 ghp_tu_token_aqui"
  exit 1
fi

if [[ ! -f "$REPORT" ]]; then
  echo "✗ No se encuentra $REPORT"
  exit 1
fi

echo "==> 1. Verificando token..."
curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/user | jq '{ login: .login, id: .id }'

echo ""
echo "==> 2. Creando issue en $REPO..."
echo ""

BODY=$(cat "$REPORT" | jq -Rs .)

curl -sL -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
  \"title\": \"$TITLE\",
  \"body\": $BODY,
  \"labels\": [\"bug\"]
}" \
  "https://api.github.com/repos/$REPO/issues" 2>&1 | tee /tmp/pi-issue-result.txt

echo ""
echo "==> 3. Resultado guardado en /tmp/pi-issue-result.txt"
echo "    Si el issue se creó, busca la URL ahí."
