#!/bin/bash
echo "══════════════════════════════════════════════"
echo "TEST 4: ACCIONES PERSONALIZADAS"
echo "══════════════════════════════════════════════"
echo ""

# Reset
curl -s -X POST http://localhost:8080/api/file -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null

echo "--- 4.1: FIND & REPLACE ---"
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"FR","type":"FIND_REPLACE","findText":"test","replaceText":"correo"},
    "selection": {"type":"COLUMNS","indices":[1],"cells":[]}
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
emails = [d['rows'][i][1] for i in range(5)]
print('  Emails:', emails)
ok = all('correo' in e for e in emails)
print('  ' + ('OK' if ok else 'FAIL'))
"

echo "--- 4.2: TRANSFORM reverse ---"
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Rev","type":"TRANSFORM","transformExpression":"reverse"},
    "selection": {"type":"CELLS","indices":[0,1,2],"cells":[
      {"row":0,"col":0},{"row":1,"col":0},{"row":2,"col":0}
    ]}
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('  Nombres:', [d['rows'][i][0] for i in range(3)])
"

echo "--- 4.3: TRANSFORM length ---"
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Len","type":"TRANSFORM","transformExpression":"length"},
    "selection": {"type":"COLUMNS","indices":[3],"cells":[]}
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('  Longitudes:', [d['rows'][i][3] for i in range(5)])
"

echo "--- 4.4: PREFIX ---"
curl -s -X POST http://localhost:8080/api/file -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Pref","type":"PREFIX","findText":"Sr. "},
    "selection": {"type":"CELLS","indices":[3,4],"cells":[
      {"row":3,"col":0},{"row":4,"col":0}
    ]}
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('  Nombres:', [d['rows'][i][0] for i in range(3,5)])
"

echo "--- 4.5: SUFFIX ---"
curl -s -X POST http://localhost:8080/api/file -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Suf","type":"SUFFIX","findText":"!!!"},
    "selection": {"type":"ROWS","indices":[0],"cells":[]
  }
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('  Fila 0:', d['rows'][0])
"

echo "--- 4.6: TRANSFORM substr(0,3) ---"
curl -s -X POST http://localhost:8080/api/file -H 'Content-Type: application/json' \
  -d '{"action":"open","path":"data/pruebas.csv"}' > /dev/null
curl -s -X POST http://localhost:8080/api/action/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "action": {"name":"Sub","type":"TRANSFORM","transformExpression":"substr(0,3)"},
    "selection": {"type":"COLUMNS","indices":[0],"cells":[]}
  }' | python3 -c "
import sys,json; d=json.load(sys.stdin)
nombres = [d['rows'][i][0] for i in range(5)]
print('  substr(0,3):', nombres)
print('  ' + ('OK - todos <= 3 chars' if all(len(n) <= 3 for n in nombres) else 'some are longer'))
"

echo ""
echo "✅ TEST 4 COMPLETADO"
