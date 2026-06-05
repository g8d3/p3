# A2A Protocol Test Results & Extension Proposal

> **Date**: 2026-06-05
> **A2A Spec Version**: 1.0.0
> **SDK Version**: a2a-sdk 1.1.0 (Google → Linux Foundation)
> **Test Agents**: Alpha-Generalist (port 9001), Beta-Quality (port 9002)
> **Location**: `s84/a2a_test/`

---

## 1. Test Results

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | **Agent Discovery** (Agent Cards) | ✅ | Cards served at `/.well-known/agent.json`, skills described declaratively |
| 2 | **Task Execution** (submit → poll → complete) | ✅ | Lifecycle `submitted → working → completed` works via `POST /message:send` + `GET /tasks/{id}` |
| 3 | **Task Cancellation** | ✅ | `POST /tasks/{id}:cancel` transitions to `canceled` state |
| 4 | **Quality Gate** | ❌ | **No protocol-level quality distinction.** Both "approved" and "rejected" outputs end in `completed` state. Quality is buried in artifact text — invisible to the protocol. |
| 5 | **Cross-Agent Discovery** | ⚠️ | Agent Cards list skills but **no quality criteria, acceptance tests, or expected output validation** |
| 6 | **Multi-turn Context** (`contextId`) | ⚠️ | `contextId` exists but **no storage contract** — server may or may not remember context |
| 7 | **State Machine Completeness** | ❌ | Missing states: `pending-review`, `needs-revision`, `quality-approved`, `escalated` |
| 8 | **Task Listing** | ✅ | `GET /tasks` returns all tasks with their states |

---

## 2. Limits Encontrados

### 2.1 Quality es invisible para el protocolo

A2A asume que los agentes son **opacos y confiables**. Si un agente produce basura, el protocolo no lo sabe:

```
Cliente                    A2A Agent (Beta)
   │                              │
   │  POST /message:send          │
   │  "review this buggy code"    │
   │─────────────────────────────▶│
   │                              ├─ detecta keywords "bug"
   │                              ├─ genera respuesta: "❌ FAILED"
   │                              │
   │  GET /tasks/{id}             │
   │◀─────────────────────────────│
   │  status.state = "completed"  │  ← MISMO estado que si hubiera pasado
   │  artifact.text = "❌ FAILED" │  ← Calidad solo aquí, texto opaco
```

**Lo que falta**: una dimensión de calidad en el `TaskStatus` que A2A no tiene.

### 2.2 Sin concepto de "checker" o "quality gate"

En AOP (tu protocolo), el flujo tiene un paso explícito de validación:

```
maker → (entrega) → checker → (aprueba/rechaza) → maker corrige o se acepta
```

En A2A, no hay `checker`. No hay `pending-review`. No hay `needs-revision`. No hay un estado que diga "esto se terminó pero falta validación de otro agente".

### 2.3 Agent Cards no declaran criterios de calidad

Un Agent Card dice:
- `skills: ["research", "summarize"]` ← qué hace
- Pero no dice: `criteria: ["no TODOs", "tests pass", "no hardcoded values"]` ← cómo se valida

### 2.4 contextId es frágil

A2A define `contextId` en los mensajes, pero **no especifica**:
- Quién almacena el contexto (¿cliente? ¿servidor? ¿ambos?)
- Cuánto tiempo se retiene
- Cómo se recupera
- Si el agente DEBE usarlo

En tu AOP esto está resuelto con `HANDOFF.md` + `context.db` + `session_id`.

### 2.5 Sin trazabilidad de calidad

Los `trace` de AOP registran cada hop (maker→checker, verdict, redirection).
A2A solo tiene `metadata` arbitrario — no hay trazabilidad estructurada de calidad.

---

## 3. Propuesta: Extensión A2A-Q (Quality Extension for A2A)

