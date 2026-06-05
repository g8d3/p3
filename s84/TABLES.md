# Tablas de Referencia — Protocolos de Control de Agentes AI

> Extraídas de la conversación en s84 (Junio 2026).
> Contenido completo en `AOP-SPEC.md`, `A2A-TEST-RESULTS.md`, `A2A-Q-RFC.md`.

---

## 1. Comparativa General de Protocolos para Control de Agentes

| Protocolo | Dirección | Creador / Gobernancia | Capa | Transporte | Descubrimiento | Madurez |
|---|---|---|---|---|---|---|
| **MCP** (Model Context Protocol) | agente ↔ herramientas/datos | Anthropic → Linux Foundation (AAIF) | Vertical: un agente con sus tools | JSON-RPC 2.0 sobre stdio o HTTP+SSE | El servidor anuncia tools al conectar | ✅ Producción (~97M SDK/mes) |
| **A2A** (Agent-to-Agent) | agente ↔ agente | Google → Linux Foundation | Horizontal: coordinación entre agentes | JSON-RPC 2.0 sobre HTTP, gRPC, SSE | Agent Cards en `/.well-known/agent.json` | ✅ Producción (150+ organizaciones) |
| **ACP** (Agent Client Protocol) | cliente (IDE/CLI) ↔ agente | Zed + JetBrains | Orquestación: editor invoca agente | JSON-RPC sobre stdio (default), HTTP, WebSocket | Cliente lanza agente conocido | ✅ Crecimiento rápido (19+ agentes) |
| **ACP** (Agent Communication Protocol) | agente ↔ agente | BeeAI/IBM → Linux Foundation | Multi-framework | HTTP REST + SSE | Registry | 💀 Deprecado — fusionado con A2A |
| **ANP** (Agent Network Protocol) | agente ↔ agente (Internet abierto) | Comunidad | Red descentralizada: descubrimiento global | HTTPS / JSON-LD | DID + `.well-known` + buscadores | 🔬 Especificación |
| **AIDP** (Agent Interaction & Delegation Protocol) | agente → execution boundary | IETF (Internet-Draft) | Control-plane: autoridad, delegación, auditoría | Transporte-agnóstico | N/A (autoridad formal) | 📄 Borrador IETF |
| **AOCL** (Agent Orchestration Control Layers) | orquestador → pipeline | IETF (Internet-Draft) | Gobernanza: pipeline de 11 capas | Transporte-agnóstico (usa AEE envelopes) | N/A (orquestación interna) | 📄 Borrador IETF |
| **MACP** (Multi-Agent Coordination Protocol) | agente ↔ agente | Comunidad | Coordinación kernel: sesiones con modos | gRPC sobre HTTP/2 | Manifiestos + negociación | 📄 Draft comunitario |
| **MPAC** (Multi-Principal Agent Coordination) | agente ↔ agente | Investigación | Multi-stakeholder: detección de conflictos | Capa de aplicación | Sesión con coordinador | 📄 Draft |
| **OpenEAGO** | orquestación empresarial | FINOS (Linux Foundation) | Gobernanza empresarial: compliance, data sovereignty | mTLS, HTTP | Registry centralizado con mTLS | 📄 Especificación FINOS |
| **Function Calling** | modelo ↔ código del dev | OpenAI (solo OpenAI) | In-process: modelo invoca funciones | JSON dentro de request/response | El dev registra funciones por request | ✅ Solo OpenAI |
| **AP2** (Agent Payment Protocol) | agente ↔ sistema de pagos | Comunidad | Pagos autónomos | Criptográfico | N/A | 🔬 Emergente |

### Stack recomendado (capas complementarias)

```
┌─────────────────────────────────────────────┐
│  Descubrimiento global     ANP              │
├─────────────────────────────────────────────┤
│  Coordinación agente↔agente  A2A / MACP     │
├─────────────────────────────────────────────┤
│  Cliente↔Agente (IDE/CLI)   ACP             │
├─────────────────────────────────────────────┤
│  Agente↔Herramientas        MCP             │
├─────────────────────────────────────────────┤
│  Control-plane / Auditoría  AIDP / AOCL     │
└─────────────────────────────────────────────┘
```

---

## 2. Línea de Tiempo: Confusión de los dos ACP

| Fecha | Evento |
|-------|--------|
| 2024 | IBM/BeeAI lanza **Agent Communication Protocol** (ACP) — agente↔agente |
| Abril 2025 | Google lanza **Agent-to-Agent Protocol** (A2A) — 50+ partners |
| Junio 2025 | Google dona A2A a **Linux Foundation** |
| Agosto 2025 | Zed lanza **Agent Client Protocol** (ACP) — mismo acrónimo, distinto problema (cliente↔agente) |
| Finales 2025 | BeeAI ACP se fusiona con **A2A** — el "ACP agente↔agente" desaparece |
| Febrero 2026 | JetBrains se une a Zed como co-maintainer del **Agent Client Protocol** |
| 2026 hoy | Quedan dos: **ACP** (cliente↔agente, Zed+JetBrains) y **A2A** (agente↔agente, Linux Foundation) |

