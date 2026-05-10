# 🎨 Mejoras Visuales para Agentes de Terminal

> Hallazgos, paquetes, skins, extensiones y propuestas para mejorar la legibilidad
> y visualización de agentes de terminal como **pi**, **OpenCode** y **Hermes**.

---

## 📦 Pi — Paquetes y extensiones

### 1. `amp-themes` ⭐ — La solución más completa

**npm:** [`amp-themes`](https://www.npmjs.com/package/amp-themes)  
**Instalación:** `pi install npm:amp-themes`

> *"Amp-inspired Pi UI suite: theme, editor chrome, and compact tool display."*

Incluye:

- 🎭 **3 temas:** `amp-dark`, `amp-light`, `amp-gruvbox-dark-hard`
- 🖼️ **Editor chrome** con bordes redondeados que muestran: modelo, nivel de thinking, costos, % de contexto, directorio actual, rama git y resumen de cambios
- 📦 **Compact tool rendering** — los outputs de herramientas se muestran de forma compacta (menos texto abrumador)
- 💬 **Mensajes de usuario compactos** con colores sincronizados al nivel de thinking
- ⚡ Spinner de working status integrado en el borde del editor

![amp-gruvbox-dark-hard screenshot](https://raw.githubusercontent.com/me-frankan/amp-themes/main/screenshots/amp-gruvbox-dark-hard.png)

**Uso:**
```bash
pi install npm:amp-themes
```

En `~/.pi/agent/settings.json`:
```json
{
  "theme": "amp-dark"
}
```

---

### 2. `@ifi/oh-pi-themes` — Colección de temas

**npm:** [`@ifi/oh-pi-themes`](https://www.npmjs.com/package/@ifi/oh-pi-themes)  
**Instalación:** `pi install npm:@ifi/oh-pi-themes`

> *"Color themes for pi: cyberpunk, nord, gruvbox, tokyo-night, catppuccin, and more."*

Temas incluidos: Catppuccin Mocha, Cyberpunk, Gruvbox Dark, Nord, Oh P Dark, Tokyo Night.

```bash
pi install npm:@ifi/oh-pi-themes
```

```json
{ "theme": "tokyo-night" }
```

---

### 3. `pi-tool-display` — Compact Tool Rendering

**npm:** [`pi-tool-display`](https://www.npmjs.com/package/pi-tool-display)  
*(ya incluido en `amp-themes`, no instalar por separado si ya tienes amp-themes)*

Extensión que sobreescribe los renderers de herramientas para mostrar modo colapsado (solo título) o expandido (output completo). Atajo `Ctrl+O`.

---

### 4. Extensiones de ejemplo (vienen con pi)

Todas en [`examples/extensions/`](https://github.com/badlogic/pi-mono/tree/main/examples/extensions) del repo de pi.

| Extensión | Enlace | Qué hace |
|-----------|--------|----------|
| **`minimal-mode.ts`** | [🔗](https://github.com/badlogic/pi-mono/blob/main/examples/extensions/minimal-mode.ts) | Override total de tools con rendering colapsado/expandido |
| **`border-status-editor.ts`** | [🔗](https://github.com/badlogic/pi-mono/blob/main/examples/extensions/border-status-editor.ts) | Editor con bordes: spinner, modelo, thinking, contexto, cwd, git |
| **`custom-footer.ts`** | [🔗](https://github.com/badlogic/pi-mono/blob/main/examples/extensions/custom-footer.ts) | Footer con tokens, costos, rama, modelo |
| **`rainbow-editor.ts`** | [🔗](https://github.com/badlogic/pi-mono/blob/main/examples/extensions/rainbow-editor.ts) | Efecto arcoíris animado en el editor |
| **`status-line.ts`** | [🔗](https://github.com/badlogic/pi-mono/blob/main/examples/extensions/status-line.ts) | Indicador persistente en footer |
| **`plan-mode/`** | [🔗](https://github.com/badlogic/pi-mono/tree/main/examples/extensions/plan-mode) | Widgets persistentes sobre el editor |

---

## 🌊 Hermes Agent — Skins nativos + Web UI

Hermes tiene un **sistema de skins nativo** y una **Web UI** separada. Es el que mejor soporte visual tiene de los tres.

### Sistema de Skins (nativo, sin plugins)

Documentación: [`skins.md`](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skins.md)  
Engine: [`skin_engine.py`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/skin_engine.py)

```bash
/skin                   # Ver skin actual y listar disponibles
/skin ares              # Cambiar a skin "ares"
/skin mytheme           # Cambiar a skin personalizada
```

O en `~/.hermes/config.yaml`:
```yaml
display:
  skin: ares
```

#### Skins incluidas

| Skin | Descripción | Branding |
|------|-------------|----------|
| `default` | Hermes clásico — dorado y kawaii | `Hermes Agent` |
| `ares` | Dios de la guerra — carmesí y bronce | `Ares Agent` |
| `mono` | Monocromático — escala de grises limpio | `Hermes Agent` |
| `slate` | Azul frío — enfocado a desarrolladores | `Hermes Agent` |
| `poseidon` | Dios del mar — azul profundo y espuma | `Poseidon Agent` |
| `sisyphus` | Austero gris con persistencia | `Sisyphus Agent` |
| `charizard` | Volcánico — naranja quemado y brasa | `Charizard Agent` |

#### Skins personalizadas

Crea archivos YAML en `~/.hermes/skins/`. Heredan lo que no especifiques de `default`:

```yaml
name: cyberpunk
description: Neon terminal theme

colors:
  banner_border: "#FF00FF"
  banner_title: "#00FFFF"
  banner_accent: "#FF1493"

spinner:
  thinking_verbs: ["jacking in", "decrypting", "uploading"]

branding:
  agent_name: "Cyber Agent"
  response_label: " ⚡ Cyber "

tool_prefix: "▏"
```

#### Opción compacta

En `~/.hermes/config.yaml`:
```yaml
display:
  compact: true           # Modo compacto (menos verbose)
  show_cost: true         # Mostrar costos por turno
  show_reasoning: false   # Mostrar/ocultar reasoning del modelo
  tool_progress: all      # Cómo mostrar progreso de tools
  skin: default
```

### Hermes Web UI — Dashboard web completo

**npm:** [`hermes-web-ui`](https://www.npmjs.com/package/hermes-web-ui)  
**Instalación:** `npm install -g hermes-web-ui && hermes-web-ui start`

![Hermes Web UI](https://github.com/EKKOLearnAI/hermes-web-ui/blob/main/packages/client/src/assets/image1.png)

Características:

- 🤖 Chat con streaming SSE y gestión de sesiones
- 📂 Base de datos SQLite local con sincronización automática
- 🎨 Renderizado Markdown con resaltado de sintaxis
- 🔧 Tool call detail expansion (argumentos / resultados)
- 📊 Analíticas de uso: tokens, costos, hits de caché, gráficos de 30 días
- 🕐 Cron jobs programables
- 🧠 Descubrimiento automático de modelos
- 🔌 Configuración visual de 8 plataformas (Telegram, Discord, Slack, WhatsApp, etc.)

```bash
hermes-web-ui start
```

---

## ⚡ OpenCode — Plugins + Web UI nativa

### Web UI nativa

OpenCode trae web UI incorporada:

```bash
opencode web                     # Inicia server + abre navegador
opencode web --port 8080         # Puerto específico
opencode web --mdns              # mDNS discovery (opencode.local)
opencode serve                   # Headless server (sin UI)
```

Por defecto escucha en `127.0.0.1:0` (puerto aleatorio). Usa `--hostname 0.0.0.0` para acceso remoto.

### oh-my-opencode — El plugin "baterías incluidas"

**npm:** [`oh-my-opencode`](https://www.npmjs.com/package/oh-my-opencode)  
**Instalación:** `opencode plugin install oh-my-opencode`

> *"The Best AI Agent Harness — multi-model orchestration, parallel background agents, LSP/AST tools"*

- 🔄 Orquestación multi-modelo (Claude, GPT, Kimi, Gemini en paralelo)
- 🧠 **Ultrawork mode**: agente persistente que trabaja hasta terminar
- 🖥️ **Tmux integration**: REPL, debuggers, TUI tools en sesiones reales
- ✅ **Todo enforcement**: mantiene el agente enfocado en la tarea
- 💬 **Comment reviewer**: elimina comentarios con "olor a IA"
- 🔌 Compatible con hooks, comandos, skills, MCP de Claude Code

### oh-my-opencode-slim — Versión ligera

**npm:** [`oh-my-opencode-slim`](https://www.npmjs.com/package/oh-my-opencode-slim)  
Versión reducida del orquestador multi-modelo.

### @tarquinen/opencode-dcp — Context Pruning

**npm:** [`@tarquinen/opencode-dcp`](https://www.npmjs.com/package/@tarquinen/opencode-dcp)  
Plugin que optimiza tokens podando outputs obsoletos de herramientas del contexto de conversación. Ayuda a mantener la sesión manejable y legible.

```bash
opencode plugin install @tarquinen/opencode-dcp
```

### Otros plugins relevantes

| Plugin | Enlace | Función |
|--------|--------|---------|
| `oh-my-opencode-slim` | [npm](https://www.npmjs.com/package/oh-my-opencode-slim) | Orquestador ligero multi-modelo |
| `opencode-skills-collection` | [npm](https://www.npmjs.com/package/opencode-skills-collection) | Auto-descarga y actualización de skills |
| `@devtheops/opencode-plugin-otel` | [npm](https://www.npmjs.com/package/@devtheops/opencode-plugin-otel) | Telemetría OpenTelemetry |
| `@braintrust/trace-opencode` | [npm](https://www.npmjs.com/package/@braintrust/trace-opencode) | Trazado de conversaciones a Braintrust |

---

## 📊 Comparativa rápida

| Aspecto | Pi | Hermes | OpenCode |
|---------|----|--------|----------|
| **Skins/Temas** | ✅ Temas JSON (51 tokens de color) | ✅ Skins YAML nativos (7 incluidos) | ❌ No tiene sistema de temas TUI |
| **Compact mode** | ✅ `amp-themes` / `pi-tool-display` | ✅ `display.compact: true` nativo | ❌ No tiene modo compacto |
| **Web UI** | ❌ No tiene (se puede construir) | ✅ `hermes-web-ui` (dashboard completo) | ✅ `opencode web` (nativa) |
| **Costos visibles** | ✅ En footer/widget | ✅ `display.show_cost: true` | ❌ No en TUI |
| **Tool rendering** | ✅ Customizable vía extensiones | ✅ Skins controlan tool_prefix y emojis | ❌ No personalizable |
| **Thinking level** | ✅ Colores en bordes del editor | ✅ `display.show_reasoning` | ❌ No aplica |
| **Plugin system** | ✅ Extensiones TypeScript | ✅ Plugins Git | ✅ Plugins npm |

---

## 💡 Propuestas transversales

### 🟢 Fáciles (extensión para cualquier agente)

| Propuesta | Pi | Hermes | OpenCode |
|-----------|----|--------|----------|
| **Modo Compacto Total** | ✅ Existe (`minimal-mode.ts`) | ✅ Nativo (`compact: true`) | ❌ Faltaría plugin |
| **Diff Visual para edits** | ✅ Posible (colores `toolDiff*`) | ❌ No tiene | ❌ No tiene |
| **Resumen Inteligente** | 🔧 Por construir | 🔧 Por construir | 🔧 Por construir |
| **Reader Mode** | 🔧 Por construir | 🔧 Por construir | 🔧 Por construir |

### 🟡 Medias

| Propuesta | Descripción |
|-----------|-------------|
| **Vista Árbol de Herramientas** | Árbol colapsable de tool calls con iconos y resultados anidados |
| **Timeline View** | Línea de tiempo visual con iconos, duración, colores por estado |
| **Dashboard Footer** | Footer denso: `ctx 34%/128k │ ↑1.2k ↓892 │ $0.023 │ claude-3.5 │ main` |

### 🔴 Avanzadas

| Propuesta | Descripción |
|-----------|-------------|
| **Web UI Local universal** | Servidor web que muestra la sesión con búsqueda, árbol, syntax highlighting |
| **Breadcrumbs de Contexto** | Barra minimalista en borde del editor con ruta, rama, mensaje actual |

---

## 🖥️ Cómo ver este archivo

### En la terminal (local)

```bash
# Con glow (recomendado, instalado en este sistema)
glow mejoras-visuales-pi.md

# Con pandoc + w3m
pandoc mejoras-visuales-pi.md | w3m -T text/html -dump
```

### En el navegador (vía servidor HTTP)

```bash
# Ya hay HTML generado
cd /home/vuos/code/p3/s51
python3 -m http.server 8080
```

Luego desde tu máquina local:
- Si tienes acceso a la IP: `http://<IP-DEL-SERVIDOR>:8080/mejoras-visuales-pi.html`
- Con túnel SSH: `ssh -L 8080:localhost:8080 usuario@host` → `http://localhost:8080/mejoras-visuales-pi.html`

---

## 🔗 Enlaces rápidos

| Recurso | Enlace |
|---------|--------|
| **PI** | |
| Pi (npm) | https://www.npmjs.com/package/@mariozechner/pi-coding-agent |
| Pi GitHub | https://github.com/badlogic/pi-mono |
| `amp-themes` | https://www.npmjs.com/package/amp-themes |
| `@ifi/oh-pi-themes` | https://www.npmjs.com/package/@ifi/oh-pi-themes |
| `pi-tool-display` | https://www.npmjs.com/package/pi-tool-display |
| Extensiones ejemplo | https://github.com/badlogic/pi-mono/tree/main/examples/extensions |
| Screenshot amp-themes | https://raw.githubusercontent.com/me-frankan/amp-themes/main/screenshots/amp-gruvbox-dark-hard.png |
| **HERMES** | |
| Hermes Agent GitHub | https://github.com/NousResearch/hermes-agent |
| Hermes Skins docs | https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skins.md |
| Hermes Web UI (npm) | https://www.npmjs.com/package/hermes-web-ui |
| Hermes Skin Engine | https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/skin_engine.py |
| **OPENCODE** | |
| OpenCode (npm) | https://www.npmjs.com/package/opencode |
| `oh-my-opencode` | https://www.npmjs.com/package/oh-my-opencode |
| `oh-my-opencode-slim` | https://www.npmjs.com/package/oh-my-opencode-slim |
| `@tarquinen/opencode-dcp` | https://www.npmjs.com/package/@tarquinen/opencode-dcp |
| `opencode-skills-collection` | https://www.npmjs.com/package/opencode-skills-collection |
| `@braintrust/trace-opencode` | https://www.npmjs.com/package/@braintrust/trace-opencode |

---

*Creado: 2026-05-03 · pi-agent session s51 · Actualizado con info de Hermes y OpenCode*
