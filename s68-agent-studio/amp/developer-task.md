# 🏗️ Tu misión: Construir Agent Studio

Eres un Developer Agent. Tu trabajo es construir la plataforma **Agent Studio** — un sistema donde agentes de IA codean, graban, stremean y reciben feedback de humanos y otros agentes.

> **Mientras trabajas, TODO lo que haces está siendo grabado y transmitido en vivo.**
> Humanos y otros agentes pueden verte, darte feedback, e intervenir si te atascas.

---

## 📋 Qué construir (fase 1)

### 1. Dashboard Web (React + Vite)
Un dashboard para que humanos vean agentes trabajar en vivo:

- **`/watch`** — Ver agente en vivo: su escritorio (screenshots periódicos), comandos que ejecuta, output, pensamientos, errores
- **`/agents`** — Lista de agentes activos con estado
- **`/recordings`** — Ver grabaciones pasadas (replay del trace)
- **`/feedback`** — Panel para enviar feedback, sugerencias, comandos
- **Multi-view** — Poder ver 2-4 agentes simultáneamente (como s63 MultiStream)

### 2. Sistema de Feedback Humano
- Chat en vivo junto al stream del agente
- Los humanos escriben y el agente lo recibe como evento
- Los humanos pueden enviar **comandos de intervención** si el agente está atascado
- Historial persistente de feedback por sesión

### 3. Grabación con Estructura Inteligente
Ya existe `tape/recorder.js` que graba en JSONL.
Necesitas construir **el reproductor** (`tape/player.js`) que:
- Lee el trace JSONL y reproduce los eventos en orden
- Convierte el trace a **video MP4** (screenshots + TTS narración)
- Genera **subtítulos SRT** sincronizados con los eventos
- Exporta a **Markdown** como tutorial paso a paso

### 4. Sistema de Revisión por Agentes
- Un agente revisor puede "ver" el stream de otro agente (leer eventos)
- El revisor puede generar reportes de calidad
- Si detecta un error, puede spawnear un helper agent que ayude

---

## 🛠 Stack técnico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite + react-router-dom |
| Streaming | WebSocket (ws) — ya hay base en `stage/server.js` |
| Orquestación | sandbox-agent — ya hay base en `amp/orquestador.js` |
| Grabación | JSONL + screenshots — ya hay `tape/recorder.js` |
| Estilos | CSS moderno (dark theme, responsive) |
| Build | Vite |

## 📁 Estructura del proyecto

```
s68-agent-studio/
├── package.json
├── amp/
│   ├── orquestador.js     ← Ya existe (lanza agentes)
│   └── developer-task.md  ← Este archivo
├── stage/
│   └── server.js          ← Ya existe (streaming server)
│   └── public/            ← Dashboard web (lo construyes TÚ)
├── tape/
│   ├── recorder.js        ← Ya existe
│   └── player.js          ← LO CONSTRUYES TÚ
├── inter/                  ← Sistema de feedback (LO CONSTRUYES TÚ)
├── voz/                    ← TTS y narración
├── data/                   ← Grabaciones
└── client/                 ← React dashboard (LO CONSTRUYES TÚ)
```

## 🚀 Primer paso concreto

1. Lee `stage/server.js`, `tape/recorder.js`, y `amp/orquestador.js` para entender la infraestructura existente
2. Crea `client/` con React + Vite
3. Construye la página `/watch` que se conecta al WebSocket del stage y muestra eventos en tiempo real
4. Construye el panel de feedback
5. Construye `tape/player.js` para reproducir grabaciones

## 💡 Principios

- **Simplicidad > Features**. Una página que funciona bien es mejor que 5 a medias.
- **El trace es el activo principal**. Los videos se pueden generar después. El texto estructurado vale oro.
- **Feedback loop rápido**. Cada ciclo: codeas → transmites → recibes feedback → mejoras.
- **Colaboración**. No estás solo. Humanos y otros agentes te ayudan si lo pides.

## ⚡ Mientras trabajas

- **Transmites en vivo** — cada tool_call, mensaje, pensamiento se ve en el dashboard
- **Te graban** — tu sesión queda guardada como trace para reproducir después
- **Pueden ayudarte** — si ves `agent:feedback` o `agent:intervene` en tus eventos, alguien te está dando una mano
- **Si te atascas**, pide ayuda explícitamente y alguien (humano o agente) te responderá

---

**¡Adelante! Construye algo que otros agentes puedan usar para mostrar su trabajo al mundo.**
