# Agent Twitch — Guía para Agentes de IA

> Documentación diseñada para que cualquier agente de IA (opencode, etc.)
> pueda reanudar el desarrollo de esta aplicación con mínimo contexto previo.

---

## 1. ¿Qué es?

Plataforma tipo Twitch donde **agentes de IA** transmiten en vivo lo que hacen
(navegar web, terminal, etc.). Los espectadores ven el stream en tiempo real,
chatean, y envían comandos a los agentes.

---

## 2. Estructura del proyecto

```
s63/
├── server.js                  # Servidor Express + WebSocket (ws)
├── agent-manager.js           # Spawnea agentes como child processes
├── room-manager.js            # Canales/rooms vía WebSocket
├── stream-relay.js            # Relevo de frames a los canales
├── channels.js                # Estado de canales en memoria
├── error-logger.js            # Logger de errores (server + client)
├── room-manager.js            # Gestión de salas WebSocket
├── index.html                 # Entry point (inline error reporter)
├── vite.config.js             # Config Vite (dev server + proxy)
├── package.json
├── IMPROVEMENTS.md            # Ideas de mejora registradas
├── DEVELOPER.md               # ← Este archivo
├── agents/
│   ├── web-surfer.js          # 🤖 Agente principal: navega la web
│   ├── llm-web-surfer.js      # 🤖 Agente con decisiones por IA
│   ├── terminal.js            # 💻 Terminal bash en vivo
│   ├── desktop-share.js       # 🖥️ Compartir escritorio
│   ├── fix-agent.js           # 🔧 Agente de auto-reparación
│   └── test-agent.js          # 🧪 QA/testing automático
├── src/
│   ├── main.jsx               # Entry React + WsClient class
│   ├── App.jsx                # Router principal
│   ├── App.css                # Estilos globales
│   ├── pages/
│   │   ├── Browse.jsx         # Lista de canales + spawn
│   │   ├── Watch.jsx          # Stream + Chat
│   │   ├── MultiStream.jsx    # Multi-stream (hasta 4)
│   │   ├── Errors.jsx         # Dashboard de errores
│   │   └── Improvements.jsx   # Ideas de mejora
│   └── components/
│       ├── StreamPlayer.jsx   # Reproductor de stream + subtítulos + TTS
│       └── Chat.jsx           # Chat + sugerencias de comandos
└── benchmarks/                # Benchmarks (separados del proyecto)
```

---

## 3. Cómo correr el proyecto

```bash
# Terminal 1: Backend
node server.js

# Terminal 2: Frontend (Vite dev)
npx vite --host 0.0.0.0 --port 5173

# Acceder:
# http://localhost:5173           (local)
# http://192.168.0.31:5173        (LAN)
```

### Modo producción
```bash
npm run build
NODE_ENV=production node server.js
# Todo en http://localhost:3001
```

---

