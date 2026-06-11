# s82 — Multi-Agent Autonomous System

> Sistema infinito de agentes cooperativos. Nunca para.

## Ver el sistema ahora

```
http://localhost:9090/p3/s82/           → código fuente
http://localhost:9090/p3/s82/progress/   → documentación de avances
http://localhost:9090/p3/s82/artifacts/  → outputs (videos, scripts)
http://localhost:9093                    → dashboard en vivo
```

## Componentes (todos con auto-reinicio)

| Componente | Rol | Ciclo |
|-----------|-----|-------|
| proxy_watchdog | Intercepta LLMs, detecta inactividad | continuo |
| supervisor | Monitorea salud, reinicia caídos | cada 5s |
| helperd | Reflejo cooperativo (stuck→peer ayuda) | cada 5s |
| sequencer | Asigna tareas infinitas a workers | cada 20s |
| runner | Ejecuta señales de trading continuas | cada 5min |
| dashboard | Web UI del sistema | :9093 |
| busd | Message bus entre agentes | inotify |

## Workers

```
worker-1 → TRADING: señales HyperLiquid, runner, backtest
worker-2 → CONTENIDO: screen recording, videos, documentación
```

## Seguir el progreso

```bash
# Últimas señales de trading
tail -f /home/vuos/code/p3/s82/data/trading_log.csv

# Últimas decisiones del supervisor
tail -f /home/vuos/code/p3/s82/data/supervisor-out.log

# Últimas tareas asignadas
tail -f /home/vuos/code/p3/s82/data/sequencer-out.log

# Ayudas cooperativas
tail -f /home/vuos/code/p3/s82/data/helperd.log

# Ver workers en vivo
tmux capture-pane -t worker-1 -p | tail -5
tmux capture-pane -t worker-2 -p | tail -5
```

## Comandos útiles

```bash
# Estado completo
curl -s http://localhost:9093/api/summary | python3 -m json.tool

# Ver señales de trading
curl -s http://localhost:9093/api/signals | python3 -m json.tool

# Ver ayudas entre agentes
curl -s http://localhost:9093/api/helps | python3 -c "
import sys,json; d=json.load(sys.stdin)
for a,h in d['history'].items():
    print(f'{a}: {len(h)} ayudas, {sum(1 for x in h if x.get(\"resolved\"))} resueltas')
"

# Reiniciar todo
bash /home/vuos/code/p3/s82/scripts/autoheal.sh
```
