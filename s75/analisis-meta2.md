# Análisis de `input-s74-meta.txt` (3836 líneas, sesión MetaGPT → s74)

---

## 1) Decisiones de Arquitectura

| Decisión | Contexto / Evolución |
|---|---|
| **Probar MetaGPT como base multi-agente** | Arranque de la sesión. Se clona `FoundationAgents/MetaGPT` y se intenta poner a correr. |
| **Descartar MetaGPT** | "MetaGPT está diseñado para generar código desde cero en una sola pasada, no para iterar/mejorar continuamente." No sirve para el loop de mejora continua. |
| **s73-framework como posible base** | Se descubre que ya existe `s73-framework/` con orquestador, WebSocket, SQLite, UI. Se intenta construir encima. |
| **s73-framework descartado** | El usuario objeta: "asumiste que lo que está en el folder 73 funciona sin probarlo". Se abandona por dependencias no verificadas. |
| **Sistema standalone (s74)** | Se reconstruye todo como sistema independiente sin depender de s73-framework. `server.py` + `agent.py` + `web/` |
| **Carpetas como versiones** (`versions/v001`, `v002`...) | En vez de git worktrees o branches. Cada versión es un directorio con su propio stack. |
| **Symlink para versión activa** (`versions/live → v002`) | Cambio instantáneo entre versiones sin reiniciar el servidor. |
| **Hot-reload del orquestador** | `touch server.py` gatilla reinicio automático (vía `watchdog`). Como Flask --reload. |
| **Rutas compartibles** (`/v003/tasks`, `/v003/benchmarks`) | Cada ruta representa estado de la aplicación. Compartible por URL. |
| **Unificación UI: gestión + app en la misma página** | El toolbar de gestión (tasks, versions, benchmarks, tags) y el contenido de la app viven en la misma URL. |
| **Versión base inmutable** | `versions/base/` siempre disponible con funcionalidades esenciales. Las versiones hijas se crean copiando desde la activa. |
| **Sistema de tags many-to-many** | Tags con relaciones entre tags (tabla `tag_relations`) para taxonomía flexible. |
| **AI auto-tagging** | El LLM genera tags automáticamente basados en el diff de cada versión (ej: "UI", "bugfix", "feature"). |
| **Arquitectura v2 (reinicio total)** | Se mueve todo lo construido a `v1/` y se empieza desde cero en `v2/` con un orquestador mínimo y `LEARNINGS.md`. |
| **Cada versión contiene su stack completo** | UI, lógica, todo dentro del directorio de la versión. |
| **Datos globales compartidos** | Tasks, benchmarks, leaderboard son globales — no versionados. |

---

## 2) Problemas Técnicos