---

## 3. A2A Test Results (8 escenarios)

| # | Test | Resultado | Notas |
|---|------|-----------|-------|
| 1 | **Agent Discovery** (Agent Cards) | ✅ | Cards servidas en `/.well-known/agent.json`, skills declarativas |
| 2 | **Task Execution** (submit → poll → complete) | ✅ | Lifecycle `submitted → working → completed` |
| 3 | **Task Cancellation** | ✅ | `POST /tasks/{id}:cancel` — **bug de race condition detectado y corregido** |
| 4 | **Quality Gate** | ❌ | **No existe.** Aprobado y rechazado terminan ambos en `state: completed` |
| 5 | **Cross-Agent Discovery** | ⚠️ | Agent Cards listan skills pero **sin criterios de calidad** |
| 6 | **Multi-turn Context** (`contextId`) | ⚠️ | `contextId` existe pero **sin contrato de almacenamiento** |
| 7 | **State Machine Completeness** | ❌ | Faltan: `pending-review`, `needs-revision`, `quality-passed`, `escalated` |
| 8 | **Task Listing** | ✅ | `GET /tasks` funciona |

### Hallazgo clave

A2A asume agentes **opacos y confiables**. No hay diferencia entre
"completado con éxito" y "completado con errores" a nivel protocolo.
La calidad queda enterrada en texto del artifact, invisible para la
máquina de estados.

---

## 4. A2A State Machine — Missing Quality Dimension

```
A2A Task States (actual):
  submitted → working → completed  ✅ (success)
                      → failed      ❌ (error)
                      → canceled    🛑 (user-initiated stop)
                      → rejected    🚫 (server refused)
                      → input-required  (needs more info)
                      → auth-required   (needs auth)

MISSING from A2A state machine:
  → pending-review      (work done, needs validation)     🔍
  → needs-revision      (checker rejected, go back)       🔄
  → quality-approved    (passed all gates)                ✅
  → escalated           (human intervention needed)       ⚠️
```

---

## 5. A2A Agent Adoption (Junio 2026)

| Agente / Framework | ¿A2A nativo? | Versión | Estado | Vía |
|---|---|---|---|---|
| **Google ADK** | ✅ Sí | v1.0 | Producción | Nativo |
| **LangGraph/LangChain** | ✅ Sí | v1.0 | Producción | LangSmith Server |
| **CrewAI** | ✅ Sí | v1.0 | Producción | Nativo |
| **Microsoft Agent Framework** | ✅ Sí | v1.0 | Producción | Sucesor de AutoGen+SK |
| **AutoGen (AG2 fork)** | ✅ Sí | v1.0 | Producción | Fork comunitario AG2 |
| **Semantic Kernel** | ✅ Sí | v1.0 | Producción | Migrando a MAF |
| **Pydantic AI** | ✅ Sí | v1.0 | Producción | Nativo |
| **BeeAI (IBM)** | ✅ Sí | v1.0 | Producción | Nativo |
| **Agno** | ✅ Sí | v1.0 | Producción | Nativo |
| **Cisco agntcy** | ✅ Sí | v1.0 | Producción | Nativo |
| **LiteLLM** | ✅ Sí | v1.0 | Producción | Nativo |
| **OpenCode** | ❌ No | ⚠️ v0.3 | Community | `opencode-a2a` (wrapper) |
| **Claude Code** | ❌ No | — | Community | `a2a-adapter` (wrapper) |
| **Crush** | ❌ No | — | ❌ Nada | Ni nativo ni wrapper |
| **Cursor** | ❌ No | — | ❌ Nada | — |
| **Windsurf** | ❌ No | — | ❌ Nada | — |
| **Docker Desktop** | ❌ No | — | ❌ Nada | Solo MCP |

**Patrón**: Frameworks de orquestación (ADK, LangGraph, CrewAI) adoptaron A2A rápido.
Agentes de código (OpenCode, Crush, Cursor) no — apuestan por MCP.

### SDKs oficiales A2A

| Lenguaje | Paquete | Estado |
|---|---|---|
| Python | `pip install a2a-sdk` | ✅ v1.1.0 |
| JavaScript/TypeScript | `npm install @a2a-js/sdk` | ✅ v1.0 |
| Go | `go get github.com/a2aproject/a2a-go` | ✅ v1.0 |
| Java | Maven `a2a-java` | ✅ v1.0 |
| C#/.NET | `dotnet add package A2A` | ✅ v1.0 |
| Rust | `cargo add a2a-lf` | ✅ v1.0 |

---

## 6. AOP — 8 Capas del Protocolo de Orquestación

