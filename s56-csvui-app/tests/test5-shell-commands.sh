#!/bin/bash
# Test 5: Shell command actions — the bug you reported
# Commands execute but cells sometimes don't update

SERVER="http://localhost:8080"
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  ✅ $name"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name — esperado: '$expected' | obtenido: '$actual'"
    FAIL=$((FAIL+1))
  fi
}

echo "══════════════════════════════════════════════"
echo "TEST 5: COMANDOS SHELL"
echo "══════════════════════════════════════════════"
echo ""

# Load test data
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null

echo "--- 5.1: echo básico con {cell} (debe devolver el mismo texto) ---"
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Echo","type":"SHELL_COMMAND","commandTemplate":"echo {cell}"},
    "selection": {"type":"CELLS","indices":[0],"cells":[{"row":0,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][0][0])")
check "echo Ana García" "Ana García" "$VAL"

echo "--- 5.2: wc -w (contar palabras con {cell}) ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Wc","type":"SHELL_COMMAND","commandTemplate":"echo {cell} | wc -w"},
    "selection": {"type":"CELLS","indices":[3],"cells":[{"row":3,"col":3}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][3][3])")
check "wc -w 'Regular' → 1" "1" "$VAL"

echo "--- 5.3: sha256sum (pipe sin {cell}) ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Sha","type":"SHELL_COMMAND","commandTemplate":"sha256sum | cut -d\" \" -f1"},
    "selection": {"type":"CELLS","indices":[0],"cells":[{"row":0,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][0][0])")
echo "  sha256('Ana García') = ${VAL:0:20}..."
if [ ${#VAL} -eq 64 ]; then
  echo "  ✅ SHA256 tiene 64 caracteres (correcto)"
  PASS=$((PASS+1))
else
  echo "  ❌ SHA256 debería tener 64 chars, tiene ${#VAL}"
  FAIL=$((FAIL+1))
fi

echo "--- 5.4: MÚLTIPLES celdas con una columna ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Upper","type":"SHELL_COMMAND","commandTemplate":"echo {cell} | tr '[:lower:]' '[:upper:]'"},
    "selection": {"type":"COLUMNS","indices":[0],"cells":[]}
  }')
echo "$RESP" | python3 -c "
import sys,json
d = json.load(sys.stdin)
vals = [d['rows'][i][0] for i in range(5)]
expected = ['ANA GARCÍA', 'CARLOS LÓPEZ', 'MARÍA TORRES', 'JOSÉ RAMÍREZ', 'LAURA SÁNCHEZ']
ok = all(v == e for v,e in zip(vals, expected))
print(f'  Resultados: {vals}')
print(f'  {\"✅ CORRECTO\" if ok else \"❌ FALLÓ\"}')
if ok: open('/dev/null','w')
"

echo "--- 5.5: CELDA CON ESPACIOS (caso borde) ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Wc","type":"SHELL_COMMAND","commandTemplate":"echo {cell} | wc -w"},
    "selection": {"type":"CELLS","indices":[2],"cells":[{"row":2,"col":3}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][2][3])")
check "wc -w 'Muy bien, sigue así' → 4" "4" "$VAL"

echo "--- 5.6: COMANDO QUE FALLA (debe mostrar error) ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Falla","type":"SHELL_COMMAND","commandTemplate":"comando_inexistente {cell}"},
    "selection": {"type":"CELLS","indices":[0],"cells":[{"row":0,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][0][0])")
if echo "$VAL" | grep -q "Error\|Exit\|not found"; then
  echo "  ✅ Muestra error correctamente: $VAL"
  PASS=$((PASS+1))
else
  echo "  ❌ Debería mostrar error, pero se ve: $VAL"
  FAIL=$((FAIL+1))
fi

echo ""
echo "══════════════════════════════════════════════"
echo "RESULTADOS TEST 5: $PASS pasaron, $FAIL fallaron"
echo "══════════════════════════════════════════════"
