# ORCHESTRATION.md — Progreso del Sistema Multi-Agente

> **Responsable**: supervisor + helperd
> **Estado**: ✅ Base funcionando, en mejora continua

## Arquitectura Actual

```
proxy_watchdog (s84) → detecta actividad LLM de agentes
       ↓
  supervisor (c/5s) → monitorea, asigna tareas, coordina
       ↓
  helperd (c/5s) → reflejo cooperativo (stuck → peer help)
       ↓
  busd (inotify) → entrega mensajes entre agentes
       ↓
  workers (opencode + proxy) → ejecutan tareas
```

## Logros

- [x] Proxy intercepta llamadas LLM y detecta idle/stuck
- [x] Supervisor cicla cada 5s con reglas determinísticas
- [x] Helperd detecta peers stuck y pide ayuda
- [x] busd entrega mensajes correctamente via tmux send-keys
- [x] Workers reciben y procesan tareas autónomamente
- [x] Dashboard muestra estado del equipo en :9093
- [x] Sistema sobrevive crashes (autoheal revive componentes)

## En Progreso

- [ ] Asignación inteligente de tareas por especialidad
- [ ] Workers documentan su progreso en /progress/
- [ ] Ciclo completo de calidad (maker → checker)

## Pendiente

- [ ] Persistencia de estado entre reinicios del sistema
- [ ] Worker-1 produce estrategia de trading HyperLiquid
- [ ] Worker-2 produce pipeline de screen recording
- [ ] Auto-mejora: supervisor aprende de ciclos pasados

## Análisis Crítico del Sistema

### ✅ Lo que funciona
- **Proxy watchdog**: detecta actividad LLM, asigna agent IDs por tmux window name, health endpoint funcional. Base sólida.
- **Supervisor**: ciclo 5s, asigna tareas a workers idle, reinicia componentes caídos. Reglas determinísticas eficientes.
- **busd**: entrega mensajes entre agentes via inotify + tmux send-keys. Simple y robusto.
- **Screen recording pipeline**: ffmpeg x11grab + PulseAudio captura pantalla real. Narración TTS con edge-tts.
- **Trading signals**: 4 assets (ETH/BTC/SOL/HYPE), RSI+MACD+funding+OB, IC tracking, walk-forward analysis.

### ❌ Lo que no funciona
- **Helperd false positives**: `STUCK_AFTER=25s` causa ~50 alertas/hora por workers idle en prompt. El fix (subir threshold + detectar prompt) está en código pero helperd nunca se reinicia porque `kill` timeoutea.
- **Sin task queue persistente**: supervisor rotas 5 tareas hardcodeadas. Si worker pierde mensaje, la tarea se pierde.
- **Sin feedback loop**: workers reciben tareas pero nunca reportan resultados al supervisor. No hay trazabilidad.
- **Synthetic agents**: proxy detecta `agent-9`, `supervisor-test` como agentes reales via /proc. Helperd los filtra pero siguen apareciendo en dashboard.
- **Videos negros**: las primeras grabaciones salieron negras por falta de ventanas en `:0`. Fixed con xterm auto-setup.
- **Git kills timeout**: `kill $(pgrep -f helperd)` timeoutea consistentemente, impidiendo restart del daemon.

### 🔧 Lo que mejoraría mañana
1. **Helperd**: hacer que el kill/restart funcione (usar `pkill -f` o archivo PID), o que el helperd detecte cambios en config.py y se reconfigure solo.
2. **Task queue**: reemplazar las 5 tareas hardcodeadas con cola SQLite persistente. Workers hacen pull en lugar de push.
3. **Feedback**: worker escribe resultado a `data/task-results/` al completar tarea. Supervisor lo lee y registra en graph DB.
4. **Discovery de proyectos p3/**: supervisor indexa `p3/` y asigna tareas contextuales (ej. "explora s86-dex-trading-pipeline").
5. **Auto-restart helperd**: si helperd crashea, supervisor lo revive en <5s. Ya está implementado pero no probado.
6. **Dashboard de señales**: el JSON de market_analysis.json no tiene endpoint HTTP. Agregar ruta `/api/signals` al dashboard :9093.

## Cómo ver el progreso en el navegador

Todo el progreso está disponible en el file server (puerto 9090):

| Archivo | URL |
|---------|-----|
| Progreso general | http://localhost:9090/p3/s82/progress/ |
| TRADING.md | http://localhost:9090/p3/s82/progress/TRADING.md |
| CONTENT.md | http://localhost:9090/p3/s82/progress/CONTENT.md |
| AGENTS.md | http://localhost:9090/p3/s82/progress/AGENTS.md |
| ORCHESTRATION.md | http://localhost:9090/p3/s82/progress/ORCHESTRATION.md |
| README.md | http://localhost:9090/p3/s82/progress/README.md |
| Dashboard | http://localhost:9093 |
| LEARNINGS.md | http://localhost:9090/p3/s82/LEARNINGS.md |
| SKILL.md | http://localhost:9090/p3/s82/SKILL.md |
| Código fuente | http://localhost:9090/p3/s82/core/ |

## Sistema actual (componentes)

| Componente | Puerto | Archivo | URL código |
|-----------|--------|---------|------------|
| proxy_watchdog | :9098 | s84/proxy/proxy_watchdog.py | http://localhost:9090/p3/s84/proxy/proxy_watchdog.py |
| helperd | daemon | core/helperd.py | http://localhost:9090/p3/s82/core/helperd.py |
| dashboard | :9093 | web/server.py | http://localhost:9090/p3/s82/web/server.py |
| supervisor | daemon | core/supervisor.py | http://localhost:9090/p3/s82/core/supervisor.py |
| sequencer | daemon | core/sequencer.py | http://localhost:9090/p3/s82/core/sequencer.py |
| busd | daemon | ~/.agents/skills/orquestar-agentes/scripts/busd | |
