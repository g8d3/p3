# Pendientes y mejoras

> Documento de ideas, bugs y mejoras. No todos serán implementados.

## 1. Depurar backend WebSocket nativo

**Contexto**: el backend nativo (0 deps, implementación manual RFC 6455)
funciona correctamente en pruebas desde Python (envía pong, mantiene conexión),
pero el navegador reporta el círculo rojo (WS no conectado).

**Objetivo**: encontrar el patrón que permita evitar este tipo de errores
en el futuro. No se trata solo de arreglar el bug puntual, sino de
establecer una práctica que prevenga errores similares.

**Preguntas abiertas**:
- ¿Es un error en el frame encoding/decoding?
- ¿Es un problema de timing (onopen vs onclose)?
- ¿Es un error de manejo de conexiones concurrentes?
- ¿El navegador recibe el frame de handshake pero no puede completar la conexión?

**Para implementar**: un test que compare byte a byte las respuestas del
backend nativo vs el de la librería ante el mismo handshake.

**Lección esperada**: implementar protocolos de red desde cero tiene un alto
costo de debugging. La decisión de hacerlo intercambiable (poder cambiar
entre implementación nativa y librería) fue la correcta porque permitió
comparar comportamientos.

## 2. Propagación de errores del cliente al servidor

El framework necesita un mecanismo para que los errores del navegador
lleguen al servidor automáticamente.

**Idea de implementación**:
- Interceptar `window.onerror` y `window.onunhandledrejection`
- Enviar los errores por WebSocket al servidor con un tipo específico
- Alternativa: endpoint `POST /api/log-error`
- El servidor los muestra en consola y los guarda en un modelo `ErrorLog`

## 3. Actualizaciones parciales (no refrescar todo)

Las pantallas de dashboard y procesos reemplazan `innerHTML` completo,
lo que causa:
- Scroll al inicio de la página
- Pérdida de estado de inputs
- Imposibilidad de interactuar durante la actualización

**Solución propuesta**: actualizar solo los valores que cambian:

```javascript
// En vez de:
el.innerHTML = `<div>...completo...</div>`

// Hacer:
document.getElementById('cpu-value').textContent = data.cpu + '%'
document.getElementById('ram-bar').style.width = data.memory.percent + '%'
```

## 4. Barra de navegación desbordada en móvil

La barra de pestañas (nav) se sale del ancho de la pantalla en móvil.

**Solución**: hacer el contenedor scrolleable horizontalmente:

```css
.app-nav {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
```

## 5. Multi-DB: conexiones a múltiples servidores

Ya implementado (`app.db("nombre", "url")` + `@app.model(db="nombre")`).
Pendiente de probar con diferentes motores (SQLite + PostgreSQL simultáneos).

## 6. Browser APIs bridge

`@app.browser_api("dictation")` está definido en el servidor pero aún no
se auto-expone al JavaScript. Falta:
- Que genere automáticamente el endpoint JS
- Que el cliente pueda llamarlo como `nimbo.api.dictation(text)`
- Soporte para: dictado, geolocalización, cámara, micrófono, notificaciones

## 7. Autenticación y autorización

No hay sistema de usuarios ni tokens. Para una app de administración
del servidor, es necesario al menos un mecanismo básico.

## 8. Template de app `agentui`

La app de ejemplo (`apps/agentui/`) debería ser un template que se pueda
clonar para empezar proyectos nuevos rápidamente.

## 9. Comando `nimbo create`

Un comando CLI que cree la estructura de un proyecto nuevo:

```bash
python -m nimbo create mi-app
```
