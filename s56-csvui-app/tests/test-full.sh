#!/bin/bash
# Pruebas completas de CSV Tabulator
# Requiere: agente-browser, servidor corriendo en :8080

SERVER="http://localhost:8080"
PASS=0
FAIL=0
ERRORS=""

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  ✅ $name"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name — esperado: '$expected' | obtenido: '$actual'"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  ❌ $name"
  fi
}

check_contains() {
  local name="$1" expected="$2" actual="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo "  ✅ $name"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name — debería contener '$expected'"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  ❌ $name"
  fi
}

echo "╔══════════════════════════════════════════════╗"
echo "║   CSV Tabulator — Pruebas completas         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. API básica ──────────────────────────────────────
echo "━━━━━ 1. API básica ━━━━━"
INFO=$(curl -s "$SERVER/api/info")
check_contains "Info endpoint responde" "status" "$INFO"
check_contains "Info tiene dataDir" "dataDir" "$INFO"

FILES=$(curl -s "$SERVER/api/files")
check_contains "Lista archivos" "sample.csv" "$FILES"

# ── 2. Cargar archivo ──────────────────────────────────
echo ""
echo "━━━━━ 2. Cargar archivo ━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"sample.csv"}')
STATUS=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
ROWS=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["rowCount"])')
check "Abrir sample.csv" "Opened: sample.csv" "$STATUS"
check "4 filas de datos" "4" "$ROWS"

# ── 3. Editar celda ────────────────────────────────────
echo ""
echo "━━━━━ 3. Editar celda ━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/cell" -H 'Content-Type: application/json' \
  -d '{"row":0,"col":0,"value":"ALICE"}')
CELL=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["rows"][0][0])')
check "Editar celda (0,0)" "ALICE" "$CELL"

# ── 4. Acciones built-in ──────────────────────────────
echo ""
echo "━━━━━ 4. Acciones built-in ━━━━━"
# Re-load
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"sample.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" -H 'Content-Type: application/json' \
  -d '{"action":{"name":"Upper","type":"TO_UPPER"},"selection":{"type":"CELLS","indices":[],"cells":[{"row":0,"col":0},{"row":1,"col":0}]}}')
N0=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["rows"][0][0])')
N1=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["rows"][1][0])')
check "Uppercase Alice" "ALICE" "$N0"
check "Uppercase Bob" "BOB" "$N1"

# ── 5. Shell command ──────────────────────────────────
echo ""
echo "━━━━━ 5. Shell command ─━━━━"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"sample.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" -H 'Content-Type: application/json' \
  -d '{"action":{"name":"Wc","type":"SHELL_COMMAND","commandTemplate":"echo {cell} | wc -w"},"selection":{"type":"CELLS","indices":[],"cells":[{"row":0,"col":3}]}}')
WC=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["rows"][0][3])')
check "wc -w de fecha" "1" "$WC"

# ── 6. Custom action ──────────────────────────────────
echo ""
echo "━━━━━ 6. Custom action ─━━━━"
RESP=$(curl -s -X POST "$SERVER/api/actions" -H 'Content-Type: application/json' \
  -d '{"name":"TestRev","type":"TRANSFORM","transformExpression":"reverse"}')
NACT=$(echo "$RESP" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
echo "  Acciones despues de crear: $NACT"

# ── 7. Row operations ────────────────────────────────
echo ""
echo "━━━━━ 7. Row ops ─━━━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/row" -H 'Content-Type: application/json' \
  -d '{"action":"add"}')
check_contains "Add row aumenta filas" '"rowCount":5' "$RESP"

RESP=$(curl -s -X POST "$SERVER/api/row" -H 'Content-Type: application/json' \
  -d '{"action":"delete","index":4}')
check_contains "Delete row disminuye filas" '"rowCount":4' "$RESP"

# ── 8. Column operations ─────────────────────────────
echo ""
echo "━━━━━ 8. Column ops ─━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/column" -H 'Content-Type: application/json' \
  -d '{"action":"add"}')
check_contains "Add col" '"colCount":5' "$RESP"

RESP=$(curl -s -X POST "$SERVER/api/column" -H 'Content-Type: application/json' \
  -d '{"action":"rename","index":0,"header":"FullName"}')
H0=$(echo "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["headers"][0])')
check "Renombrar columna" "FullName" "$H0"

# ── 9. New file ──────────────────────────────────────
echo ""
echo "━━━━━ 9. New file ─━━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"new"}')
check_contains "New file" '"rowCount":3' "$RESP"

# ── 10. Save ─────────────────────────────────────────
echo ""
echo "━━━━━ 10. Save ─━━━━━━━━"
RESP=$(curl -s -X POST "$SERVER/api/save" -H 'Content-Type: application/json' \
  -d '{"path":"/tmp/test-save.csv"}')
check_contains "Save" '"status":"Saved' "$RESP"

# ── 11. Browser UI ────────────────────────────────────
echo ""
echo "━━━━━ 11. Browser UI ─━━━━"
agent-browser open "$SERVER/" 2>&1
sleep 4
agent-browser snapshot -i -C 2>&1 > /tmp/ui-snapshot.txt

# Ruta fija visible
UI_PATH=$(agent-browser get text '#file-path-display' 2>&1)
check_contains "Ruta fija visible" "📁" "$UI_PATH"

# Dropdown con archivos
grep -q "sample.csv" /tmp/ui-snapshot.txt && echo "  ✅ Dropdown lista sample.csv" && PASS=$((PASS+1)) || echo "  ❌ Dropdown sin sample.csv"

# Tabla visible
TROWS=$(echo "document.querySelectorAll('.tabulator-row').length" | agent-browser eval --stdin 2>&1)
echo "  Filas iniciales: $TROWS"

# Sidebar visible
agent-browser get text '#sidebar-content' 2>&1 | grep -q "BUILT-IN" && echo "  ✅ Sidebar con acciones" && PASS=$((PASS+1)) || echo "  ❌ Sidebar vacia"

agent-browser close 2>&1

# ── Resultados ────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   RESULTADOS                                 ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Pasaron: $PASS                                 ║"
echo "║  Fallaron: $FAIL                                ║"
echo "╚══════════════════════════════════════════════╝"
if [ $FAIL -gt 0 ]; then
  echo -e "$ERRORS"
  exit 1
fi
exit 0
