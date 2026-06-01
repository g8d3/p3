Ahora voy a explorar en paralelo los stacks tecnológicos reales de los proyectos.
Tengo todos los datos. Aquí está el análisis completo:

---

# Análisis de 75 proyectos en p3

## 1. Categorías de proyectos

| Categoría | Proyectos | % |
|---|---|---|
| **🤖 AI Agents & Multi-Agent Systems** | s2, s9, s17, s18, s19, s20, s21, s37, s44, s50, s51, s57, s63, s65, s66, s68, s70, s73, s73-framework, s74 | **~20** | **27%** |
| **📈 Crypto / Trading / DeFi** | s1, s16, s28, s29, s33, s34, s39, s40, s41, s42, s43 | **11** | **15%** |
| **🎬 Video / Content Production** | s24, s25, s26, s35, s36, s45, s46, s52, s53, s58, s61 | **11** | **15%** |
| **🌐 Browser Automation / CDP / Scraping** | s4, s6, s7, s8, s31, s32, s44 (compartido) | **7** | **9%** |
| **📱 Full-stack Apps / Platforms** | s3, s5, s56, s60, s62, s71 | **6** | **8%** |
| **🔐 Smart Contract Security** | s10, s11, s12 | **3** | **4%** |
| **💰 Finance / Tax / LLC** | s14, s49 | **2** | **3%** |
| **🧪 API / Benchmarking / Testing** | s15, s23, s59, s64 | **4** | **5%** |
| **⚙️ Infra / Config / DevTooling** | s22, s30, s54, s69, s75, s76 | **6** | **8%** |
| **🎮 Vibe Coding / Real-time Collab** | s47, s48 | **2** | **3%** |
| **🧊 Vacío / Mínimo** | s13, s55 | **2** | **3%** |

---

## 2. Stacks tecnológicos predominantes

### Lenguajes

| Lenguaje | Proyectos (aprox.) | Tendencia |
|---|---|---|
| **Python** | ~40+ | **Dominante absoluto.** Presente en crypto, agents, video, scraping, data. |
| **JavaScript** | ~22 | Base sólida. Principalmente Node.js (Express, Playwright, Puppeteer). |
| **TypeScript** | ~15 | **En crecimiento.** Reemplazando a JS en proyectos nuevos (React, fullstack). |
| **Shell/Bash** | ~8 | Utilitario (scripts, CI, workers). |
| **Kotlin** | 2 (s56, s71) | Casos específicos (Compose Desktop, Android). |
| **Go** | 2 (s56, s73) | Emergente — un AI agent CLI, un microservicio CSV. |
| **Rust** | 1 (s60) | SpacetimeDB module (fullstack). |
| **Zig** | 1 (s33) | EVM wallet generator (experimental). |

### Frameworks clave

| Capa | Stack | Proyectos |
|---|---|---|
| **Frontend** | **React** (mayoría Vite, 1 Next.js) | s3, s5, s6, s11, s16, s19, s45, s47, s60, s63 |
| **Backend** | **Express** (Node) + **FastAPI** (Python) | Express: s2, s5, s11, s20, s63, s68 — FastAPI: s16, s35 |
| **Bases de datos** | **SQLite** es el estándar de facto | s2, s5, s16, s20, s65, s74, s75, s76 |
| **Browser automation** | **Playwright** y **Puppeteer** | s4, s7, s8, s25, s44, s58, s63 |
| **AI/LLM** | **OpenAI SDK** (mayoría), Bittensor, Anthropic | Decenas de proyectos |
| **Crypto** | **ethers.js/viem**, hyperliquid-sdk, wagmi/RainbowKit | s11, s19, s34, s39, s40, s41 |
| **Video** | **Remotion** (React), **ManimGL** (Python), **ShortGPT** | s45, s51, s52, s53 |

### Patrón de stack típico por categoría

```
AI Agent:       Python/TypeScript + Express/FastAPI + SQLite + OpenAI SDK + Playwright
Crypto/DeFi:    Python + hyperliquid-sdk + pandas + (ocasional) React frontend
Video:          Python + OpenAI/ElevenLabs + Playwright/Puppeteer + YouTube API
CDP/Scraping:   TypeScript/JS + Playwright/Puppeteer + (ocasional) PocketBase
Fullstack:      React (Vite) + Express (Node) + SQLite + JWT
```

---

## 3. Tendencias generales del usuario

### 🔥 What the user *really* cares about

**"Agentes autónomos que hacen cosas."** No es teoría — es ejecución práctica. El hilo conductor de >50% de los proyectos es: *agentes de IA que producen outputs del mundo real* (tradear, crear video, publicar contenido, escanear contratos, interactuar con browsers).

### Patrones de comportamiento identificados

**1. Prototipado ultra-rápido (velocity first)**
- Usa **Python** para la lógica core (mínima fricción) y **TypeScript/React** solo cuando hay UI.
- Stack de烧烤 mínimo: SQLite (sin ORM pesado), Express/FastAPI (sin GraphQL), Playwright directo.
- Promedio de proyecto: días, no semanas. Muchos son MVPs funcionales.

**2. Obsesión por automatizar todo lo que toca**
- Contenido: escribe scripts para generar, editar, y publicar video automáticamente.
- Trading: bots + backtesters + monitoreo de VRP — todo automatizado.
- Browsers: CDP, Playwright, Puppeteer en mil variantes para controlar el navegador.
- Impuestos: incluso el tax filing lo quiere automatizar.

**3. Diversidad técnica experimental (no dogmático)**
- Salta entre Zig (wallets), Rust (SpacetimeDB), Go (Agents), Kotlin (Compose Desktop), Java/Go (CSV app).
- Pero **siempre vuelve a Python** para lo serio. Los experiments son juguetes.

**4. Fuerte inclinación crypto/DeFi — pero pragmática**
- No es maximalista crypto. Usa bittensor, Hyperliquid, ethers.js, wagmi como **herramientas**, no como ideología.
- Los proyectos de trading son análisis real (backtesting, VRP, estrategias) no memecoins.

**5. Evolución visible: de utilitarios → sistemas multi-agente**
- Proyectos tempranos (s1-s20): scraper individual, bot simple, app monolítica.
- Proyectos recientes (s50-s76): **multi-agent orchestrators**, agent hubs, frameworks, pipelines. Maduración clara hacia arquitecturas de agentes.

**6. Interés en "vibe coding" y colaboración en tiempo real**
- LiveKit + WebSocket + Yjs para coding colaborativo (s47, s48).
- Es un interés emergente — pocos proyectos pero señales claras de exploración.

### Arquetipo del usuario

> **Constructor autodidacta.** Prioriza "que funcione" sobre "que sea perfecto." Le gusta explorar tecnologías nuevas (Zig, Rust, LiveKit) pero su core es Python + TypeScript. Está obsesionado con agentes autónomos, automatización de contenido, y crypto análisis. Su evolución es clara: pasó de hacer scripts aislados a construir sistemas multi-agente orquestados. Es un **power builder** que genera ~1 proyecto por semana como promedio.

### Mapa de evolución temporal (inferido por número de proyecto)

```
s01-s10:  Scrapers, bots simples, security experiments
s11-s20:  Apps más completas, AI chat, marketplace
s21-s30:  Video, bittensor, trading, CDP tooling
s31-s40:  Wallets, content automation, trading bots
s41-s50:  Multi-agent, video pipelines, vibe coding
s51-s60:  Cinematic video, agent hubs, fullstack apps
s61-s76:  Frameworks, agent systems, orquestadores
         → MADUREZ: de scripts → sistemas multi-agent
```