En lugar de crear un protocolo nuevo, propongo una **extensión oficial de A2A**.
A2A ya define un [mecanismo de extensiones](https://a2a-protocol.org/latest/specification/#46-extensions)
con `AgentExtension`, `A2A-Extensions` header, y puntos de extensión en el data model.

### 3.1 ¿Por qué extensión y no protocolo nuevo?

| Razón | Explicación |
|-------|-------------|
| A2A ya tiene mercado | 50+ empresas, Linux Foundation, SDKs en 4 lenguajes |
| Mecanismo de extensiones existe | `AgentExtension`, headers, extension points ya están en la spec v1.0 |
| Composición, no competencia | La extensión se sienta SOBRE A2A. No compite, lo complementa. |
| Adopción inmediata | Cualquier agente A2A puede ignorar la extensión y seguir funcionando. Los que la implementan ganan calidad. |

### 3.2 Lo que la extensión agrega

```
A2A base (spec v1.0)
├── Agent Card           → + qualityCriteria (expectativas de calidad)
├── Task                 → + qualityState (pending-review, needs-revision, quality-approved, escalated)
├── SendMessage          → + qualityGate (checker obligatorio o no)
├── new: RequestReview   → Enviar trabajo a un checker
├── new: SubmitVerdict   → Checker aprueba/rechaza
├── Agent Card           → + qaSkills (el agente puede hacer de checker)
└── Metadata             → + traceHop (trazabilidad estructurada)
```

### 3.3 Extension Spec (v0.1 draft)

#### 3.3.1 Extension Declaration

```json
{
  "id": "a2a-quality",
  "name": "A2A Quality Extension",
  "version": "0.1.0",
  "description": "Adds quality gates, review cycles, and acceptance criteria to A2A tasks."
}
```

Declarado en el `AgentCard.extensions`:

```json
{
  "extensions": [
    {
      "id": "a2a-quality",
      "version": "0.1.0",
      "config": {
        "min_reviewers": 1,
        "auto_approve_skills": ["code-review", "validate"],
        "criteria": [
          "No syntax errors",
          "No hardcoded secrets",
          "Tests pass"
        ]
      }
    }
  ]
}
```

Headers en requests:

```
A2A-Extensions: a2a-quality@0.1.0
```

#### 3.3.2 New Task States

A2A-Q agrega estos estados al `TaskState`:

```
Estado         │ Descripción
───────────────┼─────────────────────────────────────────
pending-review │ Trabajo terminado, esperando validación
needs-revision │ Checker rechazó, maker debe corregir
quality-passed │ Pasó todas las gates de calidad
escalated      │ Calidad dudosa, humano necesita revisar
```

Máquina de estados extendida:

```
working → pending-review → needs-revision → working (vuelve a maker)
                         → quality-passed  → completed (estado final A2A)
                         → escalated       → [humano decide]
```

#### 3.3.3 Quality Criteria en Agent Card

Nuevo campo `qualityCriteria` en `AgentSkill`:

```json
{
  "skills": [{
    "id": "code-review",
    "name": "Code Review",
    "qualityCriteria": {
      "autoFail": ["leaked_secret", "syntax_error"],
      "checks": [
        "Syntactic correctness (node --check)",
        "No TODOs introduced",
        "Tests pass",
        "No console.log debugging"
      ],
      "requiredReviewers": ["checker"],
      "minApprovals": 1
    }
  }]
}
```

#### 3.3.4 New Operations

##### `RequestReview`

```
POST /tasks/{id}:requestReview

{
  "reviewer": "checker|agent-id",
  "criteria": ["node --check", "no TODOs"],
  "traceId": "trace-abc-123",
  "timeout": 120
}
```

Transiciona el task de `working` → `pending-review`.

##### `SubmitVerdict`

```
POST /tasks/{id}:submitVerdict

{
  "decision": "approved | rejected | needs-work",
  "summary": "Validation passed. All criteria met.",
  "details": [
    "✅ No syntax errors",
    "❌ Hardcoded API key in config.js"
  ],
  "traceId": "trace-abc-123"
}
```

Transiciona el task a `quality-passed`, `needs-revision`, o `escalated`.

#### 3.3.5 Trace Hops Estructurados

Cada salto calidad queda registrado en el metadata del task:

```json
{
  "metadata": {
    "a2a-quality:trace": [
      {"from": "maker", "to": "checker", "state": "pending-review", "ts": 1749060000},
      {"from": "checker", "to": "maker", "state": "needs-revision", "ts": 1749060100,
       "reason": "Hardcoded API key"},
      {"from": "maker", "to": "checker", "state": "pending-review", "ts": 1749060200},
      {"from": "checker", "to": "", "state": "quality-passed", "ts": 1749060300}
    ]
  }
}
```

#### 3.3.6 Efficacy & Efficiency Metrics

A2A-Q agrega métricas estructuradas de eficacia y eficiencia a cada task:

```json
{
  "metadata": {
    "a2a-quality:efficacy": {
      "task_id": "task-abc-123",
      "agent_id": "maker-A",
      "quality_score": 0.85,
      "pass": true,
      "revision_count": 2,
      "checker_verdicts": ["rejected", "rejected", "approved"],
      "criteria_results": [
        {"check": "No syntax errors", "pass": true},
        {"check": "Tests pass", "pass": true},
        {"check": "No hardcoded secrets", "pass": false, "severity": "critical"},
        {"check": "No TODOs added", "pass": true}
      ]
    },
    "a2a-quality:efficiency": {
      "task_id": "task-abc-123",
      "agent_id": "maker-A",
      "total_wall_time_ms": 45000,
      "processing_time_ms": 12000,
      "review_time_ms": 33000,
      "revision_cycles": 2,
      "estimated_tokens": 45000,
      "tool_calls": 12,
      "utilization": 0.65
    },
    "a2a-quality:process": {
      "task_id": "task-abc-123",
      "assignment_correctness": "correct",
      "agent_selection_latency_ms": 200,
      "handoff_count": 0,
      "context_retrieval_time_ms": 15,
      "bottleneck": "review (66% of wall time)"
    }
  }
}
```

| Categoría | Métrica | Qué mide |
|-----------|---------|----------|
| **Eficacia del agente** | `quality_score` | 0.0–1.0, basado en criterios pasados/totales |
| | `pass` | ¿Aprobó todas las gates? |
| | `revision_count` | Número de ciclos maker→checker |
| | `criteria_results` | Desglose por criterio individual |
| **Eficiencia del proceso** | `total_wall_time_ms` | Tiempo real desde que se creó hasta que se aprobó |
| | `processing_time_ms` | Tiempo que el agente realmente trabajó |
| | `review_time_ms` | Tiempo que el checker tomó |
| | `revision_cycles` | Número de veces que volvió a maker |
| | `estimated_tokens` | Consumo aproximado de tokens |
| | `tool_calls` | Número de tools invocadas |
| | `utilization` | Tiempo productivo / tiempo total |
| **Hardware (local)** | `cpu_usage_pct` | % de CPU usado durante la tarea |
| | `memory_mb` | RAM usada por el agente (MB) |
| | `context_size` | Tamaño del contexto (tokens, archivos, sesiones activas) |
| | `context_window_pct` | % del context window del LLM utilizado |
| | `process_count` | Número de procesos hijos/spawned |
| **Hardware (remoto)** | `api_latency_ms` | Latencia de llamadas a APIs externas |
| | `remote_gpu_used` | GPU remota utilizada (modelo, VRAM) |
| | `network_io_bytes` | Bytes enviados/recibidos |
| **Agente (runtime)** | `runtime_language` | Python, Go, TypeScript, Rust... |
| | `runtime_memory_mb` | Memoria base del runtime (ej: OpenCode ~200MB, Crush ~30MB) |
| | `startup_time_ms` | Tiempo en iniciar el agente |
| **Calidad de asignación** | `assignment_correctness` | ¿Se asignó al agente correcto? |
| | `bottleneck` | Dónde se perdió más tiempo |

Estas métricas permiten:
- **Comparar agentes**: ¿cuál es más eficaz? ¿cuál más eficiente?
- **Detectar agentes problemáticos**: alto `revision_count` + bajo `quality_score` = agente que no cumple
- **Optimizar rutas**: si el bottleneck siempre es "review", toca añadir más checkers o mejorar los criterios
- **Auditar**: trace completo de cada tarea con métricas de rendimiento

---

## 4. Comparación: AOP vs A2A-Q Extension

| Capacidad | AOP (tu spec) | A2A-Q (extensión propuesta) |
|-----------|--------------|---------------------------|
| Transporte | File bus (inotify), HTTP planeado | HTTP (JSON-RCP, REST, gRPC) |
| Roles explícitos | maker, checker, video-maker, explorer | Se declaran en `AgentSkill.qualityCriteria` |
| Quality Gate | L3 del protocolo, obligatorio | Campo `qualityCriteria` + nuevos estados |
| Cancelación | Via signal + grace period | Via `CancelTask` (A2A base) |
| Redirección | trace_hop + reassign | `needs-revision` → maker corrige |
| Sesiones | HANDOFF.md + context.db | `contextId` (A2A base) + `a2a-quality:trace` |
| Trazabilidad | trace-helper (archivos JSON) | `metadata.a2a-quality:trace` (en el task) |
| **Eficacia** | maker→checker cycle con aprobado/rechazado | `a2a-quality:efficacy` en metadata (quality_score, revision_count, criteria_results) |
| **Eficiencia** | — | `a2a-quality:efficiency` en metadata (wall_time, processing_time, tokens, utilization) |
| **Proceso** | — | `a2a-quality:process` en metadata (bottleneck, assignment_correctness, handoff_count) |
| Autonomía | ciclador escanea y asigna | No resuelto (fuera de scope) |
| Supervisión | supervisor con health checks | No resuelto (fuera de scope) |

### 4.1 Qué ganas con la extensión

- **Interoperabilidad inmediata**: cualquier agente A2A existente puede añadir la extensión
- **Sin fork del protocolo**: la extensión se declara en headers y AgentCard
- **Backward compatible**: agents sin la extensión siguen funcionando
- **Menos código**: reusas el transporte HTTP, el modelo de tareas, la autenticación de A2A

### 4.2 Qué pierdes respecto a AOP

- **Transporte file bus** (inotify) — no existe en A2A
- **Supervisor** con health checks + crash recovery — out of scope
- **Ciclador** autónomo — out of scope
- **Roles agnósticos** — A2A no distingue maker de checker a nivel protocolo
- **Calidad obligatoria** — en A2A-Q la extensión es optativa (el agente base sigue sin validar)

---

## 5. Conclusión y Recomendación

### La extensión es el camino correcto

| Criterio | Protocolo nuevo (desde cero) | Extensión A2A-Q |
|----------|------------------------------|-----------------|
| Esfuerzo de adopción | Alto (meses) | Bajo (semanas) |
| Compatibilidad | Ninguna | 100% con A2A |
| Mercado existente | 0 | 50+ empresas, SDKs |
| Mecanismo de extensión | Inventar | Ya existe en spec v1.0 |
| Riesgo | Alto (nadie lo adopta) | Bajo (pierdes nada, ganas calidad) |

### Próximos pasos concretos

1. **Escribir la extensión como RFC formal** (formato que acepte el A2A project)
2. **Implementar en Python** sobre el SDK oficial (`a2a-sdk`)
3. **Probar con agentes reales**: que Alpha y Beta usen A2A-Q
4. **Publicar**: abrir PR/discusión en el [repo del A2A project](https://github.com/a2aproject/A2A)

---

## A: Test Files

| File | Purpose |
|------|---------|
| `a2a_test/a2a_server.py` | A2A v1.0 server (lightweight, threading) |
| `a2a_test/agent_alpha.py` | Alpha agent (generalist, port 9001) |
| `a2a_test/agent_beta.py` | Beta agent (quality specialist, port 9002) |
| `a2a_test/client.py` | Test orchestrator + 8 test scenarios |
| `a2a_test/run_test.sh` | Tmux launcher (3 windows: alpha, beta, client) |
