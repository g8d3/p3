# GUIÓN: s82 Multi-Agent System — Video Escena por Escena
# Cada escena: duración, qué se ve exactamente, qué se dice

## ESCENA 1 — Dashboard (15s)
Duración: 15s
Setup: xterm con 'watch -n 2 curl -s http://localhost:9093/api/team | python3 -m json.tool | head -30'
Qué se ve: JSON del dashboard con agentes activos, stats, helps
Narración: "Este es el dashboard del sistema multi-agente s82. Aquí vemos todos los agentes activos: worker uno, worker dos, supervisor. Cada uno reporta su estado en tiempo real — segundos desde su última actividad, CPU, memoria."

## ESCENA 2 — Proxy Health (15s)
Duración: 15s
Setup: xterm con 'watch -n 2 curl -s http://localhost:9098/health | python3 -c "import json,sys;d=json.load(sys.stdin);[print(f\"{a}: last_s={i.get(chr(108)+chr(97)+chr(115)+chr(116)+chr(95)+chr(115))} idle={i.get(chr(105)+chr(100)+chr(108)+chr(101))} status={i.get(chr(115)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115))}\") for a,i in d[\"agents\"].items()]"'
Qué se ve: Lista de agentes con last_s, idle status, estado
Narración: "El proxy watchdog monitorea cada llamada a los modelos de lenguaje. Detecta automáticamente cuando un agente está inactivo por más de cuarenta y cinco segundos, y lo marca como idle. Aquí vemos worker uno y worker dos activos, el supervisor funcionando."

## ESCENA 3 — Tmux Workers (20s)
Duración: 20s
Setup: xterm con 'watch -n 2 tmux list-windows -t main'
Qué se ve: Lista de ventanas tmux: supervisor, worker-1, worker-2
Narración: "El sistema corre sobre tmux con ventanas dedicadas. Cada worker es un agente autónomo con su propia sesión. El supervisor orquesta las tareas, worker uno y worker dos ejecutan el trabajo. Cuando un worker está libre, el supervisor le asigna automáticamente una nueva tarea."

## ESCENA 4 — Supervisor + Helperd Logs (20s)
Duración: 20s
Setup: Two xterms side by side: left='watch -n 3 tail -5 data/supervisor.log', right='watch -n 3 tail -5 data/helperd.log'
Qué se ve: Logs del supervisor (task assignments) y helperd (help events)
Narración: "El supervisor asigna tareas cada cinco segundos a los workers inactivos. Aquí vemos su log con las tareas asignadas. El helperd, por su parte, implementa el reflejo cooperativo: cuando un worker se queda atascado, detecta el problema y pide ayuda al worker más cercano. Esto permite que el equipo se auto-gestione sin intervención humana."

## ESCENA 5 — Cierre (10s)
Duración: 10s
Setup: Todos los xterms visibles
Qué se ve: Vista general del sistema con múltiples ventanas
Narración: "Este es el ecosistema s82 funcionando. Agentes autónomos que trabajan en equipo, se monitorean entre sí, y producen resultados reales: señales de trading en HyperLiquid, contenido por screen recording, y exploración de nuevos proyectos."

## Total: 80s (~1:20)
