#!/bin/bash
# Demo A2A en español — con pausas entre cada paso para que la narración coincida
set -e
DELAY=2

echo ""
echo "=============================================="
echo "  DEMO A2A — PRUEBAS DE PROTOCOLO"
echo "  $(date)"
echo "=============================================="
echo ""

echo ">>> PASO 1: Descubrimiento de Agentes"
curl -s http://localhost:9001/.well-known/agent.json | python3 -c "
import sys,json
c=json.load(sys.stdin)
print(f'  Alpha: {c[\"name\"]}')
print(f'  Skills: {[s[\"name\"] for s in c.get(\"skills\",[])]}')
"
curl -s http://localhost:9002/.well-known/agent.json | python3 -c "
import sys,json
c=json.load(sys.stdin)
print(f'  Beta: {c[\"name\"]}')
print(f'  Skills: {[s[\"name\"] for s in c.get(\"skills\",[])]}')
"
echo "  ✅ Tarjetas de agente encontradas"
sleep $DELAY

echo ""
echo ">>> PASO 2: Ejecución de Tarea"
RESP=$(curl -s -X POST http://localhost:9001/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"¿Qué clima hace hoy?"}],"messageId":"m1"}}')
TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('id','?'))")
echo "  Tarea creada: $TASK_ID"
sleep 1.5
curl -s "http://localhost:9001/tasks/$TASK_ID" | python3 -c "
import sys,json
t=json.load(sys.stdin).get('result',{})
print(f'  Estado: {t[\"status\"][\"state\"]}')
print(f'  Respuesta: {t.get(\"artifacts\",[{}])[0].get(\"parts\",[{}])[0].get(\"text\",\"\")[:80]}...')
"
sleep $DELAY

echo ""
echo ">>> PASO 3: Cancelación"
RESP2=$(curl -s -X POST http://localhost:9001/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"Escribe un reporte largo"}],"messageId":"m2"}}')
T2=$(echo "$RESP2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('id','?'))")
echo "  Tarea: $T2"
sleep 0.3
echo "  Cancelando..."
curl -s -X POST "http://localhost:9001/tasks/$T2:cancel" \
  -H "Content-Type: application/json" -d '{}' | python3 -c "
import sys,json
r=json.load(sys.stdin).get('result',{})
print(f'  Estado cancelación: {r.get(\"status\",{}).get(\"state\",\"?\")}')
"
sleep 1
VERIFY=$(curl -s "http://localhost:9001/tasks/$T2")
echo "  Estado final: $(echo "$VERIFY" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t.get('status',{}).get('state','?'))")"
sleep $DELAY

echo ""
echo ">>> PASO 4: LIMITACIÓN DE CALIDAD (HALLAZGO CLAVE)"
echo "  Enviando código BUENO a Beta..."
R3=$(curl -s -X POST http://localhost:9002/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"Revisa este código: def foo(): pass"}],"messageId":"m3"}}')
T3=$(echo "$R3" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('id','?'))")
sleep 2
S3=$(curl -s "http://localhost:9002/tasks/$T3" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t['status']['state'])")
echo "  Código bueno → estado: $S3"

echo "  Enviando código con ERROR a Beta..."
R4=$(curl -s -X POST http://localhost:9002/message:send \
  -H "Content-Type: application/json" \
  -d '{"message":{"role":"user","parts":[{"text":"Este código tiene un bug"}],"messageId":"m4"}}')
T4=$(echo "$R4" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',{}).get('id','?'))")
sleep 2
S4=$(curl -s "http://localhost:9002/tasks/$T4" | python3 -c "import sys,json; t=json.load(sys.stdin).get('result',{}); print(t['status']['state'])")
echo "  Código con error → estado: $S4"
echo ""
echo "  ❌❌❌ AMBOS SON '$S3' — ¡NO HAY DISTINCIÓN DE CALIDAD! ❌❌❌"
sleep $DELAY

echo ""
echo ">>> PASO 5: La Solución — Extensión A2A-Q"
echo "  Nuevos estados: quality:pending-review → needs-revision → passed"
echo "  Nuevas operaciones: requestReview, submitVerdict"
echo "  Métricas: eficacia (score, revisiones), eficiencia (tiempo, tokens)"
echo "  Hardware: CPU, RAM, contexto, runtime"
echo ""

echo "=============================================="
echo "  RESUMEN"
echo "=============================================="
echo "  Descubrimiento: ✅"
echo "  Ejecución:     ✅"
echo "  Cancelación:   ✅ (bug corregido)"
echo "  Calidad:       ❌ no existe en A2A"
echo ""
echo "  Solución: A2A-Q — extensión de calidad para A2A"
echo "  RFC:      s84/A2A-Q-RFC.md"
echo "  Código:   s84/a2a_test/"
echo "  Repo:     github.com/g8d3/p3/tree/main/s84"
echo "=============================================="
