# LEARNINGS.md — Multi-Agent System Objectives & Findings

*Live document. Updated as the system evolves.*

## Índice de procesos creados (y por qué se eliminaron)

| Proceso | Archivo | Qué hacía | Problema | Estado |
|---------|---------|-----------|----------|--------|
| **proxy_watchdog** | `s84/proxy/proxy_watchdog.py` | Intercepta llamadas LLM, detecta agentes por /proc, sirve health endpoint | Útil como herramienta de visibilidad | ✅ Conservado |
| **helperd** | `core/helperd.py` | Detectaba agents stuck y pedía ayuda a un peer vía busd | Spam sin verificar, sin OODA, asumía que sus acciones funcionaban | ❌ Rediseñar |
| **supervisor** | `core/supervisor.py` | Ciclo cada 5s, monitoreaba salud, reiniciaba componentes caídos | Duplicaba función del helperd, sin LLM para razonar | ❌ Rediseñar |
| **sequencer** | `core/sequencer.py` | Asignaba tareas infinitas a workers cada 20s | Se quedó sin tareas específicas y empezó a dar tareas genéricas mezclando roles | ❌ Eliminado |
| **reviewer_agent** | `core/reviewer_agent.py` | Revisaba calidad de videos y trading con Mimo v2.5 | Separado innecesariamente, yo puedo revisar | ❌ Eliminado |
| **runner** | `artifacts/trading/runner.py` | Generaba señales de trading cada 5min, escribía a CSV y JSON | Útil pero debería ser parte de worker-1 | ❌ Delegado a worker-1 |
| **guardian** | `core/guardian.py` | Unificaba todo en un solo proceso con LLM cada 30s | Acababa de crearlo cuando el usuario señaló que YO soy ese agente pensante | ❌ Eliminado |
| **autoheal** | `scripts/autoheal.sh` | Revivía componentes caídos cada 30s | Causó procesos zombis que se re-parentaban a init, difíciles de matar | ❌ Eliminado |
| **busd** | `orquestar-agentes/scripts/busd` | Message bus via inotify, entregaba mensajes entre agentes | Spam, mensajes se acumulaban sin entregar, múltiples instancias | ❌ Reemplazar |
| **dashboard** | `web/server.py` | Web UI con tabs, tablas, señales, goal tree | Útil para visualización | ✅ Conservado |
| **graph** | `core/graph.py` | SQLite DB para tracking de relaciones entre agentes | Infraestructura útil | ✅ Conservado |

### Lección: Un solo proceso con IA > múltiples procesos deterministas

La arquitectura inicial tenía múltiples procesos independientes porque asumí que necesitaba componentes especializados (uno para salud, otro para stuck, otro para tareas). Pero esto creó:

1. **Coordinación entre procesos**: Tenían que comunicarse entre sí (vía busd o archivos)
2. **Duplicación de lógica**: helperd y supervisor hacían cosas similares
3. **Detección falsa de stuck**: agentes sintéticos (agent-9, supervisor-test) generaban spam infinito
4. **Sin verificación**: Los procesos asumían que sus acciones funcionaban sin comprobar
5. **Procesos zombis**: autoheal dejaba hijos huérfanos que seguían corriendo

La solución correcta: **un solo proceso que use un LLM para razonar** (OODA: Observar, Orientar, Decidir, Actuar, Verificar) en vez de múltiples scripts deterministas que no pueden adaptarse.

Y el agente pensante ideal para ese proceso es el propio coordinador (opencode), no un script Python autónomo.

## Arquitectura Final

```
Yo (opencode) ─── coordino, pienso, decido, verifico
  ├── worker-1 (trading): ejecuta tareas de trading
  ├── worker-2 (contenido): ejecuta tareas de contenido
  └── herramientas: proxy_watchdog, dashboard, graph, helperd (bajo demanda)
```

No más procesos autónomos. Yo soy el cerebro. Las herramientas existen para servirme, no para reemplazarme.

## Lecciones Clave

### 1. No mezclar roles
El sequencer empezó dando tareas de trading a worker-1 y contenido a worker-2, pero cuando se quedó sin tareas predefinidas, empezó a dar tareas genéricas mezclando los roles. Worker-2 terminó haciendo trading.

### 2. No asumir que una acción funcionó (OODA)
El helperd enviaba "ayuda" pero nunca verificaba si el agente se recuperó. Repetía la misma acción sin escalar ni cambiar de estrategia.

### 3. Los procesos zombis son difíciles de matar
El autoheal creaba procesos hijos que, al matar al padre, se re-parentaban a init. pkill -f es peligroso porque puede matar el shell actual.

### 4. Un solo agente con LLM > múltiples scripts deterministas
Un LLM puede observar, razonar, decidir y verificar. Los scripts solo ejecutan lógica fija. La flexibilidad del LLM es más valiosa que la velocidad del script.