| Problema | Causa | Solución/Estado |
|---|---|---|
| **API keys en el directorio** | El usuario no quería exponer llaves en el código | Se usaron env vars `OPENCODE_GO_*` + wrapper script |
| **`pip` no en PATH** | Sistema Debian sin pip global | → **uv** (resuelve de raíz) |
| **PEP 668 (Debian bloquea pip system-wide)** | Protección de Debian | uv no tiene esta restricción |
| **`ensurepip` ausente** | Paquete python3-venv no instalado | uv crea venvs sin ensurepip |
| **`faiss-cpu==1.7.4` sin wheels para Python ≥3.11** | Dependencia antigua de MetaGPT | Se editó `requirements.txt` para usar `faiss-cpu>=1.7.4,<2` |
| **Typer + click incompatible** | `click>=8.1` rompe typer 0.9.0: "Secondary flag is not valid for non-boolean flag" | Downgrade a `click==8.0.4` |
| **github.com inaccesible** | Red sin internet | Se clonó MetaGPT antes de perder conectividad |
| **curl/ssh bloqueados** | Restricciones de seguridad de la tool | Se usó Python `urllib` para testear APIs |
| **s73-framework no probado** | Se asumió que funcionaba | El usuario lo señaló como error |
| **sleep para polling de agente** | Se esperaba con `sleep 60` a que el LLM responda | El usuario exige evento-driven, no polling |
| **LLM responde vacío con `max_tokens=10`** | deepseek-v4-flash usaba todos los tokens en reasoning | Se aumentó `max_tokens` a 100+ |
| **Formato de respuesta inconsistente** | `reasoning_content` vs `reasoning` según el modelo | Se unificó el parser para ambos campos |
| **LLM genera código Flask en vez de asyncio** | El modelo no conocía la arquitectura real | Se mejoró el prompt con contexto del código existente |
| **LLM reescribe archivo entero en vez de editar** | Find/replace fallaba porque el texto no coincidía | Se cambió a estrategia de reemplazo de líneas exactas + diff |
| **Puerto ocupado (Address already in use)** | Múltiples inicios sin matar proceso anterior | Se añadió `fuser -k` + force kill |
| **Variables PORT/WS_PORT/HTTP_PORT inconsistentes** | Constantes mal renombradas durante refactors | Se estabilizó en v2 |
| **WebSocket bloqueado por firewall** | WS en puerto separado (9878) no accesible desde red externa | Se unificó HTTP+WS en mismo puerto; fallback a polling |
| **UI sin feedback al crear tarea** | Modal se cerraba sin indicación visible | Se mejoró el estado "working" en la UI |
| **alert/prompt/confirm bloqueantes** | Diálogos JS que el usuario rechazó explícitamente | Reemplazados por modales HTML inline |
| **Error 403 en OpenCode GO API** | User-Agent `Python-urllib/3.x` bloqueado | Se fijó `User-Agent: curl/8.0` |
| **Hot-reload no resuelve HTML faltante** | Watcher reinicia server.py pero no regenera HTML | Se agregó inicialización al startup |
| **Agente escribe commits en el repo principal** | `agent.py` hacía `git commit` en el repo de p3 | Se aisló en versiones separadas (sin commit al repo padre) |
| **Archivos perdidos durante `mv a v1/`** | Comando glob incorrecto | Se restauró desde git |
| **LLM tarda 60+ segundos** | Modelo deepseek genera mucho reasoning | El usuario consideró inaceptable; no se optimizó del todo |

---

## 3) Stack Decisions

| Capa | Decisión | Detalle |
|---|---|---|
| **Lenguaje** | Python 3.11 → Python 3.12 | 3.11 para MetaGPT (<3.12), 3.12 para s74 standalone |
| **Gestor Python** | **uv** | En vez de pip/venv. Resuelve PEP 668, PATH, ensurepip, y resolución de dependencias |
| **LLM Provider** | **OpenCode GO** | `OPENCODE_GO_API_KEY`, `OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1/` |
| **Modelos benchmarkeados** | 6 modelos | `deepseek-v4-flash`, `deepseek-v4-pro`, `kimi-k2.6`, `kimi-k2.5`, `mimo-v2.5`, `minimax-m2.5` |
| **Base de datos** | **SQLite** | Ledger de tareas, versiones, benchmarks, tags, config |
| **Tiempo real** | **WebSockets** (`websockets` librería Python) | Comunicación bidireccional con la UI |
| **HTTP Server** | Custom asyncio + `websockets.serve` | En v1: HTTP+WS en puertos separados; en v2: unificados |
| **HTTP Client** | **httpx** | Llamadas a la API del LLM (OpenAI-compatible) |
| **Control de versiones** | **Git** | Cada versión en su directorio con su propio `.git` (aislado) |
| **Web UI (MetaGPT SPO)** | **Streamlit** | Descartado junto con MetaGPT |
| **Web UI (s74 v1)** | **HTML embebido en server.py** → luego archivo separado | Mala práctica revertida en v2 |
| **Web UI (s74 v2)** | **HTML en `_template/`** | Separado del código del orquestador |
| **Hot-reload** | **watchdog** (vía `uvicorn` o custom) | Detecta cambios en `server.py` y reinicia |
| **Infraestructura** | Sin Docker (disponible pero no usado) | Solo `uv` + Python nativo |
| **Browser** | Firefox (para probar UI) | Usuario probaba en Firefox |
| **Host** | `0.0.0.0` (todas las interfaces) | Accesible desde la red |
| **Puertos** | 9878 (HTTP), 9879 (WS) en v1 → unificado en 9879 en v2 | |
| **Gitignore** | Excluye `*.db`, `*.log`, `.venv`, `data/`, `versions/live` | |
