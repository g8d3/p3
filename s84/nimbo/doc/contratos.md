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
    "api": "/api/process",
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
| `kill` | no | — | Muestra botón "✕" (mata recurso vía `DELETE /api/{model}/{id}`) |
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

Toda la API sigue un solo estándar. Un modelo es un modelo, tenga respaldo en DB o no.

### CRUD universal

| Método | Ruta | Cuerpo | Respuesta | Uso |
|---|---|---|---|---|
| `GET` | `/api/{model}` | — | `[{...}, ...]` | Listar todos |
| `GET` | `/api/{model}/schema` | — | `{"name":"{model}","fields":[...]}` | Schema del modelo |
| `GET` | `/api/{model}/{id}` | — | `{...}` | Leer uno |
| `POST` | `/api/{model}` | `{...}` | `{...}` | Crear |
| `PUT` | `/api/{model}/{id}` | `{...}` | `{...}` | Actualizar |
| `DELETE` | `/api/{model}/{id}` | — | `{...}` | Borrar (o matar, si es proceso) |
| `POST` | `/api/{model}/run/{id}` | — | `{"stdout":"...","stderr":"...","returncode":0}` | Ejecutar comando |

No hay rutas especiales fuera de este patrón. Un proceso se lista con `GET /api/process`,
se mata con `DELETE /api/process/{pid}`, etc.

### Modelos virtuales (sin DB)

Los modelos declarados con `@app.system` (ej: `process`) también siguen el mismo patrón.
La única diferencia es que algunas operaciones no aplican:
- `POST /api/{model}` → 405 si `noCreate`
- `PUT /api/{model}/{id}` → 405 si `noEdit`

### Query parameters estándar

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `?limit=N` | `?limit=50` | Máximo de registros a devolver |
| `?offset=N` | `?offset=100` | Desplazamiento para paginación |
| `?sort=campo` | `?sort=-created_at` | Ordenar (prefijo `-` para descendente) |
| `?{campo}={valor}` | `?status=running` | Filtrar por valor exacto |

---

## 3. Cliente ↔ Servidor (WebSocket)

### Conexión

```
ws://{host}:{port}/ws
```

### Formato universal de mensajes

Todos los mensajes WebSocket siguen el mismo formato:

```json
{"type": "{tipo}", "data": {...}}
```

### Tipos de mensajes

| `type` | Dirección | Descripción | Ejemplo `data` |
|---|---|---|---|
| `log` | ambas | Evento de log | `{"level":"info","content":"...","source":"system","time":"HH:MM:SS"}` |
| `crud` | servidor → cliente | Notificación de cambio CRUD | `{"model":"agent","action":"create","id":5,"data":{...}}` |
| `model:{model}` | servidor → cliente | Actualización de datos vivos | `{"model":"process","data":[{...},{...}]}` |
| `system` | servidor → cliente | Stats del sistema | `{"cpu":45,"memory":{...}}` |
| `reload` | servidor → cliente | El servidor se reinició | `{"version":2}` |

### Uso

```javascript
// Cliente: escuchar cualquier tipo
nimbo.ws.on('log', msg => { ... });
nimbo.ws.on('crud', msg => { ... });
nimbo.ws.on('model:process', msg => { ... });
// O escuchar todo
nimbo.ws.on('message', msg => { ... });
```

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
  "label": "Etiqueta visible",
  "default": "valor por defecto"
}
```

El tipo determina el control HTML generado:
- `string` → `<input type="text">` (o `<textarea>` si el contenido > 80 chars)
- `int` → `<input type="number">`
- `float` → `<input type="number" step="any">`
- `bool` → `<input type="checkbox">`

---

## 6. Glosario

| Término | Significado |
|---|---|
| `model` | Cualquier recurso declarado con un decorador (`@app.model`, `@app.system`, `@app.log`) |
| `resource` | Sinónimo de modelo. El nombre en minúscula usado en URLs |
| `schema` | Lista de campos con tipo, label, default |
| `config` | Objeto JSON que configura el comportamiento del CRUD en cliente |
| `action` | Botón personalizado en la tabla (▶ para ejecutar, ✕ para matar) |
