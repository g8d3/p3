# IPC Bus — Especificación del Protocolo Multi-Agente

**Versión:** 0.1  
**Propósito:** Permitir que N agentes en cualquier lenguaje se comuniquen, sean orquestados, y tengan visibilidad total.

---

## 1. Filosofía

- **Un archivo = un mensaje.** No hay sockets, no hay pipes nombrados, no hay RPC.
- **JSON sobre stdin/stdout** para procesos agente.
- **WebSocket** para la UI web.
- **Cero dependencias.** El protocolo usa solo lo que el OS ya tiene: filesystem + WebSocket.

---

## 2. Topología

```
                          ┌──────────────────────┐
                          │   Orchestrator        │
                          │   (daemon, puerto WS) │
                          │                      │
                          │  ┌────────────────┐  │
                          │  │ state.db       │  │  ← SQLite central
                          │  │ (tareas, logs, │  │
                          │  │  resultados)   │  │
                          │  └────────────────┘  │
                          └────┬──────┬─────────┘
                      WS       │      │  FS (inbox/outbox)
                ┌──────────────┘      └──────────────┐
                ▼                                     ▼
        ┌───────────────┐                    ┌───────────────┐
        │  Web App      │                    │  Agentes      │
        │  (UI, mobile) │                    │  ─────────    │
        │               │                    │  backend.py   │
        │  Dashboard    │                    │  frontend.js  │
        │  Logs         │                    │  connector.rs │
        │  Config       │                    │  worker.py    │
        │  Editor       │                    │  ...          │
        └───────────────┘                    └───────────────┘
```

---

## 3. El Contrato: Mensajes

### 3.1 Formato universal

Todo mensaje es un archivo JSON con esta estructura:

```json
{
  "id": "msg_abc123",
  "type": "task | result | log | error | ping | config",
  "agent": "backend-1",
  "timestamp": "2026-05-29T10:00:00Z",
  "payload": { }
}
```

### 3.2 Tipos de mensaje

| type | emitter | descripción |
|------|---------|-------------|
| `task` | Orchestrator → Agente | Asigna trabajo |
| `result` | Agente → Orchestrator | Entrega resultado |
| `log` | Cualquiera | Registro estructurado |
| `error` | Cualquiera | Error con stack trace |
| `ping` | Cualquiera | Heartbeat / health check |
| `config` | Orchestrator → Agente | Actualización de config en caliente |

### 3.3 Task (Orchestrator → Agente)

```json
{
  "id": "task_001",
  "type": "task",
  "agent": "backend-1",
  "timestamp": "2026-05-29T10:00:00Z",
  "payload": {
    "action": "generate_script",
    "params": {
      "trends": "...",
      "voice": "es-MX-DaliaNeural"
    },
    "depends_on": ["task_000"],
    "timeout_s": 120,
    "retry": 2,
    "fallback": {
      "action": "generate_script_simple",
      "params": { "topic": "default" }
    }
  }
}
```

### 3.4 Result (Agente → Orchestrator)

```json
{
  "id": "task_001",
  "type": "result",
  "agent": "backend-1",
  "timestamp": "2026-05-29T10:00:05Z",
  "payload": {
    "status": "ok | error | fallback_used",
    "output": { "script": "..." },
    "fallback_used": null,
    "duration_ms": 4500,
    "tokens_used": 350
  }
}
```

### 3.5 Log (cualquiera)

```json
{
  "id": "log_045",
  "type": "log",
  "agent": "backend-1",
  "timestamp": "2026-05-29T10:00:03Z",
  "payload": {
    "level": "info | warn | error | debug",
    "message": "Generating script from trends...",
    "data": { "trends_count": 12 }
  }
}
```

---

## 4. Canales de Comunicación

### 4.1 Inbox/Outbox (Filesystem)

```
agents/
├── inbox/                    ← Orchestrator escribe aquí
│   ├── backend-1/
│   │   ├── task_001.json     ← tarea para backend-1
│   │   └── task_002.json
│   ├── frontend-2/
│   └── connector-1/
├── outbox/                   ← Agentes escriben aquí
│   ├── backend-1/
│   │   ├── task_001.json     ← resultado de backend-1
│   │   └── log_045.json      ← logs del agente
│   ├── frontend-2/
│   └── connector-1/
└── shared/                   ← datos compartidos (lectura cualquiera)
    ├── config.json
    └── state.json
```

**Flujo:**
1. Orchestrator escribe `inbox/backend-1/task_001.json`
2. backend-1 detecta el archivo (inotify, polling, o loop)
3. backend-1 lee, ejecuta, escribe `outbox/backend-1/result_001.json`
4. backend-1 elimina `inbox/backend-1/task_001.json` (ack)
5. Orchestrator detecta el resultado, lo registra, asigna siguiente tarea

**Reglas:**
- Un archivo = un mensaje. No append.
- El agente **siempre** responde (result, error, o log).
- Si el agente no responde en `timeout_s`, Orchestrator intenta fallback.
- Los archivos se limpian después de N ciclos (configurable).

### 4.2 stdin/stdout (Para procesos agente)

Cuando un agente corre como child process del Orchestrator:

```json
// Orchestrator escribe en stdin del proceso:
{"type": "task", "id": "t1", "payload": {"action": "fetch", "params": {...}}}

// Agente escribe en stdout (una línea JSON por mensaje):
{"type": "log", "id": "l1", "payload": {"level": "info", "message": "fetching..."}}
{"type": "result", "id": "t1", "payload": {"status": "ok", "output": {...}}}
```

**Cada línea es un mensaje JSON completo.** El agente puede emitir múltiples mensajes (logs + resultado final).

