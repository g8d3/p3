# Versionado de API con namespaces

## Propósito

Analizar cómo un usuario que ya tiene modelos funcionando puede
versionarlos sin romper lo existente y con el mínimo código posible.

## Caso base

```python
# app actual, funcionando
@app.model class User:
    name: str
    email: str

@app.model class Post:
    title: str
    body: str
```

Rutas: `/user`, `/post`

---

## 1. Envolver en namespace

```python
@app.namespace("api")
class Api:
    @app.model class User(User): ...   # hereda de User en raíz
    @app.model class Post(Post): ...   # hereda de Post en raíz
```

Rutas: `/api/user`, `/api/post`. Las rutas viejas `/user`, `/post` pueden seguir o no.

**Hueco:** el usuario debe reescribir las clases dentro de `Api` aunque solo haya cambiado el namespace. ¿Se puede evitar?

---

## 2. Namespace vacío hereda del padre

Si un namespace está vacío, hereda los modelos del namespace padre:

```python
@app.namespace("api")
class Api:
    @app.model class User: ...
    @app.model class Post: ...

    @app.namespace       # hereda User y Post de Api automáticamente
    class V1: ...
```

Rutas: `/api/user`, `/api/post`, `/api/v1/user`, `/api/v1/post`.

**Hueco:** los modelos `User` y `Post` existen tanto en `/api/` como en `/api/v1/`.
¿Son los mismos datos o se duplican? ¿Comparten la misma tabla DB?

---

## 3. Namespace hereda de otro namespace (no del padre directo)

```python
@app.namespace("api")
class Api:
    @app.model class User: ...

@app.namespace("v2")
class V2(Api):    # hereda User de Api
    pass
```

Rutas: `/api/user`, `/v2/user`.

**Hueco:** `V2` hereda de `Api` pero no está definido DENTRO de `Api`. El namespace
de `V2` es `/v2/`, no `/api/v2/`. La herencia es de contenido, no de ruta.

---

## 4. Versión que extiende modelos

```python
@app.namespace("api")
class Api:
    @app.model class User: ...

    class V1:     # sin @app.namespace — hereda contenido de Api
        @app.model class User(Api.User):
            phone: str
```

**Hueco 1 — herencia y dependencia cíclica:** `V1` está definido DENTRO de `Api`.
Si `V1` heredara de `Api`, crearía una dependencia circular (Api → V1 → Api).

**Hueco 2 — clase sin `@app.namespace`:** si una clase no tiene `@app.namespace`,
¿hereda el namespace del padre? ¿O no genera rutas?

**Hueco 3 — orden de definición:** `V1` se define antes de que `Api.User` exista?
En Python, el cuerpo de la clase se ejecuta de arriba a abajo. Si `V1` usa `Api.User`,
`Api.User` debe definirse antes que `V1`.

---

## 5. Namespace anidado sin parámetros

```python
@app.namespace("api")
class Api:
    @app.model class User: ...

    @app.namespace
    class V1:        # @app.namespace sin args → nombre de clase = "v1"
        @app.model
        class User(Api.User):
            phone: str
```

Ruta: `/api/v1/user` con teléfono, `/api/user` sin teléfono.

Ambos coexisten. Los clientes viejos usan `/api/user`, los nuevos `/api/v1/user`.

---

## 6. Caso completo: migración gradual

```python
# 1. Modelos originales en raíz
@app.model class User: ...
@app.model class Post: ...

# 2. Se envuelven en namespace api
@app.namespace("api")
class Api:
    @app.namespace
    class V1: ...

# 3. V2 agrega campos nuevos
@app.namespace("api/v2")
class V2(Api.V1):          # hereda todo de V1
    @app.model class User(Api.V1.User):
        phone: str
```

Rutas:
- `/api/v1/user`, `/api/v1/post` — originales, funcionando
- `/api/v2/user` — con teléfono
- `/api/v2/post` — igual que V1

---

## Huecos detectados

| # | Hueco | Pregunta |
|---|---|---|
| 1 | Namespace vacío hereda modelos del padre | ¿Cómo se implementa sin `__init_subclass__` o metaclass? |
| 2 | Namespace hereda de otro namespace | ¿Herencia de clases Python alcanza o necesitamos algo más? |
| 3 | Namespace sin `@app.namespace` | ¿No genera ruta? ¿Hereda del padre? |
| 4 | Dependencia cíclica | Namespace que hereda del padre que lo contiene |
| 5 | Modelos compartidos vs duplicados | `/api/user` y `/api/v1/user`: ¿misma tabla DB o distintas? |
| 6 | Migración de rutas viejas | ¿Los endpoints originales `/user` se eliminan o siguen? |
