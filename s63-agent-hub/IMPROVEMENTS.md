# 🚀 Agent Twitch — Lista de Mejoras Potenciales

> Ideas registradas para futuras iteraciones.
> No están en desarrollo activo a menos que se decida lo contrario.

---

## 1. Agentes en Rust (bajo consumo de memoria)

**Problema:** Cada agente Node.js + Chromium headless consume ~200-500MB RAM.
Con 15GB de RAM, podemos correr ~3-4 agentes simultáneos.

**Idea:** Reescribir los agentes en Rust para:
- Usar `headless_chrome` (crate) o `chromiumoxide` en vez de Playwright/Node
- Reducir el overhead del runtime de Node.js (~30-50MB por proceso)
- Posibilidad de compartir un solo Chromium entre múltiples agentes
- Loop de captura más eficiente (sin GC de JS)

**Estimación:** Podría bajar el consumo a ~50-100MB por agente,
permitiendo 10-15 agentes simultáneos.

**Riesgos:**
- Trabajo arduo de reescritura
- Mayor complejidad de desarrollo
- Integración con el sistema de IPC actual (JSON sobre stdin/stdout)
- Menor flexibilidad para scripting rápido

**Estado:** 💡 Idea registrada. No hay plan de implementación inmediato.

---

## 2. Versionamiento de fixes (sandbox + rollback)

**Problema:** Cuando el Fix Agent aplica cambios automáticos,
no hay manera segura de deshacerlos si algo sale mal.

**Idea:** Sistema de versionamiento para la aplicación:
- Snapshots del código antes de aplicar un fix (git commit automático)
- Sandbox para probar fixes en un entorno aislado antes de aplicar
- Rollback automático si un fix causa errores
- Diferentes "ramas" o versiones: `stable` (sin fixes), `fixes-pendientes`, `produccion`

**Componentes necesarios:**
- Git integration (commits automáticos pre-fix)
- Entorno de pruebas sandboxeado (Docker/container)
- Sistema de health checks post-fix
- Interfaz para comparar versiones y hacer rollback

**Riesgos:**
- Complejidad significativa
- Docker/K8s requerido para sandboxing real
- Almacenamiento de snapshots

**Estado:** 💡 Idea registrada. No hay plan de implementación inmediato.

---

## 3. WebRTC en vez de MJPEG (streaming más fluido)

**Problema:** El streaming actual viaja como JPEGs base64 por WebSocket (~5fps).
Es simple pero no es video real.

**Idea:** Usar WebRTC para streaming de video real:
- Captura de pantalla → FFmpeg → WebRTC
- Soporte para audio (micrófono del agente)
- Menor latencia y mayor framerate (30fps+)
- Menor ancho de banda (códec video vs JPEG)

**Riesgos:**
- Complejidad de signaling STUN/TURN
- Necesita servidor TURN para NAT traversal
- Más complejo de debuggear

**Estado:** 💡 Idea registrada.

---

## 4. Agente tipo "IDE" (transmitir código en vivo)

**Idea:** Un agente que abre VSCode/Cursor en modo headless
y transmite sesiones de coding en vivo. Los viewers pueden sugerir
cambios vía chat y el agente los implementa.

**Estado:** 💡 Idea registrada.

---

## 5. Multi-idioma para agentes (Python, Rust, Go)

**Idea:** Poder escribir agentes en cualquier lenguaje,
no solo Node.js. El sistema de IPC (JSON sobre stdin/stdout)
ya es lenguaje-agnóstico, pero faltan:
- Scripts de bootstrap para cada lenguaje
- SDK/librerías cliente para la comunicación
- Ejemplos y templates

**Estado:** 💡 Idea registrada.

---

## 6. Página web de mejoras (roadmap visible en la app)

**Problema:** Las ideas de mejora están solo en un archivo Markdown.
No hay visibilidad desde la aplicación web.

**Solución:** Página `/improvements` que muestra IMPROVEMENTS.md
formateado con tarjetas por cada idea, accesible desde el nav.

**Estado:** ✅ Implementado.

---

## 7. Streaming eficiente (arquitectura estilo videojuego)

**Problema:** Actualmente enviamos screenshots JPEG (~80KB cada uno, ~5fps)
por cada agente. Es ancho de banda ineficiente.

**Idea:** Arquitectura "thin server, rich client" como en los videojuegos:
- El servidor envía la **mínima información posible** (eventos, coordenadas, texto, DOM changes)
- El cliente **renderiza localmente** la interfaz del agente
- Los frames comprimidos son solo un respaldo / thumbnail
- Usar diff de frames (solo enviar cambios) para reducir tráfico

**Estado:** 💡 Idea registrada.

---

## 8. Red descentralizada de agentes

**Idea:** Que los agentes no dependan de un solo servidor central.
- Los agentes se comunican entre sí vía P2P (WebRTC)
- Cualquier nodo puede ser servidor y cliente
- Los espectadores se conectan al agente más cercano (menor latencia)
- Inspirado en: BitTorrent, IPFS, ActivityPub (Fediverso)

**Estado:** 💡 Idea registrada.

---

## 9. Integración con herramientas de IA externas

**Idea:** Permitir que agentes externos (opencode, Cline, Aider, etc.)
tomen tareas del sistema:
- `GET /api/tasks` — agente externo ve tareas pendientes
- `POST /api/tasks/:id/claim` — toma una tarea
- `POST /api/tasks/:id/complete` — reporta resultado
- El agente externo edita el código y reporta el fix

**Estado:** 💡 Idea registrada.

---

## 10. Roles y permisos en el sistema de errores

**Problema:** Actualmente todos los usuarios ven todos los errores.
Un administrador necesita ver todo, un usuario normal solo sus propios errores.

**Idea:** Sistema de roles/grupos/permisos:
- Admin: ve todos los errores del sistema
- Usuario normal: ve solo errores de sus canales/sesiones
- Los errores se etiquetan con `channelId` y `userId`
- La `/errors` filtra según el rol del usuario autenticado

**Estado:** 💡 Idea registrada. Requiere autenticación y sesiones de usuario.

---

## 11. Tabla de errores con operaciones tipo SQL

**Mejora:** La página `/errors` debería permitir:
- Paginación (✅ implementado)
- Ordenar por fecha, severidad, tipo, estado
- Filtrar por múltiples criterios simultáneamente
- Agrupar por tipo o canal
- Exportar a CSV/JSON

**Estado:** ⚠️ Paginación básica implementada. Ordenamiento y filtros avanzados pendientes.

---

## 12. DVR del stream (grabar últimos N segundos)

**Idea:** Permitir al usuario guardar/ver los últimos N segundos de cualquier stream,
como un DVR (Digital Video Recorder):
- El servidor almacena en búfer los últimos N segundos de frames
- El usuario pausa el stream y vuelve atrás
- Al reanudar, salta al vivo
- Configurable por el usuario (5s, 10s, 30s...)

**Estado:** 💡 Idea registrada. Solo UI/local por ahora, sin backend.