### 4.3 WebSocket (Para la UI)

El Orchestrator expone un WebSocket en `ws://host:9876/ws`. La UI web se conecta y recibe:

```json
// Eventos en tiempo real:
{"event": "task_started", "task_id": "t1", "agent": "backend-1"}
{"event": "log", "agent": "backend-1", "level": "info", "message": "..."}
{"event": "task_completed", "task_id": "t1", "status": "ok"}
{"event": "queue_update", "queue_size": 3}
{"event": "error", "agent": "connector-1", "message": "API timeout"}
```

La UI también puede enviar comandos al Orchestrator:

```json
// La UI envía:
{"command": "assign_task", "agent": "backend-1", "action": "generate_script"}
{"command": "update_config", "config": {"voice": "es-MX-JorgeNeural"}}
{"command": "stop_agent", "agent": "backend-1"}
{"command": "get_state"}
```

---

## 5. El Agente: Contrato Mínimo

Cualquier programa que quiera ser un agente en este sistema debe implementar:

```python
# Mínimo viable (Python pseudo-código)
def handle_task(task):
    """Recibe un task, ejecuta, devuelve resultado."""
    result = execute(task["action"], task["params"])
    write_outbox(task["id"], {"status": "ok", "output": result})
    delete_inbox(task["id"])

# Pero antes de eso, debe:
# 1. Suscribirse a su inbox
while True:
    task = read_inbox()
    if task:
        handle_task(task)
    sleep(0.5)  # polling o inotify

# 2. Reportar logs periódicamente
emit_log("info", "Agent started", {"pid": os.getpid()})

# 3. Responder a pings (health check)
emit_result(ping_id, {"status": "alive", "memory_mb": get_rss()})
```

---

## 6. El Orchestrator: Responsabilidades

| Responsabilidad | Mecanismo |
|----------------|-----------|
| Asignar tareas | Escribe en inbox/ del agente |
| Recibir resultados | Lee de outbox/ del agente |
| Timeouts | Timer por tarea, ejecuta fallback si expira |
| Cadenas de fallback | Si `status: error`, intenta `task.fallback` |
| Prioridades | Cola FIFO con priorización explícita |
| Health checks | Ping periódico, reinicia agente si no responde |
| Logs centralizados | Recibe de todos, almacena en state.db |
| Estado persistente | SQLite: tareas, resultados, logs, config |
| WebSocket push | Envía eventos a la UI en tiempo real |

---

## 7. Cadenas de Fallback (Resiliencia)

Cada tarea puede definir una cadena de fallback:

```json
{
  "action": "tts_edge",
  "params": {"text": "..."},
  "timeout_s": 30,
  "retry": 1,
  "fallback": {
    "action": "tts_local_piper",
    "params": {"text": "..."},
    "fallback": {
      "action": "tts_espeak",
      "params": {"text": "..."}
    }
  }
}
```

Orchestrator intenta tts_edge → timeout → fallback tts_local_piper → error → fallback tts_espeak.

**Lección de s71:** Nunca un solo punto de falla. Siempre Plan B, C, D.

---

## 8. Auto-Modificación

El agente puede recibir un task de tipo `self_modify`:

```json
{
  "action": "self_modify",
  "params": {
    "file": "agents/backend-1/code.py",
    "change": "replace",
    "old": "timeout_s = 30",
    "new": "timeout_s = 60"
  }
}
```

O más potente: el Orchestrator (o la UI) envía código nuevo:

```json
{
  "action": "self_modify",
  "params": {
    "instruction": "Add retry logic with exponential backoff to the fetch function"
  }
}
```

El agente ejecuta la instrucción (usando un LLM interno o un script de transformación), modifica su propio código, y se recarga.

**Esto cierra el círculo:** la app se modifica a sí misma basada en instrucciones de la UI o de otros agentes.

---

## 9. Config Global

Archivo `config.yaml` en la raíz, hot-reloadeable:

```yaml
agents:
  backend-1:
    command: python3.12 backend/main.py
    max_concurrent: 3
    timeout_default_s: 120
    env:
      PROXY_URL: "http://127.0.0.1:9100"
  
  frontend-1:
    command: node frontend/server.js
    timeout_default_s: 60

orchestrator:
  port: 9876
  state_db: data/state.db
  log_retention_days: 7
  max_queue_size: 100

ipc:
  inbox_dir: agents/inbox
  outbox_dir: agents/outbox
  shared_dir: agents/shared
  poll_interval_ms: 500
  cleanup_after_hours: 24
```

---

## 10. Seguridad (API Keys)

- Las API keys se almacenan **solo en el servidor** (SQLite cifrado con `cryptography.fernet`)
- El WebSocket no expone keys — los agentes las piden vía task interno
- El frontend web muestra campos masked (`sk-...XXXX`)
- `POST /api/config` para actualizar keys (cifrado automático)

---

## 11. Resumen del Ciclo Completo

```
1. UI web: "Genera un video sobre IA"
2. Orchestrator recibe vía WS
3. Orchestrator escribe task en inbox/backend-1/
4. backend-1 detecta, ejecuta, escribe logs en outbox/
5. Orchestrator reenvía logs a la UI vía WS (en vivo)
6. backend-1 termina, escribe result en outbox/
7. Orchestrator registra en state.db
8. Orchestrator asigna siguiente tarea (frontend, etc.)
9. UI web ve el progreso en tiempo real
10. Si backend-1 falla → Orchestrator ejecuta fallback
```

---

*Documento generado el 29 de mayo de 2026. Síntesis de s63, s65, s71, s72.*
