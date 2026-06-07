# Ejemplos mínimos: 2 líneas y ya funciona

> Propósito: mostrar apps funcionales con el mínimo código posible.
> El framework debe hacer que estos ejemplos funcionen sin configuración.

Cada ejemplo es un solo archivo. Sin imports extra. Sin lógica procedural.

**Reglas que siguen estos ejemplos:**

1. Los campos se heredan con Python puro (class inheritance).
2. Los namespaces solo afectan URLs, no heredan modelos.
3. Cada decorador sin parámetros usa defaults detectados del nombre de la clase.

---

## 1. Agenda de contactos

```python
from nimbo import App
app = App(__name__)
@app.model
class Contact:
    name: str
    email: str
    phone: str
app.serve()
```

**Qué genera:** tabla CRUD en `/contact`, UI mobile.

**2 líneas de framework + 3 campos.** Sin configuración.

---

## 2. Monitor de procesos

```python
from nimbo import App
app = App(__name__)
@app.system
class Process: ...
app.serve()
```

**Qué genera:** tabla en `/process` con `pid`, `name`, `cpu_percent`, `memory_percent`, `status`.
Auto-refresh, botón ✕ para matar.

**2 líneas.** El framework detecta "Process" y sabe qué datos del sistema mostrar.

---

## 3. Proxy para LLM

```python
from nimbo import App
app = App(__name__)
@app.proxy
class OpenAI: ...
app.serve()
```

**Qué genera:** proxy en `/openai` que reenvía a OpenAI.
El framework detecta "OpenAI" en el registry y completa upstream, api_key, etc.

**2 líneas.** El nombre de la clase es suficiente.

---

## 4. Blog con usuarios y posts

```python
from nimbo import App
app = App(__name__)

@app.model
class User:
    name: str
    email: str

@app.model
class Post:
    title: str
    body: str
    user_id: int   # FK explícita
app.serve()
```

**Qué genera:** dos tablas CRUD en `/user` y `/post`.

**Relación declarada con campo explícito.** El usuario decide el nombre de la FK.

---

## 5. Blog con versionado

```python
from nimbo import App
app = App(__name__)

# Base
@app.model
class User:
    name: str
    email: str

# Versión 2: hereda campos con Python
@app.model
class UserV2(User):
    phone: str

# Namespace solo para URLs, no hereda modelos
@app.namespace("api")
class Api:
    @app.model
    class User(User): pass     # referencia al User original
    @app.model
    class UserV2(UserV2): pass # referencia al UserV2
app.serve()
```

Rutas: `/user`, `/userv2`, `/api/user`, `/api/userv2`.

**Herencia con Python puro. Namespace solo para URLs.**

---

## 6. Dashboard de sistema completo

```python
from nimbo import App
app = App(__name__)

@app.system
class Process: ...
@app.system
class Mount: ...
@app.system
class Connection: ...
@app.log
class Log: ...
app.serve()
```

**Qué genera:** 4 modelos, cada uno con auto-refresh.

**8 líneas.** Sin configuración. Cada nombre de clase le dice al framework qué datos mostrar.

---

## 7. App completa: proxy + sistema + logs

```python
from nimbo import App
app = App(__name__)

@app.proxy
class OpenAI: ...
@app.system
class Process: ...
@app.log
class Log: ...
app.serve()
```

**Qué genera:** proxy OpenAI, monitoreo de procesos, auditoría de todo.

**6 líneas efectivas.** Sin configuración.

---

## 8. Namespace con versionado de proxy

```python
from nimbo import App
app = App(__name__)

@app.namespace("v1")
class V1:
    @app.proxy
    class OpenAI: ...

@app.namespace("v2")
class V2:
    @app.proxy
    class OpenAI: ...
app.serve()
```

Rutas: `/v1/openai` (proxy v1), `/v2/openai` (proxy v2).

**Cada versión es independiente.** Namespace solo agrupa URLs.

---

## Resumen

| Ejemplo | Líneas | Qué hace |
|---|---|---|
| Contactos | 5 | CRUD completo |
| Procesos | 2 | Monitoreo del sistema |
| Proxy LLM | 2 | Proxy a OpenAI |
| Blog | 8 | Dos tablas relacionadas |
| Blog versionado | 14 | Dos versiones, herencia Python |
| Dashboard | 8 | 4 modelos de sistema |
| App completa | 6 | Proxy + sistema + logs |
| Proxy versionado | 10 | Dos versiones de proxy |

**Ninguno requiere configuración.** El framework detecta todo del nombre de la clase.
