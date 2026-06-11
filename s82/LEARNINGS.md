# LEARNINGS.md — Multi-Agent System Objectives & Findings

*Live document. Updated as the system evolves.*

## Current Objectives

### 1. All agents must work, not just the supervisor
The supervisor, helperd, proxy, and dashboard are active — but worker-1 and worker-2 sit idle. This is wasted capacity. **The supervisor must assign tasks to idle workers automatically.**

### 2. Cycles must be fast
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
