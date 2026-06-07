# Ejemplos mínimos: 2 líneas y ya funciona

> Propósito: encontrar huecos en el diseño. Si un ejemplo no es posible
> o es muy verboso, algo falta en el framework.

Cada ejemplo es una app completa que ocupa un solo archivo.
Sin configuración. Sin imports extra. Sin lógica procedural.

---

## 1. Agenda de contactos

```python
from nimbo import App
app = App(__name__)
@app.model
class Contact: ...
app.serve()
```

**Qué genera:** tabla `contact` con campos `name`, `description`, CRUD completo, UI mobile.

**Hueco:** los campos por defecto de `@app.model` son genéricos (`name`, `description`).
Para una agenda de contactos ideales serían `name`, `email`, `phone`.
→ El decorador debería detectar el nombre de la clase y elegir defaults?
  O el usuario SIEMPRE agrega campos porque cada modelo es distinto?

---

## 2. Monitor de procesos

```python
from nimbo import App
app = App(__name__)
@app.system
class Process: ...
app.serve()
```

**Qué genera:** tabla `process` con `pid`, `name`, `cpu_percent`, `memory_percent`, `status`.
Auto-refresh cada 5s, botón ✕ para matar.

**¿Funciona?** Sí — `@app.system` sin parámetros usa defaults.

---

## 3. Proxy para LLM

```python
from nimbo import App
app = App(__name__)
@app.proxy
class OpenAI: ...
app.serve()
```

**Qué genera:** proxy en `http://localhost:8080/proxy/openai/` que reenvía a OpenAI.
Modelo `openai` con `agent_id`, `status`, `pid`, `cpu`, etc.
Modelos anidados `request` y `token-usage` para auditoría.

**Hueco:** `upstream` default no existe. El decorador no sabe a qué URL reenviar.
→ `@app.proxy` sin upstream debería ser un proxy local (solo registra, no reenvía)
  o generar un error claro.

---

## 4. Blog con usuarios y posts

```python
from nimbo import App
app = App(__name__)

@app.model
class User: ...

@app.model
class Post: ...

app.serve()
```

**Qué genera:** dos tablas CRUD independientes. Sin relación entre ellas.

**Hueco:** `Post` debería tener `user_id` para relacionarse con `User`.
Pero el decorador no sabe que `Post` pertenece a `User`.
→ ¿Cómo se declara una relación? ¿`@app.model(belongs_to="user")`?
  ¿O el usuario debe agregar `user_id: int` explícitamente?

---

## 5. Proxy con agentes y requests

```python
from nimbo import App
app = App(__name__)
@app.namespace("agentes")
@app.proxy
class Proxy:
    @app.model
    class Agent: ...

    @app.model
    class Request: ...
app.serve()
```

**Qué genera:**
- `GET /agentes/proxy` — lista proxies (solo uno)
- `GET /agentes/proxy/agent` — lista agentes
- `GET /agentes/proxy/request` — lista requests

**Hueco:** `Agent` dentro de `Proxy` hereda el namespace `/agentes/`.
Pero `@app.model` dentro de `@app.proxy` sin nombre propio usa el nombre de la clase (`agent`).
La ruta queda `/agentes/proxy/agent`. ¿Es clara o debería ser `/agentes/agent`?

---

## 6. Dashboard de sistema completo

```python
from nimbo import App
app = App(__name__)

@app.system
class Process: ...

@app.system("mounts")
class Mount: ...

@app.system("connections")
class Connection: ...

@app.log
class Log: ...

app.serve()
```

**Qué genera:** 4 modelos: procesos, monturas, conexiones de red, logs de auditoría.
Todo auto-refresh, todo visible en la UI.

**¿Funciona?** Sí, si cada `@app.system` con nombre genera su propio endpoint de datos.
El sistema necesita proveer endpoints para `mounts` y `connections`.

**Hueco:** los endpoints de datos para `mounts` y `connections` no existen en `system.py`.
→ Cada `@app.system` con nombre debería mapearse a un endpoint del sistema automáticamente.
  O el framework debe permitir registrar nuevos endpoints de sistema fácilmente.

---

## 7. Proxy + logs + monitoreo (app completa)

```python
from nimbo import App
app = App(__name__)

@app.proxy
class LLM: ...

@app.system
class Process: ...

@app.log
class Log: ...

app.serve()
```

**Qué genera:** proxy para LLM, monitoreo de procesos, auditoría de todo.
Tres modelos en 6 líneas efectivas. Sin configuración.

**¿Funciona?** Depende de cuánto default tenga cada decorador.

---

## Resumen de huecos detectados

| # | Hueco | Severidad |
|---|---|---|
| 1 | `@app.model` sin campos: ¿qué campos por defecto? | Media |
| 2 | `@app.model` sin relación entre modelos | Alta |
| 3 | `@app.proxy` sin `upstream`: ¿error o proxy local? | Baja |
| 4 | Endpoints de sistema para modelos nuevos (mounts, connections) | Alta |
| 5 | Claridad de rutas en modelos anidados | Media |
