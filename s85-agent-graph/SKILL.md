# Multi-Agent Company System

Sistema multi-agente donde N instancias de opencode trabajan como equipo,
un watcher las monitorea, y un pulso social las mantiene activas.

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│  tmux session                                        │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ worker-1 │  │ worker-2 │  │ watcher  │          │
│  │ opencode │  │ opencode │  │ opencode │          │
│  │ proxy    │  │ proxy    │  │ proxy    │          │
│  │ X_AID=w1 │  │ X_AID=w2 │  │ X_AID=w3 │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │                │
│       └──────────────┴──────────────┘                │
│                        │                             │
│              ┌─────────▼─────────┐                   │
│              │   proxy_watchdog   │  ← intercepta    │
│              │   (localhost:9098) │     requests LLM  │
│              └─────────┬─────────┘                   │
│                        │                             │
│              ┌─────────▼─────────┐                   │
│              │   pulse.py        │  ← monitorea      │
│              │   (daemon)        │     proxy + tmux  │
│              └───────────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## Componentes

### 1. Proxy Watchdog (`s84/proxy/proxy_watchdog.py`)
- Intercepta llamadas LLM de todos los agentes
- Detecta procesos opencode via `/proc` (no necesita registro)
- Health endpoint: `http://localhost:9098/health`
- Log endpoint: `http://localhost:9098/log`
- Identifica agentes por header `X-Agent-ID`
- Detecta idle (45s sin actividad)

### 2. Pulse Social (`pulse.py`)
Daemon que cada N segundos:
- Lee proxy health → detecta agentes sin actividad LLM
- Captura tmux panes → detecta pantalla congelada
- Si alguien está **trabado** (comando visible + output congelado + sin LLM) → notifica watcher
- Si alguien está **idle** (sin actividad por mucho tiempo) → avisa watcher para re-enganchar

Flags:
```
--watch 1,2           # ventanas a monitorear
--watcher 3           # ventana del watcher
--names "1:w1,2:w2"   # mapeo ventana:nombre
--interval 15         # segundos entre chequeos
--stuck-after 25      # segundos para detectar stuck
--idle-after 180      # segundos para detectar idle (0=desactivado)
```

### 3. start-company.sh
Comando único que levanta el equipo completo:
```bash
./start-company.sh [NUM_WORKERS]
```
- Crea N ventanas tmux con opencode + proxy
- Ventana N+1 para watcher
- Asigna `X_AID` por ventana (identificación en proxy)
- Arranca pulse automáticamente

### 4. Graph Relationships (`graph/core.py`)
Los agentes registran sus interacciones:
```python
g.register_agent("worker-1", {"type": "worker"})
g.add_relationship("watcher", "helped", "worker-1",
    {"note": "envié Escape por comando colgado"})
g.relationship_summary("worker-1")
# → {trust_score: 0.8, total_interactions: 15, ...}
```

## Configuración Necesaria

### providers.json
```json
{
  "proxy": {
    "type": "openaicompatible",
    "api_key": "",
    "base_url": "http://localhost:9098/v1",
    "headers": {"X-Agent-ID": "{env:X_AID}"},
    "models": ["deepseek-v4-flash"]
  }
}
```

### opencode.json (en ~/.config/opencode/)
El provider "proxy" debe configurarse con el header `X-Agent-ID` para
que el proxy distinga entre agentes.

## Modo de Uso

```bash
# 1. Arrancar proxy (si no está)
python3 /path/to/s84/proxy/proxy_watchdog.py &

# 2. Levantar compañía
cd s85-agent-graph
./start-company.sh 3   # 3 workers + 1 watcher

# 3. Dar instrucciones a los workers
tmux send-keys -t 1 "Tu proyecto: ..." Enter
tmux send-keys -t 2 "Tu proyecto: ..." Enter

# 4. Ver estado
curl -s http://localhost:9098/health
tail -f /tmp/company-pulse.log
```

## Lecciones Aprendidas

### Limitaciones Fundamentales
- **openCode es reactivo**: necesita un mensaje para actuar. No tiene iniciativa interna.
- **No ejecuta comandos espontáneamente**: responde con texto pero no corre `ls` a menos que se le ordene explícitamente.
- **Los comandos no bloquean la UI**: opencode ejecuta y vuelve al prompt. El comando corre como hijo del shell, no de opencode.

### Stuck Detection
- ❌ Tmux capture-pane: demasiado dinámico (spinners, timers, cursors cambiando constantemente)
- ❌ Child processes via `ps --ppid`: los comandos no son hijos directos de opencode, van a través del shell/tmux
- ✅ Proxy: `last_s` (segundos desde último request LLM) es la señal más confiable
- ✅ Combinación: proxy dice "sin actividad" + tmux dice "output igual" = stuck

### Agent Identification
- ❌ Por User-Agent: todos los opencode usan el mismo
- ❌ Por PID: TCP no transporta el PID del proceso que envía el request
- ✅ X-Agent-ID header: opencode soporta `headers: {"X-Agent-ID": "{env:X_AID}"}` en providers
- ✅ Asignar `X_AID` por ventana en start-company.sh

### Patrones que Funcionan
- **Pulso social**: un daemon externo que observa y notifica, no el agente mismo
- **Watcher como colega**: no da órdenes, sugiere y pregunta
- **Idle detection**: separado de stuck detection (thresholds distintos)
- **Cooldown**: no notificar más de una vez cada N segundos sobre el mismo agente

### Peligros
- Los workers pueden ejecutar procesos pesados (ffmpeg, ML pipelines, etc.)
- `git clean -fd` borra archivos no trackeados de TODOS los proyectos
- El pulse puede saturar al watcher si no tiene cooldown
- Los mensajes imperativos matan la autonomía del agente

## Proximos Pasos (Ideas)
- Auto-corrección: watcher no solo detecta stuck, sino que envía Escape automático
- Coordinación entre workers: que puedan pedirse ayuda mutuamente via el grafo
- Perfil de agente: el grafo guarda historial de intervenciones y confianza
- Límite de recursos: watcher mata procesos que consumen mucha CPU/RAM
- Persistencia: al reiniciar, los agentes retoman su proyecto desde el grafo
