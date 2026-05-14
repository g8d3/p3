#!/bin/bash
# Test 6: Diagnóstico del bug de escapado en comandos shell
# El problema: {cell} se reemplaza sin escapar → comandos se rompen
# con espacios, acentos, quotes

SERVER="http://localhost:8080"
PASS=0; FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  ✅ $name"; PASS=$((PASS+1))
  else
    echo "  ❌ $name — esperado: '$expected' | obtenido: '$actual'"
    FAIL=$((FAIL+1))
  fi
}

echo "══════════════════════════════════════════════"
echo "TEST 6: DIAGNÓSTICO — ESCAPADO EN SHELL"
echo "══════════════════════════════════════════════"
echo ""
echo "Creando CSV con casos borde..."
cat > /home/vuos/code/p3/s56/data/escaping-test.csv << 'CSV'
nombre,valor
"Ana García","texto normal"
"Carlos O'Brien","apóstrofe"
""Juan Pérez"","double quotes"
"$USER","variable shell"
"a  b  c","multiples espacios"
CSV

curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/escaping-test.csv"}' > /dev/null

echo "--- 6.1: Texto con espacios (debe mantenerlos) ---"
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action":{"name":"Echo","type":"SHELL_COMMAND","commandTemplate":"echo {cell}"},
    "selection":{"type":"CELLS","indices":[0],"cells":[{"row":0,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][0][0])")
check "Mantener espacios entre texto normal" "Ana García" "$VAL"

echo "--- 6.2: Apóstrofe (O'Brien) — PROBABLEMENTE FALLA ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/escaping-test.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action":{"name":"Echo","type":"SHELL_COMMAND","commandTemplate":"echo {cell}"},
    "selection":{"type":"CELLS","indices":[1],"cells":[{"row":1,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][1][0])")
if echo "$VAL" | grep -qi "error\|exit"; then
  echo "  ⚠️  Error esperado con apóstrofe: $VAL"
elif [ "$VAL" = "Carlos O'Brien" ]; then
  echo "  ✅ Funciona con apóstrofe"
  PASS=$((PASS+1))
else
  echo "  ❌ Apóstrofe: esperado 'Carlos O'Brien', obtenido '$VAL'"
  FAIL=$((FAIL+1))
fi

echo "--- 6.3: Double quotes en el valor — PROBABLEMENTE FALLA ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/escaping-test.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action":{"name":"Echo","type":"SHELL_COMMAND","commandTemplate":"echo {cell}"},
    "selection":{"type":"CELLS","indices":[2],"cells":[{"row":2,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][2][0])")
if echo "$VAL" | grep -qi "error\|exit"; then
  echo "  ⚠️  Error esperado con double quotes: $VAL"
elif [ "$VAL" = '"Juan Pérez"' ]; then
  echo "  ✅ Funciona con double quotes"
  PASS=$((PASS+1))
else
  echo "  ❌ Double quotes: esperado '\"Juan Pérez\"', obtenido '$VAL'"
  FAIL=$((FAIL+1))
fi

echo "--- 6.4: Variable $USER — NO DEBE expandirse ---"
curl -s -X POST "$SERVER/api/file" -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/escaping-test.csv"}' > /dev/null
RESP=$(curl -s -X POST "$SERVER/api/action/execute" \
  -H 'Content-Type: application/json' \
  -d '{
    "action":{"name":"Echo","type":"SHELL_COMMAND","commandTemplate":"echo {cell}"},
    "selection":{"type":"CELLS","indices":[3],"cells":[{"row":3,"col":0}]}
  }')
VAL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['rows'][3][0])")
if [ "$VAL" = '$USER' ]; then
  echo "  ✅ \$USER NO se expandió (seguro)"
  PASS=$((PASS+1))
elif [ "$VAL" != "vuos" ] && [ -n "$VAL" ]; then
  echo "  ⚠️  \$USER se expandió a '$VAL' — potencial inseguro"
  FAIL=$((FAIL+1))
else
  echo "  ❌ \$USER: esperado '\$USER', obtenido '$VAL'"
  FAIL=$((FAIL+1))
fi

echo ""
echo "══════════════════════════════════════════════"
echo "RESULTADOS TEST 6: $PASS pasaron, $FAIL fallaron"
echo "══════════════════════════════════════════════"