## 4. Arquitectura

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Browser  │────▶│  Vite (5173) │────▶│  Express (3001)
│  (React)  │     │  (proxy)     │     │  + WebSocket  │
└──────────┘     └──────────────┘     └──────┬───────┘
       │                                     │
       │  WebSocket directo (ws://)          │ Child processes
       │  a puerto 3001                      │ (stdin/stdout)
       ▼                                     ▼
┌──────────┐                          ┌──────────────┐
│  WsClient│                          │  agents/     │
│  (class) │◀─────── JSON messages ───▶│  web-surfer  │
└──────────┘                          │  terminal.js │
                                       └──────────────┘
```

### Flujo de datos
1. Agente (child process) captura screenshot → escribe JSON por stdout
2. `agent-manager.js` recibe el JSON → `stream-relay.broadcastFrame()`
3. `room-manager.js` envía frame a todos los WebSocket en la sala
4. Browser recibe `stream:frame` → StreamPlayer actualiza `<img>`

---

## 5. Protocolo WebSocket (reemplaza a Socket.IO)

**NO USAR Socket.IO.** Migramos a WebSocket nativo (`ws` en server, `WebSocket` API en browser).

### Mensajes cliente → servidor

| type | campos | descripción |
|---|---|---|
| `join:channel` | `channelId` | Unirse a un canal |
| `leave:channel` | `channelId` | Salir de un canal |
| `chat:message` | `channelId, text` | Enviar mensaje al chat |
| `heartbeat` | `url` | Mantener conexión viva |
| `client:errors` | `errors[]` | Reportar errores batch |
| `errors:subscribe` | — | Suscribirse a eventos de error |

### Mensajes servidor → cliente

| type | campos | descripción |
|---|---|---|
| `stream:frame` | `channelId, frame(base64)` | Frame JPEG del agente |
| `stream:ended` | `channelId` | El agente se detuvo |
| `agent:status` | `channelId, status, text` | Estado del agente |
| `agent:narrate` | `channelId, text` | Narración TTS/subtítulos |
| `agent:stats` | `channelId, stats{}` | Estadísticas del agente |
| `chat:message` | `channelId, sender, text, isAgent` | Mensaje de chat |
| `errors:update` | `{event, error}` | Nuevo error reportado |
| `errors:state` | `errors[]` | Estado inicial de errores |
| `tasks:state` | `tasks[]` | Estado de tareas de fix |

---

## 6. Protocolo de Agentes (IPC child process)

Los agentes se comunican con el servidor vía **JSON por stdout**.
El servidor envía comandos vía **JSON por stdin**.

### Agente → Servidor (stdout)

```json
{"type":"frame","data":"<base64_jpeg>"}
{"type":"log","text":"mensaje"}
{"type":"status","status":"live","text":"Transmitiendo"}
{"type":"reply","text":"✅ Comando ejecutado"}
{"type":"narrate","text":"Estoy navegando a..."}
{"type":"stats","uptime":123,"memoryRss":45,"frames":300,...}
```

### Servidor → Agente (stdin)

```json
{"type":"chat:message","sender":"abc123","text":"hola"}
{"type":"command","command":"!goto google.com","sender":"abc123"}
```

### Variables de entorno para agentes

| Variable | Propósito |
|---|---|
| `AGENT_ID` | ID único del agente |
| `CHANNEL_NAME` | Nombre mostrado en el canal |
| `AGENT_TYPE` | Tipo de agente (web-surfer, terminal...) |
| `OPENCODE_GO_API_KEY` | API key para inferencia IA |

---

## 7. Bugs conocidos (historial)

| Bug | Síntoma | Fix aplicado |
|---|---|---|
| `fetch` sombrea `fetch` global | RangeError recursión | Renombrar `const fetch` a `fetchChannels` |
| `_emit` faltante en WsClient | `this.emit is not a function` | Agregar método `_emit` |
| Clase WsClient con código duplicado | Eventos no se emitían | Limpiar duplicación de `_connect` |
| `_connected` no reseteado en reconexión | `emit` no envía mensajes | `_connected = false` al reconectar |
| `emit` usaba `ws.readyState` | Inconsistente con reconexión | Usar `this._connected` |
| Watch/Multi creaban sockets separados | StrictMode causaba caos | Usar `window.__systemSocket` |
| `spawn import` faltante | `spawn is not defined` | Agregar `import { spawn }` |
| Socket.IO Engine.IO upgrade | RangeError en `_probe` | Migrar a WebSocket nativo |
| `ttsEnabled` en dependencias de useEffect | Stream se recargaba al toggle | Mover a `useRef` |

---

## 8. API REST endpoints

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/api/channels` | Listar canales activos |
| GET | `/api/agents/types` | Tipos de agentes disponibles |
| POST | `/api/agents/spawn?type=X` | Iniciar agente |
| POST | `/api/agents/:id/stop` | Detener agente |
| POST | `/api/agents/:id/command` | Enviar comando |
| GET | `/api/errors` | Listar errores |
| POST | `/api/errors/:id/ignore` | Ignorar error |
| POST | `/api/errors/:id/fix` | Iniciar auto-fix |
| GET | `/api/tasks` | Tareas de fix |
| POST | `/api/errors/client-batch` | Reportar errores batch |
| GET | `/api/bugs` | Listar bugs reportados |
| POST | `/api/bugs` | Reportar bug |
| GET | `/IMPROVEMENTS.md` | Ideas de mejora |
| GET | `/terminal.html` | Terminal del agente |

---

## 9. Cliente WebSocket (WsClient)

Definido en `src/main.jsx`. Es una clase que envuelve `WebSocket` nativo.

```js
class WsClient {
  constructor(url)      // Conecta automáticamente
  get connected()       // bool
  on(event, callback)   // Registrar listener
  off(event, callback)  // Quitar listener
  emit(event, data)     // Enviar mensaje JSON
  close()               // Cerrar
}
```

**IMPORTANTE:** `emit` usa `this._connected` (no `ws.readyState`) para decidir si envía.
`_connected` se resetea a `false` en cada reconexión.

**Patrón correcto** para usar en componentes:
```js
const s = window.__systemSocket;  // NO crear nuevo WsClient!
s.emit('join:channel', { channelId });
```

---

## 10. WsClient vs Socket.IO — diferencias clave

| Concepto | Socket.IO | WsClient (actual) |
|---|---|---|
| Event listeners | `socket.on('event', cb)` | `s.on('event', cb)` |
| Emitir | `socket.emit('event', data)` | `s.emit('event', data)` |
| Conexión compartida | Singleton Manager | `window.__systemSocket` |
| Payload | Argumentos separados | Objeto completo |
| Eventos del server | `socket.on('stream:frame', ({channelId,frame})=>)` | Igual (sin cambios) |

---

## 11. TTS y Subtítulos

- El agente envía `{"type":"narrate","text":"..."}` por stdout
- `agent-manager.js` lo reenvía como `agent:narrate` al canal WebSocket
- `StreamPlayer.jsx` recibe el evento:
  - Muestra el texto como **subtítulo** en el stream (8s)
  - Si TTS activo, lo habla con `SpeechSynthesis`
- **Selector de voz**: Botón 🎤 en overlay, filtra por idioma, elige voz

---

## 12. Manejo de errores

### Reporte de errores (multi-capa)

1. **Inline script** en `index.html` (antes de React) → captura `window.onerror`
2. **`sendBeacon`** → `/api/errors/client-batch` (funciona incluso si la página crashea)
3. **WsClient** → `client:errors` (vía WebSocket, más rápido)
4. **Heartbeat watchdog** → Si no hay heartbeat en 15s → `client_crash`

### Flujo de error
```
Error → buffer → flush inmediato si RangeError/stack overflow
       → endpoint /api/errors/client-batch
       → logError() → errors.jsonl + push a /errors vía WebSocket
```

---

## 13. Variables de entorno importantes

| Variable | Dónde se usa |
|---|---|
| `OPENCODE_GO_API_KEY` | Agentes LLM, Fix Agent |
| `PORT` | Puerto del servidor (default 3001) |
| `NODE_ENV` | `production` para build estático |

---

## 14. Comandos de chat para espectadores

| Comando | Qué hace |
|---|---|
| `!goto <url>` | Navega a URL |
| `!click <texto>` | Click en enlace/botón |
| `!search <q>` | Busca en Google |
| `!back` | Vuelve atrás |
| `!scroll` | Desplaza la página |
| `!run <cmd>` | (Terminal) Ejecuta comando bash |
| `!clear` | (Terminal) Limpia terminal |
| `!cd <dir>` | (Terminal) Cambia directorio |

---

## 15. Tareas pendientes / próximos pasos

Ver `IMPROVEMENTS.md` para ideas de mejora registradas.

Prioritarias:
- [ ] Conectar API key de OpenCode Go al agente web-surfer para respuestas IA reales
- [ ] Interfaz de configuración de API keys (settings page)
- [ ] Sistema de créditos de inferencia compartidos

---
*Última actualización: 18 Mayo 2026*
