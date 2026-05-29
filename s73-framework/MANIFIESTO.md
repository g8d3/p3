# Manifiesto del Framework Multi-Agente

**Versión:** 0.1  
**Fecha:** 29 de mayo de 2026  
**Origen:** Síntesis de 10+ proyectos en p3 (s63–s72)  
**Propósito:** Definir los principios inmutables sobre los que se construye toda aplicación en este framework.

---

## Preámbulo

Hemos construido aplicaciones de todo tipo — dashboards, generadores de video, clientes móviles, agentes autónomos, benchmarks, sandboxes — y en cada una encontramos los mismos problemas:

- La IA no ve lo que pasa (sin visibilidad)
- Cada cambio requiere recompilar o reiniciar (ciclo lento)
- Los errores se tragan silenciosamente (sin resiliencia)
- Los agentes no pueden coordinarse (sin IPC)
- No hay trazabilidad entre cambios (sin commits)

Este framework es la respuesta. No es una biblioteca ni un lenguaje nuevo. Es un **conjunto de decisiones arquitecturales** que cualquier proyecto, en cualquier lenguaje, puede seguir.

---

## Los 7 Pilares

### I. Visibilidad Total

> **Toda capa del sistema debe exponer su estado en tiempo real, para humanos y para IA.**

- Cada acción se loguea con timestamp, duración, y resultado.
- Los errores nunca se tragan — siempre se registran con stack trace.
- El estado del sistema es inspeccionable vía API y WebSocket.
- La UI muestra logs en vivo, cola de tareas, estado de agentes.
- No hay `catch {}` vacío. No hay `print()` sin contexto.
- **Origen:** s71 (errores silenciosos que costaron horas), s72 (modo dev + actions API), s63 (logs de agente).

### II. Configuración sobre Código

> **El comportamiento se define en archivos externos, no en el código fuente.**

- Toda decisión de comportamiento vive en YAML/JSON externo.
- El runtime detecta cambios en caliente y se adapta sin reiniciar.
- API keys, voces TTS, colores, tiempos de espera — todo configurable.
- La propia app tiene un editor de config en su UI.
- **Origen:** s71 (~80% de los cambios eran config, no lógica), s72 (POST /api/style, POST /api/config).

### III. API Ultra-Simple

> **Las APIs internas deben ser entendibles en una sola línea, sin lookup de documentación.**

- Máximo 2 palabras por acción (`agent.assign()`, `bus.emit()`, `task.result()`).
- Valores en lenguaje natural ("send", "es-MX", "high"), no códigos numéricos.
- Parámetros con defaults sensatos — el caso común no requiere argumentos.
- Fallbacks automáticos cuando la acción principal no está disponible.
- **Origen:** s71/IDEAS.md (APIs de Android requieren lookup constante), dolor con ACTION_PERFORM_IME_ACTION.

### IV. IPC Universal

> **Cualquier proceso, en cualquier lenguaje, puede ser un agente del sistema.**

- El canal de comunicación es JSON sobre archivos (inbox/outbox).
- También soporta stdin/stdout para procesos hijo, y WebSocket para la UI.
- El formato de mensaje es fijo: `{id, type, agent, timestamp, payload}`.
- No hay SDK obligatorio — solo escribir/leer JSON.
- **Origen:** s63 (IPC vía JSON stdout), s65 (sandbox multi-lenguaje), s72 (agents/inbox, agents/outbox).

### V. Ciclo Corto

> **El feedback loop entre "hago un cambio" y "veo el resultado" debe ser < 10 segundos.**

- Tests automatizados que se ejecutan en segundos, no minutos.
- CDP/Playwright para testing de UI sin intervención humana.
- Watchdog que detecta cambios y re-ejecuta la suite.
- Benchmarks integrados para detectar regresiones de performance.
- **Origen:** s64 (benchmarks), s72 (harness.py + watchdog + CDP), s63 (ciclo de agente).

### VI. Resiliencia por Capas

> **Ninguna operación tiene un solo punto de falla. Siempre hay Plan B, C, D.**

- Cada tarea puede definir una cadena de fallback.
- Timeouts con reintentos y backoff exponencial.
- Si un agente no responde, el Orchestrator ejecuta el fallback.
- Los errores se reportan con contexto completo para diagnóstico inmediato.
- **Origen:** s71 (SpeechRecognizer null, telemetría fallando), s64 (timeouts y fallbacks en API), s72 (proxy LLM caído → script default).

### VII. Commits Trazables

> **Cada cambio atómico se registra con un mensaje que explica el por qué.**

- Un commit = un cambio lógico (feature, fix, refactor, doc).
- El mensaje responde "por qué", no "qué".
- Los tests se ejecutan antes de cada commit (o el watchdog los detecta).
- Cualquier agente puede ver `git diff HEAD~1` para entender qué cambió.
- **Origen:** s72 (watchdog + commits multi-agente), necesidad de revertir cambios de agentes automáticos.

---

## Decisiones Arquitecturales Inmutables

1. **El IPC es sobre archivos JSON.** No sockets, no RPC, no colas de mensajes externas. El filesystem es el bus.
2. **El Orchestrator es un daemon ligero.** No un framework pesado. Su única responsabilidad es coordinar mensajes.
3. **Los agentes son procesos independientes.** No hilos, no corrutinas. Procesos separados con su propio ciclo de vida.
4. **El estado es SQLite.** Nada más. Un archivo, portable, sin servidor.
5. **La UI es web.** HTML+CSS+JS servida por el propio Orchestrator. Sin frameworks pesados (React opcional para apps complejas).
6. **La config es YAML.** Porque se puede comentar y es más legible que JSON para humanos.
7. **El logging es estructurado.** JSON, no texto plano. Para que tanto humanos como IA puedan parsearlo.

---

## Lo Que No Es Este Framework

- ❌ No es un reemplazo de Kubernetes, Docker, o systemd.
- ❌ No es una biblioteca que importas. Es una arquitectura que sigues.
- ❌ No es un lenguaje de programación. Cualquier lenguaje funciona.
- ❌ No es opinativo sobre frameworks web, bases de datos, o estilos de UI.

---

## Cómo Usar Este Manifiesto

1. **Proyectos nuevos:** Clonar `s73-framework/plantilla-proyecto/` como punto de partida.
2. **Proyectos existentes:** Usar los checklists en `s73-framework/checklists/` para verificar cumplimiento.
3. **Agentes nuevos:** Seguir el contrato IPC en `s73-framework/specs/ipc-bus.md`.
4. **Contribuciones:** Cualquier cambio a este manifiesto requiere discusión previa con el usuario.

---

*"La IA no necesita ver — necesita que el sistema le hable."*
