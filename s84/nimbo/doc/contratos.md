# Contratos entre capas — nimbo

> Versión inicial. Estos contratos pueden evolucionar.

## 1. Server → Cliente (inyectado en HTML)

### `window.__NIMBO_RESOURCES__`

```json
["agent", "command", "datasource", "log", "process"]
```

Lista de nombres de modelos. El orden es el de registro. El cliente construye la navegación a partir de esta lista.

Inyectado por `server.py:_serve_static()` en todo `index.html` servido.

---

### `window.__NIMBO_CONFIGS__`

```json
{
  "process": {
    "api": "/api/system/processes",
    "id": "pid",
    "refresh": 5000,
    "noCreate": true,
    "noEdit": true,
    "kill": true,
    "fields": [
      {"name": "pid", "type": "int"},
      {"name": "name", "type": "string"},
      {"name": "cpu_percent", "type": "float", "label": "CPU%"},
      {"name": "memory_percent", "type": "float", "label": "MEM%"},
      {"name": "status", "type": "string"}
    ]
  },
  "log": {
    "refresh": 3000,
    "noCreate": true,
    "noEdit": true,
    "fields": [
      {"name": "source", "type": "string"},
      {"name": "level", "type": "string"},
      {"name": "content", "type": "string"},
      {"name": "time", "type": "string"}
    ]
  },
  "command": {
    "actions": [
      {"label": "▶", "class": "btn-primary", "handlerTemplate": "run"}
    ]
  }
}
```

| Campo | Obligatorio | Default | Descripción |
|---|---|---|---|
| `fields` | sí | — | Schema de la tabla para el CRUD |
| `api` | no | `"/api/{model}"` | Endpoint para listar datos |
| `id` | no | `"id"` | Campo identificador |
| `refresh` | no | — | Intervalo de auto-refresh (ms) |
| `noCreate` | no | `false` | Oculta botón "+ New" |
| `noEdit` | no | `false` | Oculta botón "✎" |
| `kill` | no | — | Muestra botón "✕" (mata recurso vía `/api/system/kill/{id}`) |
| `actions` | no | — | Array de acciones personalizadas (ver sección 1.1) |

Inyectado por `server.py:_serve_static()`.

#### Formato de acciones

```json
{
  "actions": [
    {"label": "▶", "class": "btn-primary", "handlerTemplate": "run"}
  ]
}
```

`handlerTemplate` es una referencia a una función JavaScript predefinida en el cliente.
Actualmente soportadas: `"run"` (ejecuta `POST /api/{model}/run/{id}`).

---

## 2. Cliente → Servidor (API REST)

### CRUD estándar (`@app.model`)

| Método | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| `GET` | `/api/{model}` | — | `[{...}, {...}]` |
| `GET` | `/api/{model}/schema` | — | `{"name":"{model}","fields":[...]}` |
| `GET` | `/api/{model}/{id}` | — | `{...}` |
| `POST` | `/api/{model}` | `{...}` | `{...}` (creado) |
| `PUT` | `/api/{model}/{id}` | `{...}` | `{...}` (actualizado) |
| `DELETE` | `/api/{model}/{id}` | — | `{...}` (eliminado) |

### Acción ejecutable (`@app.run`)

| Método | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| `POST` | `/api/{model}/run/{id}` | — | `{"stdout":"...","stderr":"...","returncode":0}` |

### Monitoreo del sistema (`@app.system`)

| Método | Ruta | Respuesta |
|---|---|---|
| `GET` | `/api/system/processes` | `[{pid, name, cpu_percent, memory_percent, status}, ...]` (top 50) |
| `GET` | `/api/system/resources` | `{"cpu":%, "memory":{...}, "disk":{...}, "net":{...}}` |
| `POST` | `/api/system/kill/{pid}` | `{"killed": pid}` |
| `POST` | `/api/exec` | `{"stdout":"...","stderr":"...","returncode":0}` |

### Utilitarios

| Método | Ruta | Respuesta |
|---|---|---|
| `GET` | `/api/models` | `["agent","command",...]` |
| `GET` | `/api/log/recent` | `[{...}, ...]` (últimos 50) |

---

## 3. Cliente ↔ Servidor (WebSocket)

### Conexión

```
ws://{host}:{port}/ws
```

Donde `{port}` es el puerto configurado (mismo que HTTP para backend nativo,
HTTP+1 para backend `websockets`). El cliente lo obtiene de `window.__NIMBO_WS_PORT__`.

### Mensajes cliente → servidor

```json
{"type": "log", "data": {"level": "info|warn|error", "content": "...", "source": "client"}}
```

### Mensajes servidor → cliente (broadcast)

```json
{"type": "log", "data": {"level": "info|warn|error", "content": "...", "source": "system|client", "time": "HH:MM:SS"}}
```

El cliente escucha con `nimbo.ws.on('log', callback)`.

---

## 4. Rutas del frontend (navegación por hash)

La aplicación es SPA con navegación por hash:

| Hash | Acción |
|---|---|
| `#{model}` | Muestra CRUD del modelo |
| (sin hash) | Primer modelo de `__NIMBO_RESOURCES__` |

El cliente usa `history.replaceState(null, '', '#' + name)` para actualizar la URL
sin causar scroll.

---

## 5. Formato de schema de campos

```json
{
  "name": "nombre_del_campo",
  "type": "string|int|float|bool",
  "label": "Etiqueta visible",       // opcional
  "default": "valor por defecto"     // opcional
}
```

El tipo determina el control HTML generado:
- `string` → `<input type="text">` (o `<textarea>` si el contenido > 80 chars)
- `int` → `<input type="number">`
- `float` → `<input type="number" step="any">`
- `bool` → `<input type="checkbox">`

---

## 6. Glosario de nombres

| Término | Significado |
|---|---|
| `model` | Clase Python decorada con `@app.model` (u otros) |
| `resource` | Nombre en minúscula del modelo (usado en URLs) |
| `schema` | Lista de campos con tipo, label, default |
| `config` | Objeto JSON que configura el comportamiento del CRUD en cliente |
| `action` | Botón personalizado en la tabla (▶ para ejecutar, ✕ para matar) |