### 5. El coordinador debe estar fuera del sistema
No incluir al coordinador (opencode) en el monitoreo automático hasta que el sistema esté probado.
- Supervisor: **5s** (fast enough to detect and react)
- Helperd: **5s** (cooperative reflex needs to be responsive)
- Autoheal: **15s** (lifecycle management, doesn't need to be as fast)

### 3. LLM calls must be efficient
Calling the LLM every 5s burns tokens. The supervisor should:
- Use **deterministic rules** for common cases (idle → assign task, stuck → ask peer)
- Only call the LLM for **novel situations** (new agent appears, component crashes)

### 4. The cooperative reflex must be bidirectional
When A is stuck → helperd asks B to help → A recovers → B might get stuck → helperd asks A to help. This is now working.

## Findings

### 2026-06-11: LLM returns empty content with reasoning
The upstream API returns the reasoning in `reasoning_content` and leaves `content` empty when `max_tokens` is too low. The fix: increase `max_tokens` to 512+ and handle `reasoning_content` as fallback.

### 2026-06-11: Proxy detection of agents
The proxy_watchdog scans `/proc` for opencode, crush, python processes. It detects them by command name, then reads `TMUX_PANE` from environ to get the window name. Agents that have never made an LLM call show as `never_active=True`.

### 2026-06-11: Env vars don't cross tmux boundaries
`tmux new-window` doesn't inherit shell env vars. Must pass them explicitly in the command string. Even better: use `source ~/.secrets/.env` or encode in the command.

### 2026-06-11: Autoheal shouldn't kill components on exit
The cleanup trap in autoheal.sh was killing ALL components on SIGTERM. Fixed: autoheal only starts/monitors, never stops components.

### 2026-06-11: nohup can't run shell builtins
`nohup cd /path && command` fails because `cd` is a shell builtin, not a standalone binary. Fix: use absolute paths or wrap in `bash -c`.

## External Objectives (from user)

The system needs **real work to produce**, not just self-maintenance:

### 1. Trading Strategies on HyperLiquid
Build, backtest, and deploy trading strategies on HyperLiquid and other DEX perpetuals.
- Related projects: s39-trading-bot, s40-trading-backtester, s41-dex-volume-fetcher, s43-crypto-strategy-lab, s1-funding-rate-scraper
- Workers should research these projects and propose integrations

### 2. Content Creation via Screen Recording
Create content by **recording the screen** (not CPU rendering - too slow).
- Topics: agent orchestration, trading, content creation itself
- Method: ffmpeg screen capture + audio overlay, not CPU-based rendering
- Related: s25-tutorial-video-recorder, s26-video-generator, s52-cinematic-coding-video-generator

### 3. Self-Building vs External Goals
The system needs BOTH:
- Self-maintenance (keep all agents working, fix what's broken)
- External production (trading strategies, content, code)
- **Synthesis**: idle workers don't just get "check the log" tasks — they should work on real project goals

## Current State (2026-06-11 09:42)

**Sistema funcionando end-to-end.** Todos los componentes activos:

| Componente | Estado | Puerto/PID |
|-----------|--------|------------|
| proxy_watchdog | ✅ | :9098 |
| helperd | ✅ | daemon |
| dashboard | ✅ | :9093 |
| supervisor | ✅ | ciclo 5s |
| busd | ✅ | inotify |
| worker-1 | ✅ | activo (proxy model) |
| worker-2 | ✅ | activo (proxy model) |

### Ciclo completo de cooperación
1. Supervisor detecta agente stuck (>25s sin LLM) o idle (>120s)
2. Escribe mensaje en el inbox del peer via busd
3. busd entrega el mensaje al peer via `tmux send-keys`
4. El peer recibe y puede tomar acción
5. Todo se registra en el graph DB

## Key Fixes & Discoveries

### 2026-06-11: inotify max_user_instances agotado
El supervisor spawnaba busd cada 5s sin control, agotando las 128 instancias de inotify. Fix: `sudo sysctl -w fs.inotify.max_user_instances=1024` y `ensure_busd()` con flag `_busd_started` para spawn único.

### 2026-06-11: busd no corría = mensajes no entregados
Los mensajes se escribían en inboxes pero nunca llegaban a los workers porque busd estaba muerto. Fix: supervisor ahora arranca busd una vez y verifica que esté vivo.

### 2026-06-11: No spamear workers cada ciclo
El supervisor asignaba una tarea nueva cada 5s a workers idle, inundando su inbox. Fix: `pending_messages()` check antes de asignar.

### 2026-06-11: Workers no detectados por proxy
Si un worker usa el provider "Build" (no "Proxy"), el proxy no ve sus llamadas LLM y no puede trackear su actividad. Fix: ambos workers ahora usan "Proxy" model.

### 2026-06-11: Supervisor no loggeaba ciclos
El supervisor sí corre cada 5s, pero solo registra en el graph DB (no en stdout). Para ver ciclos: `tail -f /home/vuos/code/p3/s82/data/supervisor.log` (log file) o consultar graph DB.

### 2026-06-11: Múltiples supervisores compitiendo
start.sh + autoheal + tests manuales spawnaban supervisores duplicados. Fix: autoheal ahora maneja el supervisor como background process (no tmux window), y ensure_busd tiene protección PID.

## Questions to Explore

- Should there be a task queue that workers pull from when idle?
- Should workers specialize (one does code, one does analysis, one does trading)?
- How do workers discover related projects (e.g., all HyperLiquid projects in p3)?
- Should we add a "curiosity" mode where idle agents explore the codebase?
