# Framework Multi-Agente

Framework para construir aplicaciones donde múltiples agentes (humanos + IA en cualquier lenguaje) colaboran con visibilidad total, configuración externa, y ciclos cortos.

## Filosofía

Ver `MANIFIESTO.md` para los 7 pilares. En una línea:

> **Visibilidad total + Configuración sobre código + API ultra-simple + IPC universal + Ciclo corto + Resiliencia por capas + Commits trazables**

## Estructura

```
s73-framework/
├── MANIFIESTO.md              ← Los 7 pilares (léeme primero)
├── config.yaml                ← Config global (hot-reload)
├── setup.py                   ← Inicializa estructura
├── run_orchestrator.py        ← Entry point del daemon
├── orchestrator/
│   └── __init__.py            ← Daemon central (WS + IPC + SQLite)
├── agent-template/
│   └── agent.py               ← Template mínimo para crear agentes
├── web-ui/
│   └── index.html             ← Dashboard web (conecta vía WS)
├── specs/
│   └── ipc-bus.md             ← Especificación del protocolo IPC
├── tests/
│   └── test_ipc_bus.py        ← Test del ciclo IPC completo
├── requirements.txt
├── inbox/                     ← Tareas para agentes (auto-creado)
├── outbox/                    ← Resultados de agentes (auto-creado)
├── shared/                    ← Datos compartidos (auto-creado)
├── data/                      ← Estado SQLite (auto-creado)
└── logs/                      ← Logs (auto-creado)
```

## Quick Start

```bash
# 1. Inicializar
python3.12 setup.py

# 2. Iniciar Orchestrator (daemon)
python3.12 run_orchestrator.py &

# 3. Abrir dashboard
#    http://localhost:9877

# 4. Enviar tarea de prueba
mkdir -p inbox/echo-agent
echo '{
  "id": "test_001", "type": "task", "agent": "echo-agent",
  "timestamp": "2026-01-01T00:00:00Z",
  "payload": {"action": "ping", "params": {"msg":"hola"}, "timeout_s": 10}
}' > inbox/echo-agent/test_001.json
```

## Cómo crear un agente

```python
from agent_template.agent import Agent

class MiAgente(Agent):
    def execute(self, action: str, params: dict) -> dict:
        # Tu lógica aquí
        return {"resultado": "ok"}

if __name__ == "__main__":
    agent = MiAgente(name="mi-agente")
    agent.run()
```

Luego agregarlo a `config.yaml`:
```yaml
agents:
  mi-agente:
    command: "python3.12 path/to/mi_agente.py"
    env:
      AGENT_NAME: "mi-agente"
```

## Protocolo

Cualquier proceso puede ser agente si:
1. Lee archivos JSON de `inbox/<nombre>/`
2. Escribe resultados en `outbox/<nombre>/`
3. Emite logs como JSON por stdout (una línea por mensaje)

Formato: `specs/ipc-bus.md`

## Tests

```bash
python3.12 tests/test_ipc_bus.py
```

## Origen

Este framework sintetiza lecciones de 10+ proyectos en `p3/` (s63-s72):
- **s63-agent-hub**: WebSocket nativo, IPC por stdout, singleton pattern
- **s64-api-benchmarks**: Timeouts, fallbacks, User-Agent, modelos razonadores
- **s65**: Sandbox multi-lenguaje, procesos independientes
- **s71-VoiceButtonApp**: Visibilidad total, config sobre código, cadenas de fallback
- **s72-ai-video-studio**: Feed engine, CDP testing, watchdog, test harness
