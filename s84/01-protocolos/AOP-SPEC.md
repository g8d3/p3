# Agent Orchestration Protocol (AOP) — Specification v0.1

> **Status**: Living Specification — synthesized from existing implementations in
> `orquestar-agentes`, `AAN`, `j`, and `HANDOFF.md` patterns.
>
> **Problem**: Existing protocols (MCP, A2A, ACP) handle tool access, editor↔agent,
> and agent↔agent delegation, but **none of them standardize quality-supervised
> orchestration**: creating sessions, monitoring work quality, redirecting
> underperforming agents, canceling work, and auditing the full lifecycle.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Agent Roles](#2-agent-roles)
3. [Transport Layer](#3-transport-layer)
4. [Message Format](#4-message-format)
5. [Task Lifecycle](#5-task-lifecycle)
6. [Quality Gates](#6-quality-gates)
7. [Session Model](#7-session-model)
8. [Trace Model](#8-trace-model)
9. [Agent States](#9-agent-states)
10. [Liveness & Health](#10-liveness--health)
11. [Protocol Operations](#11-protocol-operations)
12. [Security Model](#12-security-model)
13. [Bridge to Existing Protocols](#13-bridge-to-existing-protocols)
14. [Implementation Status](#14-implementation-status)

---

## 1. Architecture Overview

AOP defines a **supervised mesh** of agents coordinated by an orchestrator with
explicit quality gates between each work step.

```
┌──────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                          │
│  (cicla, monitorea, decide rutas, mantiene sesiones)         │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│ MAKER  │ │CHECKER │ │ VIDEO  │ │ EXPLOR │ │ CUSTOM...   │
│(código)│ │(calidad)│ │MAKER   │ │(pruebas)│ │             │
└────────┘ └────────┘ └────────┘ └────────┘ └─────────────┘
     │           │
     └───quality gate───┘
         maker → checker → aprobado/rechazado
```

### 1.1 Core Invariant

**All work MUST pass a quality gate before being considered complete.** No agent
can mark its own work as final. Every output requires a second agent (or human)
to validate it against explicit criteria.

### 1.2 Capas (layers)

| Capa | Responsabilidad | Implementación actual |
|------|----------------|----------------------|
| **L0 — Transport** | Entrega de mensajes entre agentes | `busd` (inotify + archivos) |
| **L1 — Agent Roles** | Identidad, capacidades, permisos | Roles en `orquestar`, skills |
| **L2 — Task Lifecycle** | Crear, asignar, monitorear, cancelar tareas | `task-runner`, `orquestar.py` (AAN) |
| **L3 — Quality Gate** | Validar output, aprobar/rechazar, redirigir | `checker` skill, ciclo maker→checker |
| **L4 — Session** | Contexto compartido entre tareas | HANDOFF.md, `context.db` (`j`) |
| **L5 — Trace** | Auditoría completa: quién hizo qué, cuándo, por qué | `trace-helper`, `version_registry` |
| **L6 — Supervision** | Health checks, crash recovery, stuck detection | `supervisor` |
| **L7 — Autonomous Cycle** | Escaneo proactivo, asignación automática, loop | `ciclador` |

---

## 2. Agent Roles

Every agent in an AOP mesh has a **role** that defines what work it can accept
and what quality criteria it must meet.

### 2.1 Standard Roles

| Role | ID | Accepts | Produces | Validated by |
|------|----|---------|----------|-------------|
| **Maker** | `maker` | Tasks (code, config, features) | Code changes, files | Checker |
| **Checker** | `checker` | Review requests | Approve/Reject verdict | — (autonomous) |
| **Video Maker** | `video-maker` | Video generation tasks | MP4 clips, streams | Checker |
| **Explorer** | `explorer` | Test/explore commands | Bug reports, UX issues | — (puede auto-validar) |
| **Orchestrator** | `orchestrator` | N/A (coordina) | Assignments, traces | — (punto central) |

### 2.2 Role Descriptor

Each agent publishes its capabilities in a **Role Card** (inspired by A2A Agent Cards):

```json
{
  "role": "maker",
  "version": "0.1",
  "skills": ["code", "config", "bash"],
  "accepts": ["task", "fix", "feature"],
  "quality_gates": ["checker"],
  "transports": ["bus", "http", "stdio"],
  "max_concurrent_tasks": 1
}
```

### 2.3 Role Discovery

Agents discover each other through:
- **Static config**: `orquestar N` defines a1=maker, a2=checker, a3=video-maker
- **Registry**: `aan_config.json` or `agent-states.json` lists active agents
- **Broadcast**: New agents can announce via bus (future)

---

## 3. Transport Layer

AOP is **transport-agnostic**. The spec defines a minimal message envelope that
can be carried over any transport.

### 3.1 Primary Transport: File Bus (inotify)

Current implementation via `busd`:

```
/tmp/agent-bus/
├── a1/in/          → inbox del maker (archivos = mensajes)
├── a2/in/          → inbox del checker
├── a3/in/          → inbox del video-maker
├── a1/tasks/       → tareas estructuradas (para task-runner)
├── traces/         → archivos de trace (trace-helper)
├── agent-states.json  → estado actual de cada agente
├── history/
│   ├── messages.log   → historial plano de mensajes
│   └── busd.log       → log del daemon
└── *.pid           → PIDs de daemons
```

**Entrega**: `busd` usa `inotifywait` para detectar nuevos archivos en inboxes,
extrae el contenido y lo envía al agente vía `tmux send-keys`.

### 3.2 Message Envelope (transport-agnostic)

Every message MUST have this structure:

```json
{
  "aop_version": "0.1",
  "type": "task | review | verdict | signal | trace",
  "from": "maker | checker | orchestrator | ...",
  "to": "maker | checker | ...",
  "id": "uuid-or-trace-id",
  "timestamp": 1718000000,
  "body": { "...": "..." },
  "trace_id": "trace-abc-123",
  "ttl": 300,
  "priority": "normal | high | low"
}
```

### 3.3 Supported Transports

| Transport | Latency | Persistencia | Estado actual |
|-----------|---------|-------------|---------------|
| **File bus** (inotify) | ~500ms | ✅ archivos | ✅ Producción |
| **HTTP** | ~100ms | ❌ | 🔬 Planeado |
| **SQLite compartida** | ~10ms | ✅ DB | ⚠️ Parcial (`.crush/db`) |
| **stdin/stdout** | ~1ms | ❌ | 🔬 Planeado (bridge ACP) |

---

## 4. Message Format

### 4.1 Message Types

| Type | Direction | Description | Example |
|------|-----------|-------------|---------|
| `task` | orchestrator→agent | Assign work | "Implement login form" |
| `review` | maker→checker | Request validation | "Revisa cambio X" |
| `verdict` | checker→maker | Approve or reject | "aprobado" / "rechazado: razón" |
| `signal` | any→any | Coordination signal | "task X cancelled", "agent Y blocked" |
| `trace` | any→trace-store | Audit record | {hop, status, ts, error} |
| `config` | orchestrator→agent | Reconfigure | "cambia modelo a X" |

### 4.2 Task Message Body

```json
{
  "type": "task",
  "body": {
    "title": "Implement login form",
    "description": "Add email/password login to /login route",
    "criteria": [
      "Validates email format",
      "Shows error on wrong password",
      "Redirects to /dashboard on success"
    ],
    "context": {
      "session_id": "sess-abc",
      "project": "s85-webapp",
      "files": ["src/routes/login.tsx"],
      "handoff": "HANDOFF-s84-a-s85.md"
    },
    "timeout": 300,
    "quality_gate": {
      "required": true,
      "validator": "checker",
      "auto_reject_if": [
        "missing error handling",
        "no tests",
        "hardcoded values"
      ]
    }
  }
}
```

### 4.3 Verdict Message Body

```json
{
  "type": "verdict",
  "body": {
    "decision": "approved | rejected | needs_work",
    "summary": "Validation passed. All criteria met.",
    "details": [
      "✅ Validates email format",
      "✅ Error handling present",
      "⚠️ Missing test for edge case (empty email) — optional fix"
    ],
    "trace_id": "trace-abc-123"
  }
}
```

---

## 5. Task Lifecycle

```
                    ┌──────────┐
                    │  DRAFT   │ (recién creada, sin asignar)
                    └────┬─────┘
                         │ assign
                    ┌────▼─────┐
                    │ ASSIGNED │ (tiene agente asignado)
                    └────┬─────┘
                         │ accept
                    ┌────▼─────┐
                    │ RUNNING  │ (agente trabajando)
                    └────┬─────┘
                         │ complete
                    ┌────▼─────┐     ┌──────────┐
                    │ PENDING  │────▶│ REJECTED │ (checker rechazó)
                    │ REVIEW   │     └──────────┘
                    └────┬─────┘         │
                         │ approve       │ reassign (back to RUNNING)
                    ┌────▼─────┐         │
                    │ COMPLETED│         │
                    └──────────┘         │
                         │               │
                    ┌────▼─────┐         │
                    │ CANCELLED│ (o desde cualquier estado)
                    └──────────┘
```

### 5.1 State Transitions

| From | To | Trigger | Who |
|------|----|---------|-----|
| DRAFT | ASSIGNED | `assign_task` | Orchestrator |
| ASSIGNED | RUNNING | `accept_task` | Agent |
| RUNNING | PENDING_REVIEW | `complete_task` | Agent |
| PENDING_REVIEW | COMPLETED | `approve_task` | Checker |
| PENDING_REVIEW | REJECTED | `reject_task` | Checker |
| REJECTED | RUNNING | `reassign_task` | Orchestrator |
| ANY | CANCELLED | `cancel_task` | Orchestrator / Human |
| RUNNING | BLOCKED | `agent_blocked` | Supervisor |
| BLOCKED | RUNNING | `unblock` | Orchestrator |

### 5.2 Cancellation Semantics

When a task is cancelled:
1. Orchestrator sends `signal` of type `cancel` to the agent
2. Agent MUST stop work on that task within `grace_period` (default: 5s)
3. Agent SHOULD record partial output if available
4. Orchestrator marks trace hop as `cancelled`
5. Resources SHOULD be cleaned up (kill subprocesses, release files)

### 5.3 Redirection (Reassign)

Orchestrator can redirect a task from one agent to another:
1. Original task goes to REJECTED or CANCELLED
2. New task is created with same `trace_id` but different `assigned_to`
3. Context from partial work is passed via `handoff` field
4. New agent starts from where the previous one left off

---

## 6. Quality Gates

This is AOP's key differentiator. Every task output MUST pass a quality gate.

### 6.1 Quality Gate Contract

```json
{
  "gate": {
    "validator": "checker",
    "criteria": [
      "Syntactic correctness (node --check)",
      "No TODOs/FIXMEs introduced",
      "No hardcoded values (use config)",
      "Tests pass (npm test / uv run pytest)",
      "No console.log debugging artifacts"
    ],
    "auto_fail": ["security vulnerability", "API key leak"],
    "min_approvals": 1,
    "timeout": 120
  }
}
```

### 6.2 Flow

```
Maker:  "say checker 'revisa: implementé login form en src/routes/login.tsx'"
Checker: (lee el diff, corre validaciones)
         "say maker 'aprobado: login form OK'"
      O: "say maker 'rechazado: login form — falta validación de email vacío'"
Maker:  (corrige)
         "say checker 'revisa v2: agregué validación de email vacío'"
Checker: "say maker 'aprobado: login form v2 OK'"
```

### 6.3 Redirection on Poor Quality

If an agent produces consistently low-quality work (configurable threshold,
e.g., ≥3 rejections in a row), the orchestrator SHALL:

1. Escalate to human (write to `/tmp/agent-bus/human/`)
2. Optionally reassign to a different agent
3. Record the quality issue in the trace

---

## 7. Session Model

### 7.1 Session

A **session** groups a series of related tasks and context. Represented by a
`session_id` that threads through all traces and messages.

```json
{
  "session_id": "sess-dev-20260605",
  "project": "s85-webapp",
  "created_at": "2026-06-05T10:00:00Z",
  "agents": ["maker", "checker"],
  "context": {
    "handoff_from": "s84",
    "handoff_file": "HANDOFF-s84-a-s85.md",
    "pending_items": ["HANDOFF.md", "PENDIENTE.md"]
  },
  "tasks": ["trace-abc-123", "trace-def-456"],
  "status": "active | paused | completed"
}
```

### 7.2 Context Handoff

When switching between projects or sessions, the following MUST be preserved:

| Qué | Formato | Ejemplo |
|-----|---------|---------|
| Estado del proyecto | `PENDIENTE.md` | Lista de items pendientes |
| Contexto de conversación | `HANDOFF.md` | Resumen de decisiones, arquitectura |
| Tarea activa | `TASK-A{N}.md` | Qué se estaba haciendo |
| Archivos relevantes | Lista de rutas | `src/routes/login.tsx` |

### 7.3 Context DB

```sql
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    project     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    handoff_from TEXT,
    handoff_to  TEXT
);

CREATE TABLE session_context (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    topic       TEXT NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT, -- JSON array
    created_at  TEXT NOT NULL
);

CREATE TABLE task_sessions (
    task_id     TEXT NOT NULL,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    PRIMARY KEY (task_id, session_id)
);
```

Schema ya implementado en `j` (s81) como `context.db` con tablas `handoffs`,
`context_entries`, `projects`.

---

## 8. Trace Model

Every unit of work produces an **audit trail** that records who did what, when,
and with what result.

### 8.1 Trace Structure

```json
{
  "id": "trace-ciclador-5-1749060000",
  "route": ["ciclador", "a1", "a2"],
  "hops": [
    {
      "from": "ciclador",
      "to": "a1",
      "status": "assigned",
      "ts": 1749060000,
      "error": null
    },
    {
      "from": "a1",
      "to": "a2",
      "status": "sent",
      "ts": 1749060100,
      "error": null
    },
    {
      "from": "a2",
      "to": "",
      "status": "completed",
      "ts": 1749060200,
      "error": null
    }
  ],
  "status": "completed",
  "message": "Issues: 3 TODOs...",
  "created": 1749060000,
  "updated": 1749060200
}
```

### 8.2 Trace Storage

Ya implementado en `trace-helper`:
- Archivos JSON en `/tmp/agent-bus/traces/<id>.json`
- `latest.json` symlink para acceso rápido
- `trace-helper find <needle>` para búsqueda

### 8.3 Version Registry (AAN)

La `version_registry` extiende el modelo de trazas con:

| Tabla | Propósito |
|-------|-----------|
| `versions` | Snapshots del proyecto en el tiempo |
| `agent_work` | Qué produjo cada agente en cada versión |
| `tags` | Labels planos para clasificar versiones |
| `tag_relations` | Taxonomía entre tags (broader, narrower, conflicts) |
| `version_tags` | M:N entre versiones y tags |

```sql
-- Cada versión es un snapshot completo
CREATE TABLE versions (
    id          TEXT PRIMARY KEY,        -- "v001", "v002"
    parent_id   TEXT,                    -- fork lineage
    created_by  TEXT NOT NULL,           -- "human", "builder", "validator"
    message     TEXT NOT NULL,           -- qué cambió
    status      TEXT DEFAULT 'draft',    -- draft → active → archived | rejected
    live        INTEGER DEFAULT 0        -- solo uno a la vez
);

-- Trazabilidad de qué agente hizo qué
CREATE TABLE agent_work (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id  TEXT NOT NULL REFERENCES versions(id),
    agent_type  TEXT NOT NULL,            -- "builder", "validator"
    input_spec  TEXT,                     -- qué se le pidió
    output_log  TEXT,                     -- qué produjo
    exit_status TEXT DEFAULT 'ok',        -- ok, failed, skipped
    started_at  TEXT,
    finished_at TEXT
);
```

---

## 9. Agent States

Every agent in the mesh has a lifecycle state tracked by the supervisor.

```
                  ┌──────────┐
        start     │ OFFLINE  │◀──── kill / crash
                  └────┬─────┘
                       │ tmux new-window
                  ┌────▼─────┐
         ┌───────│  IDLE    │◀────────────┐
         │       │ (::: en  │             │
         │       │  tmux)   │             │
         │       └────┬─────┘             │
         │            │ message received  │
         │       ┌────▼─────┐             │
         │       │ WORKING  │             │
         │       │ (procesa)│             │
         │       └────┬─────┘             │
         │            │ stuck >30s        │
         │       ┌────▼─────┐             │
         │       │  FROZEN  │──── Escape──┘
         │       └──────────┘
         │
         │       ┌──────────┐
         └───────│ THINKING │ (sin trabajo pendiente, procesando)
                 └──────────┘
```

### 9.1 State Detection (implementado en supervisor)

| Estado | Detección |
|--------|-----------|
| OFFLINE | Tmux window no existe |
| IDLE | Pane contiene `:::` (prompt Crush) |
| WORKING | Inbox > 0 archivos |
| THINKING | Pane cambia pero sin trabajo pendiente |
| FROZEN | Pane sin cambios por >30s con trabajo pendiente |

### 9.2 Recovery Actions

| Estado detectado | Acción |
|-----------------|--------|
| OFFLINE | `tmux new-window` + lanzar agente |
| FROZEN | Enviar Escape (cancelar comando actual) + mensaje "usa & para background" |
| CRASH_LOOP (≥5 crashes en 5min) | Escalar a human + escribir task de diagnóstico |
| STUCK_TASK (>60s en inbox) | Touch al archivo para re-trigger |

---

## 10. Liveness & Health

### 10.1 Health Checks

El supervisor corre cada `N` segundos (default: 4s) y verifica:

```
1. ¿busd está vivo?        → kill -0, restart si no
2. ¿cada ventana tmux existe? → list-windows
3. ¿cada agente responde?  → capture-pane (no vacío, no errores)
4. ¿web UI está vivo?      → pgrep server.js
5. ¿task-runner está vivo? → pgrep task-runner
```

### 10.2 Heartbeat

Los agentes no tienen heartbeat explícito. El supervisor detecta vida mediante
`tmux capture-pane`. Para remote agents (future), se necesita heartbeat explícito
cada `N` segundos.

### 10.3 Stuck Detection

```
1. Supervisor calcula md5 del contenido del pane
2. Si el md5 no cambia por >30s y hay trabajo pendiente → FROZEN
3. Envía Escape para cancelar comando colgado
4. Registra el stuck command en logs
5. Si persiste, escribe task de escalación
```

---

## 11. Protocol Operations

### 11.1 send_message

```
send_message(to, message, trace_id?)

Escribe archivo en /tmp/agent-bus/<to>/in/msg-<timestamp>-<pid>[--<trace_id>]
busd detecta, lee, reenvía al agente vía tmux send-keys
```

### 11.2 assign_task

```
assign_task(agent_id, task_body)

1. Crea trace con route [orchestrator, agent_id, checker_id]
2. Escribe tarea estructurada en /tmp/agent-bus/<agent_id>/tasks/
   (task-runner la detecta y ejecuta comandos directos)
   O: envía mensaje type=task al inbox del agente
3. task-runner o el agente aceptan → estado RUNNING
```

### 11.3 cancel_task

```
cancel_task(trace_id)

1. Envía signal type=cancel al agente
2. Agente debe parar en grace_period (5s)
3. trace-helper update-status → "cancelled"
4. Cleanup: kill subprocesos, release recursos
```

### 11.4 request_review

```
request_review(maker_id, checker_id, task_id, trace_id)

1. Maker envía type=review a checker (say checker "revisa: ...")
2. Checker recibe, examina output (git diff, node --check, etc.)
3. Checker responde type=verdict (approved / rejected)
4. trace-helper registra el hop maker→checker
```

### 11.5 redirect_task

```
redirect_task(trace_id, from_agent, to_agent, reason)

1. Cancela tarea en from_agent (si estaba running)
2. Crea nueva tarea con mismo trace_id
3. Asigna a to_agent
4. Incluye handoff context (partial output, estado actual)
5. trace-helper registra hop redirection con motivo
```

### 11.6 health_check

```
health_check(agent_id) → status

Supervisor verifica:
- Tmux window existe
- Pane no vacío
- No frozen con trabajo pendiente
→ Devuelve offline | idle | working | thinking | frozen
```

---

## 12. Security Model

Actualmente mínimo (entorno local). Para producción se requiere:

### 12.1 Identity

- Cada agente tiene un `agent_id` único (rol + número: `maker`, `a1`)
- Autenticación: por ahora confianza local (mismo filesystem, mismo tmux)
- Futuro: DID (Decentralized Identifiers) como ANP, o mTLS

### 12.2 Authorization

- Roles definen qué operaciones puede hacer cada agente
- Un maker NO puede hacer de checker sobre su propio trabajo (separación)
- El supervisor NO ejecuta tareas, solo monitorea

### 12.3 Message Integrity

- Los mensajes viajan como archivos de texto plano (suficiente para localhost)
- Futuro: firmas HMAC en cada mensaje

### 12.4 Audit

- Todas las operaciones se registran en el trace
- Los traces son append-only (no se editan hops pasados)
- El `version_registry` mantiene historial inmutable de versiones

---

## 13. Bridge to Existing Protocols

AOP no compite con MCP/A2A/ACP — los compone:

```
┌──────────────────────────────────────────────────┐
│                    AOP                            │
│  (orquestación con supervisión de calidad)        │
├──────────┬──────────┬────────────────────────────┤
│  Bridge  │  Bridge  │  Bridge                    │
│  to MCP  │  to A2A  │  to ACP                    │
├──────────┼──────────┼────────────────────────────┤
│ Tools &  │ Agent↔   │ Editor↔                    │
│ Data     │ Agent    │ Agent                      │
└──────────┴──────────┴────────────────────────────┘
```

| Protocolo | Bridge | Estado |
|-----------|--------|--------|
| **MCP** | Un agente AOP usa MCP para acceder a tools (APIs, DBs, filesystem) | ⚠️ Parcial (cada agente puede tener MCP servers configurados) |
| **A2A** | AOP puede delegar tareas a agentes A2A externos via `send_task` HTTP | 🔬 Planeado |
| **ACP** | AOP puede recibir comandos desde un editor via ACP (el editor es un cliente ACP, AOP es el "agent") | 🔬 Planeado |

---

## 14. Implementation Status

### ✅ Implemented (production)

| Componente | Dónde | Estado |
|------------|-------|--------|
| Transport (busd) | `orquestar-agentes/scripts/busd` | ✅ ~1 año en uso |
| Health supervisor | `orquestar-agentes/scripts/supervisor` | ✅ ~1 año en uso |
| Autonomous cycle | `orquestar-agentes/scripts/ciclador` | ✅ ~1 año en uso |
| Task runner | `orquestar-agentes/scripts/task-runner` | ✅ ~1 año en uso |
| Trace helper | `orquestar-agentes/scripts/trace-helper` | ✅ |
| Role skills | `orquestar-agentes/skills/{maker,checker,video-maker}` | ✅ |
| Version registry | `AAN/version_registry.py` | ✅ |
| Agent worker | `AAN/agent_light.py` | ✅ |
| Orchestrator (AAN) | `AAN/orchestrator.py` | ✅ |
| Context handoff | HANDOFF.md + `context.db` (j) | ✅ |
| Session management | `j` tool (s81) | ✅ |
| Setup/teardown | `orquestar`, `detener`, `remove-agent` | ✅ |

### ⚠️ Partial (functional, needs formalization)

| Componente | Dónde | Notas |
|------------|-------|-------|
| Quality gate contract | `checker/SKILL.md` | Especificado como skill, no como schema formal |
| Task state machine | `task-runner` + `orchestrator.py` | Estados implícitos en el código, no en spec |
| Role discovery | `orquestar` script | Estático (a1, a2, a3), no dinámico |

### 🔬 Planned (specified but not built)

| Componente | Prioridad |
|------------|-----------|
| HTTP transport binding | Media |
| A2A bridge | Alta |
| ACP bridge | Media |
| Agent Card / Role Card standard | Alta |
| Dynamic agent discovery | Baja |
| Remote agent support (non-tmux) | Baja |
| Formal security model | Media |

---

## Appendix: Existing Files Map

```
orquestar-agentes/
├── protocol.md                      → Base protocol (READ→ACT→VERIFY)
├── ROADMAP.md                       → Future ideas
├── scripts/
│   ├── orquestar                    → Setup: N agents + bus + daemons
│   ├── busd                         → Transport: inotify message bus
│   ├── supervisor                   → L6: health + stuck detection
│   ├── ciclador                     → L7: autonomous work cycle
│   ├── task-runner                  → L2: structured task executor
│   ├── trace-helper                 → L5: audit trail tracker
│   ├── say                          → Utility: send message to agent
│   ├── detener                      → Clean shutdown
│   ├── add-agent / remove-agent     → Dynamic agent management
│   └── ... (video-maker, etc.)
├── skills/
│   ├── maker/SKILL.md               → L3: code implementation role
│   └── checker/SKILL.md             → L3: quality gate role
└── web/                             → Dashboard UI

AAN (s77-aan)/
├── orchestrator.py                  → L2: DB-pooling task launcher
├── agent_light.py                   → Worker agent (API + CLI modes)
├── version_registry.py              → L5: version + agent_work DB
├── SCHEMA.md                        → Version Registry schema
├── server.py / api.py               → REST API for version management
├── aan_config.json                  → Config file
└── aan.db                           → SQLite database

j (s81)/
├── ARCHITECTURE.md                  → System design
├── j                                → Entry point (single bash script)
├── context.db                       → L4: session context SQLite
├── HANDOFF.md                       → L4: context handoff document
└── PENDIENTE.md                     → L4: pending items
```

---

*This specification is itself an output of the AOP cycle: synthesized from
existing code, to be reviewed by checker (the user), iterated based on feedback,
and versioned in the version registry.*
