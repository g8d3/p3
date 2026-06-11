# Multi-Agent Cooperative System (s82)

> Central hub for the agent team. Wires together proxy, graph DB, helperd (cooperative reflex), and mobile dashboard.

## Architecture

```
                   ┌──────────────────┐
                   │   proxy_watchdog  │  ← intercepts LLM calls, detects idle
                   │   (s84, :9098)   │
                   └────────┬─────────┘
                            │ health endpoint
                   ┌────────▼─────────┐
                   │     helperd       │  ← cooperative reflex daemon
                   │   (core/helperd)  │  detects stuck peers → asks for help
                   └──┬──────────┬────┘
                      │          │
              ┌───────▼──┐  ┌───▼────────┐
              │  busd     │  │  graph DB  │
              │ (inotify) │  │ (SQLite)   │
              └───────┬──┘  └────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
     worker-1      worker-2     watcher
     (tmux w1)     (tmux w2)   (tmux w3)
```

## How to use

```bash
# Start everything
./start.sh

# Stop
kill $(cat data/helperd.pid) $(cat data/dashboard.pid)

# Dashboard
open http://localhost:9093
```

## Cooperative Reflex (helperd)

The helperd runs in the background and:

1. **Detects** when an agent is stuck (>25s no LLM activity) or idle (>120s)
2. **Selects** the nearest active peer agent
3. **Asks** the peer via bus message to check on the stuck agent
4. **Records** the help event in the graph DB
5. **Monitors** for resolution — when the stuck agent recovers, marks help as resolved

## Agent Instructions

If you're an agent (worker, watcher) and receive a message from [HELPERD]:
1. Check the mentioned agent's window: `tmux capture-pane -t <name> -p`
2. If stuck (command hanging): send Escape, suggest backgrounding with `&`
3. If idle: send a nudge or a new task
4. Report back is optional — helperd detects resolution automatically

## Connected Projects

- `s84/proxy/proxy_watchdog.py` — LLM request interceptor
- `s85-agent-graph/graph/` — Original graph implementation
- `orquestar-agentes/scripts/busd` — Message bus
- `orquestar-agentes/scripts/supervisor` — Health monitor