| Capa | Nombre | Responsabilidad | Implementación actual |
|---|---|---|---|
| L0 | **Transport** | Entrega de mensajes entre agentes | `busd` (inotify + archivos) |
| L1 | **Agent Roles** | Identidad, capacidades, permisos | Roles a1/a2/a3 + skills |
| L2 | **Task Lifecycle** | Crear, asignar, monitorear, cancelar | `task-runner` + `orchestrator.py` (AAN) |
| L3 | **Quality Gate** | ✅ Diferenciador — validar output, aprobar/rechazar, redirigir | `checker` skill, ciclo maker→checker |
| L4 | **Session** | Contexto compartido entre tareas | HANDOFF.md + `context.db` (j) |
| L5 | **Trace** | Auditoría completa (quién, qué, cuándo, resultado) | `trace-helper` + `version_registry` |
| L6 | **Supervision** | Health checks, crash recovery, stuck detection | `supervisor` |
| L7 | **Autonomous Cycle** | Escaneo proactivo, asignación automática, loop 24/7 | `ciclador` |

---

## 7. AOP vs A2A-Q Extension

| Capacidad | AOP (spec local) | A2A-Q (extensión propuesta) |
|---|---|---|
| Transporte | File bus (inotify), HTTP planeado | HTTP (JSON-RPC, REST, gRPC) |
| Roles explícitos | maker, checker, video-maker, explorer | Se declaran en `AgentSkill.qualityCriteria` |
| Quality Gate | L3 del protocolo, **obligatorio** | Campo `qualityCriteria` + nuevos estados |
| Cancelación | Via signal + grace period | Via `CancelTask` (A2A base) |
| Redirección | trace_hop + reassign | `needs-revision` → maker corrige |
| Sesiones | HANDOFF.md + context.db | `contextId` (A2A base) + `a2a-quality:trace` |
| Trazabilidad | trace-helper (archivos JSON) | `metadata.a2a-quality:trace` (en el task) |
| **Eficacia** | maker→checker con aprobado/rechazado | `a2a-quality:efficacy` (quality_score, revision_count, criteria_results) |
| **Eficiencia** | — | `a2a-quality:efficiency` (wall_time, processing_time, tokens, utilization) |
| **Proceso** | — | `a2a-quality:process` (bottleneck, assignment_correctness) |
| Autonomía | ciclador escanea y asigna | No resuelto (fuera de scope) |
| Supervisión | supervisor con health checks | No resuelto (fuera de scope) |

---

## 8. A2A-Q: Nuevos Estados vs A2A Actual

| Estado A2A-Q | Valor | Descripción | ¿Terminal? |
|---|---|---|---|
| Pending Review | `quality:pending-review` | Trabajo terminado, esperando validación | No |
| Needs Revision | `quality:needs-revision` | Checker rechazó, maker debe corregir | No |
| Quality Passed | `quality:passed` | Todas las gates de calidad pasaron | Sí |
| Escalated | `quality:escalated` | Calidad dudosa, humano necesita revisar | Sí |

### Máquina de estados extendida

```
working → quality:pending-review → quality:needs-revision → working
                                 → quality:passed → (completado)
                                 → quality:escalated → [humano decide]
```

---

## 9. Efficacy & Efficiency Metrics (A2A-Q)

| Categoría | Métrica | Qué mide |
|---|---|---|
| **Eficacia del agente** | `quality_score` | 0.0–1.0, basado en criterios pasados/totales |
| | `pass` | ¿Aprobó todas las gates? |
| | `revision_count` | Número de ciclos maker→checker |
| | `criteria_results` | Desglose por criterio individual |
| **Eficiencia del proceso** | `total_wall_time_ms` | Tiempo real desde creación hasta aprobación |
| | `processing_time_ms` | Tiempo que el agente realmente trabajó |
| | `review_time_ms` | Tiempo que el checker tomó |
| | `revision_cycles` | Número de veces que volvió a maker |
| | `estimated_tokens` | Consumo aproximado de tokens |
| | `tool_calls` | Número de tools invocadas |
| | `utilization` | Tiempo productivo / tiempo total |
| **Calidad de asignación** | `assignment_correctness` | ¿Se asignó al agente correcto? |
| | `bottleneck` | Dónde se perdió más tiempo |

---

## 10. Files produced in s84

| File | Lines | Purpose |
|---|---|---|
| `AOP-SPEC.md` | 789 | Especificación formal del protocolo AOP (8 capas) |
| `A2A-TEST-RESULTS.md` | ~400 | Tests A2A + propuesta de extensión A2A-Q |
| `A2A-Q-RFC.md` | ~500 | RFC formal de la extensión de calidad para A2A |
| `TABLES.md` | ~350 | Este archivo — todas las tablas de referencia |
| `a2a_test/a2a_server.py` | ~300 | Servidor A2A v1.0 compliant (bug de cancelación corregido) |
| `a2a_test/agent_alpha.py` | ~70 | Agente generalista (puerto 9001) |
| `a2a_test/agent_beta.py` | ~65 | Agente de calidad (puerto 9002) |
| `a2a_test/client.py` | ~200 | Cliente de pruebas con 8 escenarios |
| `a2a_test/run_evidence.sh` | ~110 | Script reproducible con evidencia HTTP |
