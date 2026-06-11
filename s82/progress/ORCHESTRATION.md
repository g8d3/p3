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
