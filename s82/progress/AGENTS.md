# AGENTS.md — Qué hace cada agente

_Actualizado en tiempo real. Última actualización: 2026-06-11 09:45_

## Supervisor (daemon)
- **Ciclo**: cada 5s
- **Labor**: monitorear sistema, detectar idle/stuck, asignar tareas, coordinar ayuda
- **Estado actual**: ✅ corriendo, ciclos normales
- **Log**: `tail -f /home/vuos/code/p3/s82/data/supervisor-out.log`

## Helperd (daemon)
- **Ciclo**: cada 5s
- **Labor**: reflejo cooperativo — detecta peers stuck y pide ayuda
- **Estado actual**: ✅ corriendo
- **Log**: `tail -f /home/vuos/code/p3/s82/data/helperd-out.log`

## Worker-1 (tmux window)
- **Última tarea**: por asignar — explorar proyectos de trading HyperLiquid
- **Estado**: esperando instrucciones
- **Provider**: Proxy (trackeable por proxy_watchdog)
- **Ver**: `tmux capture-pane -t worker-1 -p`

## Worker-2 (tmux window)
- **Última tarea**: por asignar — investigar métodos de screen recording
- **Estado**: esperando instrucciones
- **Provider**: Proxy (trackeable por proxy_watchdog)
- **Ver**: `tmux capture-pane -t worker-2 -p`

## Busd (daemon)
- **Labor**: message bus, entrega mensajes entre agentes via inotify + tmux
- **Estado**: ✅ 1 instancia, watching 10 inboxes
- **Log**: `/tmp/agent-bus/history/busd.log`

## Proxy (daemon)
- **Labor**: intercepta llamadas LLM, detecta agentes idle, web UI en :9099
- **Estado**: ✅ upstream OK
- **Health**: `curl -s http://localhost:9098/health`
