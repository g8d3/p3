# Checklist para Proyectos — Verificación de los 7 Pilares

Usa esta checklist al iniciar un nuevo proyecto o al evaluar uno existente.
Cada ítem tiene referencias a los proyectos donde se aprendió.

---

## I. Visibilidad Total

- [ ] **Logs estructurados** (JSON, no texto plano) — s71, s72
- [ ] **Estado del servidor expuesto** vía API/WS — s72 (`/api/actions`, `/api/status`)
- [ ] **Cliente/envía logs al servidor** — s72 (modo dev, `POST /api/dev/error`)
- [ ] **Dashboard en tiempo real** — s72, s63 (WebSocket push)
- [ ] **Errores nunca silenciosos** — s71 (cada `catch {}` vacío costó horas)
- [ ] **Accesible por IA** (sin necesidad de visión) — s72 (CDP + snapshot)

## II. Configuración sobre Código

- [ ] **Config externa en YAML/JSON** — s71 (~80% de cambios eran config)
- [ ] **Hot-reload** (cambiar config ≠ reiniciar) — s72 (`POST /api/style`)
- [ ] **API keys en servidor** (nunca en cliente) — s72 (`POST /api/config`)
- [ ] **Editor de config en UI** — s72 (panel de estilo)

## III. API Ultra-Simple

- [ ] **Acciones de ≤2 palabras** — s71/IDEAS.md (`agent.write()`, `voice.listen()`)
- [ ] **Valores en lenguaje natural** ("send", no `0x10001000`) — s71
- [ ] **Fallbacks automáticos** — s71 (IME action → clipboard → paste)
- [ ] **Sin lookup de documentación** para el caso común

## IV. IPC Universal

- [ ] **JSON sobre archivos** (inbox/outbox) — s72, s63, s73
- [ ] **stdout JSON** para procesos hijo — s63 (IPC agnóstico al lenguaje)
- [ ] **WebSocket** para UI en tiempo real — s63 (no Socket.IO)
- [ ] **Cualquier lenguaje puede ser agente** — s63, s65

## V. Ciclo Corto

- [ ] **Tests automatizados en <30s** — s72 (`harness.py`)
- [ ] **CDP/Playwright para testing de UI** — s72 (agent-browser snapshot)
- [ ] **Watchdog que detecta cambios y re-corre tests** — s72 (`watch.sh`)
- [ ] **Benchmarks para regresiones de performance** — s64

## VI. Resiliencia por Capas

- [ ] **Cadenas de fallback** (Plan A → B → C) — s71, s73 (IPC spec)
- [ ] **Timeouts con reintentos** — s64 (120s timeout, fallback a script default)
- [ ] **Mecanismo de limpieza** de archivos temporales — s72 (`POST /api/cleanup`)
- [ ] **Sin puntos únicos de falla** — s71 (TTS edge → fallback local → espeak)

## VII. Commits Trazables

- [ ] **Un cambio lógico por commit** — s72
- [ ] **Mensaje responde "por qué", no "qué"** — s72
- [ ] **Tests se ejecutan pre-commit o watchdog los detecta** — s72
- [ ] **Cualquier agente puede ver `git diff HEAD~1`** — s72

---

## Por Tipo de Proyecto

### Web App (como s72)
- [ ] API REST con estado completo
- [ ] Modo dev con errores visibles
- [ ] CDP testeable (árbol de accesibilidad)
- [ ] Logs del browser llegan al servidor

### Mobile App (como s71)
- [ ] ADB screencap para visión remota
- [ ] uiautomator dump para árbol de accesibilidad
- [ ] Logs vía WebSocket o POST
- [ ] Config JSON externa con hot-reload

### Multi-Agente (como s63, s65)
- [ ] IPC vía inbox/outbox
- [ ] Orchestrator con cola de tareas
- [ ] Cada agente es un proceso independiente
- [ ] Health checks y auto-reinicio

---

*Referencia: s73-framework/MANIFIESTO.md*
