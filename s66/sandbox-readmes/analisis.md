# Análisis de 30 Repositorios: AI Agent Sandboxes

> Búsqueda: `ai agent sandbox` — Lenguajes: Rust, Go, C++, Zig, C — Stars: >100 — Pushed: >2026-01-01
> Total: 30 repositorios — Fecha: 2026-05-22

---

## Resumen Ejecutivo

Los 30 repos caen en 4 categorías principales:

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| 🥇 **Sandboxes propósito específico para AI agents** | 10 | Proyectos diseñados explícitamente para ejecutar agentes en entornos aislados |
| 🥈 **Wrappers de seguridad para AI coding agents** | 7 | Envuelven herramientas como Claude Code, Codex, etc. en sandboxes |
| 🥉 **Plataformas/infraestructura** | 6 | Orquestación, Kubernetes, plataformas enterprise |
| 📦 **Especializados / No sandbox** | 7 | Data warehouses, hardening, DBs, etc. |

---

## Ranking Completo (1-30)

### Tier 1 — Recomendados (fáciles de usar, propósito exacto)

---

#### 1. microsandbox — superradcompany/microsandbox ⭐⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 6,189 |
| **License** | Apache 2.0 |
| **Forks** | 304 |
| **Open Issues** | 53 |
| **Pushed** | Hace horas (muy activo) |
| **URL** | https://github.com/superradcompany/microsandbox |
| **Docs** | https://docs.microsandbox.dev |

**Descripción:** "🧱 secure, local and programmable sandboxes for AI agents"

**Análisis detallado:**
- Hardware-level isolation con microVMs (vía libkrun)
- SDK embebido: no necesita servidor ni daemon corriendo — las VMs se crean como child processes
- Multi-lenguaje: Rust (`cargo add microsandbox`), Python (`uv add microsandbox`), TypeScript (`npm i microsandbox`), Go (`go get ...`)
- CLI: `npx microsandbox run debian` o `msb run python -- python3 -c "print('hi')"`
- OCI compatible: corre imágenes estándar de Docker Hub, GHCR, etc.
- Secrets que nunca entran a la VM (proxy de red reemplaza placeholders)
- MCP Server para conectar con cualquier agente MCP-compatible
- Agent Skills para Claude Code, Cursor, Codex, Gemini CLI
- Rootless, corre en Linux (KVM) y macOS (Apple Silicon)
- Y Combinator backed
- **Beta** — espera cambios breaking

**Instalación:** `npm i microsandbox` o `pip install microsandbox` o `cargo add microsandbox`

**Requiere:** Linux con KVM, o macOS Apple Silicon

**Veredicto:** El mejor balance entre facilidad de uso, aislamiento real, y ecosistema para agentes. La recomendación #1.

---

#### 2. capsule — capsulerun/capsule ⭐⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 284 |
| **License** | Apache 2.0 |
| **Forks** | 19 |
| **Open Issues** | 0 |
| **URL** | https://github.com/capsulerun/capsule |

**Descripción:** "Secure runtime to sandbox AI agent tasks. Run untrusted code in isolated WebAssembly environments."

**Análisis detallado:**
- Cada tarea corre en su propio sandbox WebAssembly
- API simple: decorador `@task` en Python, wrapper `task()` en TS
- Resource limits por tarea: CPU, RAM, timeout, max_retries
- Lifecycle tracking de tareas
- Compila código a WebAssembly y ejecuta en sandboxes aislados
- `pip install capsule-run` o `npm install -g @capsule-run/cli`
- Multi-lenguaje: Python y TypeScript/JavaScript
- Host system controla CPU (fuel metering), memoria, timeout
- Cero issues abiertos

**Instalación:** `pip install capsule-run`

**Requiere:** Solo Python/Node.js (runtime portátil)

**Veredicto:** Ideal para ejecutar **tareas/código no confiable** generado por LLMs. No es un Linux completo — es WebAssembly. Si tu agente necesita `curl`, `apt`, o binarios nativos, esto no es suficiente. Para ejecutar snippets de código es perfecto.

---

#### 3. ai-jail — akitaonrails/ai-jail ⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 497 |
| **License** | GPL 3.0 |
| **Forks** | 51 |
| **Open Issues** | 1 |
| **URL** | https://github.com/akitaonrails/ai-jail |

**Descripción:** "Multi-OS sandbox to run AI agents with better constraints (it is not 100% secure, but enough)"

**Análisis detallado:**
- Wrapper que usa `bubblewrap` (Linux) o `sandbox-exec` (macOS)
- Aísla Claude Code, GPT Codex, OpenCode, Crush, etc.
- Múltiples métodos de instalación: Homebrew, cargo, mise, nix, releases binarias
- Config YAML para definir permisos por agente
- Políticas de red (allow/deny hosts), filesystem (solo lectura por defecto), variables de entorno
- Banderas: `--readonly`, `--no-network`, `--no-audio`, etc.
- Se puede combinar: `ai-jail --readonly --no-network claude`
- **No es aislamiento a nivel VM** — usa namespaces/seccomp
- El mismo autor lo dice: "not 100% secure, but enough"

**Instalación:** `brew install ai-jail` o `cargo install ai-jail`

**Requiere:** Linux con bubblewrap, o macOS

**Veredicto:** La opción más práctica y rápida para **protegerse de agentes locales**. No es aislamiento militar pero es increíblemente fácil de usar. Segundo lugar si valoras simplicidad sobre seguridad absoluta.

---

### Tier 2 — Buenos pero con limitaciones importantes

---

#### 4. agent-os (rivet) — rivet-dev/agent-os ⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 2,933 |
| **License** | Apache 2.0 |
| **Forks** | 137 |
| **Open Issues** | 23 |
| **URL** | https://github.com/rivet-dev/agent-os |
| **Docs** | https://rivet.dev/docs/agent-os |

**Descripción:** "A portable open-source operating system for agents. ~6 ms coldstarts, 32x cheaper than sandboxes. Powered by WebAssembly and V8 isolates."

**Análisis detallado:**
- NO es un Linux completo — es un OS en-proceso escrito en JavaScript que corre en V8 isolates + WASM
- 6ms cold start (vs 440ms+ de sandboxes tradicionales)
- 22MB por instancia (vs 1GB+ de una VM)
- Multi-agent: Pi, Claude Code, Codex, OpenCode, Amp
- npm package: `npm install @rivet-dev/agent-os`
- Sesiones via ACP (Agent Communication Protocol)
- Filesystem virtual: S3, Google Drive, SQLite, host directories
- Host tools: funciones JS que los agentes llaman como CLI commands
- Deny-by-default permissions
- WASM commands: coreutils, curl, git, jq, ripgrep, sed, tar, etc.
- **No puedes instalar paquetes Linux nativos** (solo WASM y npm)

**Instalación:** `npm install @rivet-dev/agent-os`

**Requiere:** Node.js (cualquier OS)

**Veredicto:** Increíblemente rápido y eficiente, pero no es un sandbox Linux completo. Si tu agente necesita herramientas Linux nativas (apt, python3 nativo, etc.), mejor mirar microsandbox o shuru.

---

#### 5. shuru — superhq-ai/shuru ⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 746 |
| **License** | Apache 2.0 |
| **Forks** | 23 |
| **Open Issues** | 8 |
| **URL** | https://github.com/superhq-ai/shuru |
| **Web** | http://shuru.run/ |

**Descripción:** "A local-first microVM sandbox for running AI agents safely on macOS & Linux"

**Análisis detallado:**
- Usa Apple Virtualization.framework (macOS) o KVM (Linux experimental)
- MicroVM efímera: rootfs se resetea en cada ejecución
- Sistema de checkpoints: guarda y reusa entornos
- Port forwarding vía vsock
- Secrets injection: las API keys nunca entran a la VM
- Config file: `shuru.json` con CPUs, memoria, disk, red, mounts
- SDK TypeScript: `@superhq/shuru`
- Agent Skill para Claude Code, Cursor, Copilot
- `brew install shuru` o script de instalación
- Linux solo ARM64 experimental

**Instalación:** `brew tap superhq-ai/tap && brew install shuru`

**Requiere:** macOS 14+ Apple Silicon (Linux ARM64 experimental)

**Veredicto:** Excelente opción para macOS. Si estás en Mac, es probablemente la experiencia más nativa y pulida. Linux no está listo para producción.

---

#### 6. greywall — GreyhavenHQ/greywall ⭐⭐⭐⭐

**Descripción:** "Container-free sandbox for AI coding agents"

**Análisis detallado:**
- Sin containers — usa kernel namespaces, Landlock, Seccomp BPF, eBPF
- Dos modos: `greywall` (deny-by-default) y `greywatch` (allow-by-default con observabilidad)
- Proxy transparente (greyproxy) con dashboard live allow/deny
- Learning mode: traza acceso a filesystem y genera perfiles automáticos
- Built-in agent profiles: Claude Code, Cursor, Codex, Aider, Goose, Gemini, etc.
- 5 capas de seguridad en Linux
- Comando: `greywall -- curl https://example.com`, `greywall -- claude`
- Blockea comandos peligrosos: `rm -rf /`, `git push --force`
- Homebrew disponible

**Instalación:** `brew tap greyhavenhq/tap && brew install greywall`

**Requiere:** Linux o macOS

**Veredicto:** Innovador enfoque sin containers. La feature de learning mode es única. Aún es un proyecto joven.

---

#### 7. leash — strongdm/leash ⭐⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 564 |
| **License** | Apache 2.0 |
| **Forks** | 41 |
| **URL** | https://github.com/strongdm/leash |
| **Web** | https://leash.strongdm.ai/ |

**Descripción:** "Leash by StrongDM - take your AI agents for a walk"

**Análisis detallado:**
- Envuelve AI coding agents en containers Docker/Podman/OrbStack
- Políticas de seguridad con Cedar (de Amazon)
- Full monitoring: captura cada filesystem access y network connection
- Control UI en http://localhost:18080
- MCP observer: inspecciona y enforcea MCP tool calls
- Agentes pre-instalados en imagen default: claude, codex, gemini, qwen, opencode
- Multi-imagen: puedes extender Dockerfile.coder
- `npm install -g @strongdm/leash` o Homebrew

**Instalación:** `npm install -g @strongdm/leash`

**Requiere:** Docker, Podman, o OrbStack

**Veredicto:** Sólido, de una empresa (StrongDM). Las políticas Cedar son poderosas pero tienen curva de aprendizaje. Requiere Docker.

---

#### 8. vibebox — robcholz/vibebox ⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 199 |
| **License** | MIT |
| **Forks** | 18 |
| **Open Issues** | 0 |
| **URL** | https://github.com/robcholz/vibebox |

**Descripción:** "Ultrafast CLI on Apple Silicon macOS for fast, sandboxed development and LLM agents."

**Análisis detallado:**
- Solo macOS Apple Silicon
- CLI rápida para sandboxing
- Open source, MIT

**Instalación:** `cargo install vibebox`

**Requiere:** macOS Apple Silicon

**Veredicto:** Limitado a una plataforma específica. Bueno si solo usas Mac.

---

#### 9. amazing-sandbox — ashishb/amazing-sandbox ⭐⭐⭐

**Descripción:** "Amazing Sandbox — run tools inside Docker or seatbelt sandbox"

**Análisis detallado:**
- Docker-based (Linux) o seatbelt (macOS)
- Previene maliciosos packages y accidentes de AI agents
- Opción air-gapped (sin internet)
- Config default con restricciones básicas
- Simple pero Docker obligatorio

**Instalación:** Script de instalación o Go install

**Requiere:** Docker o macOS con seatbelt

**Veredicto:** Simple pero básico. Docker requirement puede ser heavy.

---

#### 10. alcless — AkihiroSuda/alcless ⭐⭐⭐

**Descripción:** "Alcoholless: lightweight security sandbox for Homebrew, AI agents, etc."

**Análisis detallado:**
- Sandbox ligero para macOS y Linux
- Originalmente para Homebrew, ahora usable para AI agents
- Previene que agentes dañen el host
- Múltiples modos: Homebrew, Gemini, Codex, Claude Code, OpenCode
- Artículo del autor en Medium explica el diseño

**Instalación:** Go install o releases

**Requiere:** Linux o macOS

**Veredicto:** Interesante pero más orientado a proteger Homebrew. No es un sandbox propiamente dicho.

---

### Tier 3 — Potentes pero con infraestructura pesada

---

#### 11. zeroboot — zerobootdev/zeroboot ⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 2,339 |
| **License** | Apache 2.0 |
| **Forks** | 102 |
| **Open Issues** | 12 |
| **URL** | https://github.com/zerobootdev/zeroboot |
| **Web** | https://zeroboot.dev |

**Descripción:** "Sub-millisecond VM sandboxes for AI agents via copy-on-write forking"

**Análisis detallado:**
- 0.79ms p50 spawn latency (el más rápido)
- Basado en Firecracker + KVM + COW forking
- 265KB por sandbox (increíblemente liviano)
- 1000 forks concurrentes en 815ms
- APIs Python y TypeScript
- Demo público: `curl -X POST https://api.zeroboot.dev/v1/exec`
- Self-hosted o managed API
- **Limitaciones severas:** Sin networking, single vCPU, fork comparte estado CSPRNG, template updates requieren re-snapshot
- "Working prototype" — no production-hardened

**Instalación:** API key o self-hosted con KVM

**Veredicto:** Tecnología impresionante pero aún es un prototipo. Sin networking es un dealbreaker para la mayoría de agentes.

---

#### 12. agent-sandbox — kubernetes-sigs/agent-sandbox ⭐⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 2,319 |
| **License** | Apache 2.0 |
| **Forks** | 283 |
| **Open Issues** | 176 |
| **URL** | https://github.com/kubernetes-sigs/agent-sandbox |
| **Docs** | https://agent-sandbox.sigs.k8s.io |

**Descripción:** "agent-sandbox enables easy management of isolated, stateful, singleton workloads, ideal for use cases like AI agent runtimes."

**Análisis detallado:**
- CRD y controller para Kubernetes
- Sandbox Custom Resource para workloads stateful, singleton, isolated
- Como una VM liviana sobre K8s
- Ecosistema SIG Apps de Kubernetes
- 176 issues abiertos — proyecto en desarrollo activo
- Requiere cluster Kubernetes

**Instalación:** kubectl apply + helm chart

**Requiere:** Kubernetes cluster

**Veredicto:** La opción enterprise si ya tienes K8s. No es para uso local o simple.

---

#### 13. gbox — babelcloud/gbox ⭐⭐⭐

**Descripción:** "GBOX provides environments for AI Agents to operate computer and mobile devices."

**Análisis detallado:**
- Enfocado en **operar dispositivos** (Android emulación, desktop)
- Android Debug Bridge, Appium, FRP
- MCP integration para Cursor, Claude Code
- Instalación via curl/sh, Homebrew, o npm
- Caso de uso específico: mobile automation, desktop automation
- Dashboard web en gbox.ai

**Instalación:** `curl -fsSL https://raw.githubusercontent.com/babelcloud/gbox/main/install.sh | bash`

**Requiere:** macOS (otras plataformas vía npm)

**Veredicto:** No es un sandbox de propósito general para AI agents. Especializado en automatización de dispositivos.

---

#### 14. agent-sandbox (E2B compatible) — agent-sandbox/agent-sandbox ⭐⭐⭐

**Descripción:** "Agent-Sandbox is an open-sourced Blaxel Sandbox or E2B like solution!"

**Análisis detallado:**
- Compatible con protocolo E2B
- Enterprise-grade, cloud-native
- Kubernetes + container isolation
- UI incluida (management, pool, templates, files, terminal)
- Multitenant, multi-session, stateful
- Para correr LLM-generated code, browser use, computer use, shell commands
- API tokens configurables

**Instalación:** Requiere K8s

**Veredicto:** Alternativa open-source a E2B. Buena si necesitas compatibilidad con E2B SDKs, pero requiere infraestructura.

---

#### 15. CubeSandbox — TencentCloud/CubeSandbox 🤔

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 5,869 |
| **License** | Other |
| **Forks** | 451 |
| **Open Issues** | 73 |
| **URL** | https://github.com/TencentCloud/CubeSandbox |
| **Web** | https://cubesandbox.com |

**Descripción:** "Instant, Concurrent, Secure & Lightweight Sandbox Service for AI Agents."

**Análisis detallado:**
- Hardware-level isolation
- Instant startup (tens of ms)
- Concurrent sandboxes
- Tencent Cloud integration
- Cloud-first: diseñado para funcionar con infraestructura Tencent
- README detallado con guías de inicio

**Veredicto:** Ya lo probaste y tuviste problemas. Está muy ligado a Tencent Cloud. Saltar.

---

#### 16. k8e — xiaods/k8e ⭐⭐

**Descripción:** "k8e.sh - OpenSource Agentic AI Sandbox Matrix"

**Análisis detallado:**
- Kubernetes en un solo binario (<100MB)
- CNCF conformant
- Sandbox matrix para AI agents
- Single binary, multi-arch (x86, ARM64, RISC-V)
- 60 segundos para levantar

**Instalación:** Single binary download

**Requiere:** Linux (K8s)

**Veredicto:** Si ya sabes K8s y quieres un sandbox con orquestación. Para uso local es overkill.

---

#### 17. superhq — superhq-ai/superhq ⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 247 |
| **License** | AGPL 3.0 |
| **Forks** | 17 |
| **Open Issues** | 0 |
| **URL** | https://github.com/superhq-ai/superhq |
| **Web** | http://superhq.ai/ |

**Descripción:** "Sandboxed AI agent orchestration platform"

**Análisis detallado:**
- Orquestación de múltiples agentes (Claude Code, Codex) en sandboxes
- Interfaz desktop con terminal (GPUI)
- macOS app (brew cask)
- Alpha temprano: "Expect rough edges, missing features, breaking changes"

**Instalación:** `brew tap superhq-ai/tap && brew install --cask superhq`

**Requiere:** macOS

**Veredicto:** Demasiado temprano para producción. Interesante concepto pero alpha.

---

#### 18. herm — aduermael/herm ⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 192 |
| **License** | MIT |
| **Forks** | 6 |
| **Open Issues** | 14 |
| **URL** | https://github.com/aduermael/herm |
| **Web** | https://hermagent.com |

**Descripción:** "Terminal-native AI coding agent running in containers."

**Análisis detallado:**
- Coding agent CLI containerizado por defecto
- Corre en Docker containers
- Multi-provider: Anthropic, OpenAI, Gemini, Grok, Ollama, Azure, Bedrock
- Auto-build de dev environments (Dockerfile dinámico)
- 100% open-source (incluyendo system prompts)
- Sin aprobaciones — "no permission prompts, ever"

**Instalación:** Go install o releases

**Requiere:** Docker

**Veredicto:** Es un AI coding agent que corre en containers, no un sandbox para agentes. Más competidor de Claude Code que sandbox.

---

#### 19. bouvet — vrn21/bouvet ⭐⭐

**Descripción:** "Isolated code execution sandboxes for AI agents"

**Análisis detallado:**
- Sandbox de ejecución de código
- MCP tools
- Rust nightly
- MIT License

**Veredicto:** Proyecto pequeño, poca tracción. No hay suficiente información.

---

#### 20. matchlock — jingkaihe/matchlock ⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 581 |
| **License** | MIT |
| **Forks** | 30 |
| **Open Issues** | 7 |
| **URL** | https://github.com/jingkaihe/matchlock |

**Descripción:** "Matchlock secures AI agent workloads with a Linux-based sandbox."

**Análisis detallado:**
- Linux-based sandbox para AI agent workloads
- MIT License
- ⚠️ README extenso pero poco claro sobre la arquitectura exacta

**Veredicto:** Prometedor pero la documentación no deja claro cómo usarlo vs las alternativas.

---

#### 21. sandboxed.sh — Th0rgal/sandboxed.sh ⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 433 |
| **License** | None |
| **Forks** | 42 |
| **Open Issues** | 14 |
| **URL** | https://github.com/Th0rgal/sandboxed.sh |
| **Web** | https://sandboxed.sh |

**Descripción:** "Safe runtime for autonomous on-chain AI agents: isolated sandboxes, Library skills, encrypted secrets, and OKX read-only security checks."

**Análisis detallado:**
- Web3/OKX focused
- On-chain AI agents (cripto)
- Encrypted secrets, MCP integration
- Dashboard web y iOS app
- Docker o Ubuntu native
- Build X-Agent Hackathon project

**Veredicto:** Muy especializado para Web3/crypto. No es relevante para uso general.

---

#### 22. ChatClaw — zhimaAi/ChatClaw ⭐⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 285 |
| **License** | GPL 3.0 |
| **Forks** | 55 |
| **Open Issues** | 21 |
| **URL** | https://github.com/zhimaAi/ChatClaw |
| **Web** | https://ichatclaw.com |

**Descripción:** "ChatClaw: Get OpenClaw-like knowledge base personal AI agent in 5 mins. Sandbox-secured, ultra-small 30MB installer for macOS & Windows."

**Análisis detallado:**
- Personal AI agent desktop app
- Sandbox-secured (no especifica cómo)
- Conecta WhatsApp, Telegram, Slack, Discord, Gmail, WeChat, etc.
- Skill Market, Knowledge Base, Memory, MCP, Scheduled Tasks
- 30MB installer, macOS & Windows
- Go backend

**Veredicto:** Es un producto de AI agent, no un sandbox para agentes. No es lo que buscas.

---

#### 23. vArmor — bytedance/vArmor ⭐

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 476 |
| **License** | Apache 2.0 |
| **Forks** | 58 |
| **Open Issues** | 4 |
| **URL** | https://github.com/bytedance/vArmor |
| **Web** | https://varmor.org |

**Descripción:** "vArmor is a cloud-native container hardening system..."

**Análisis detallado:**
- No es un sandbox para agentes
- Es un **hardening system** para containers en K8s
- Usa AppArmor, BPF LSM, Seccomp, Envoy proxy
- Protege containers existentes — no crea entornos aislados para agentes

**Veredicto:** No es relevante. Es seguridad para containers en producción, no sandbox para AI agents.

---

#### 24. databend — databendlabs/databend ⭐ (No es sandbox)

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Rust |
| **Estrellas** | 9,293 |
| **License** | Other |
| **Forks** | 875 |
| **URL** | https://github.com/databendlabs/databend |
| **Web** | https://docs.databend.com |

**Descripción:** "Data Agent Ready Warehouse: One for Analytics, Search, AI, Python Sandbox."

**Análisis detallado:**
- Es un **data warehouse** (como Snowflake) con Python UDF sandbox
- No es un sandbox para AI agents
- Apareció en la búsqueda porque tiene "Python Sandbox" en la descripción
- El sandbox es solo para UDFs dentro del data warehouse

**Veredicto:** No es lo que buscas. Es un warehouse con sandbox para UDFs.

---

#### 25. paro — zunor/paro ⭐ (No es sandbox)

**Descripción:** "An AI-native multi-model database built for agents."

**Análisis detallado:**
- Base de datos multi-model (vector, full-text, graph, relational)
- Sandboxed Python UDFs (como databend)
- Beta, no production-ready
- Rust

**Veredicto:** Es una base de datos, no un sandbox.

---

#### 26. ouros — parcadei/ouros ⭐ (Sandbox especializado)

**Descripción:** "A sandboxed Python runtime for AI agents, written in Rust."

**Análisis detallado:**
- Runtime Python sandboxeado
- Sin filesystem, sin network, sin subprocess, sin environment access
- Persistent REPL sessions con snapshot/restore
- Fork sessions, rewind history
- <1 microsecond startup
- No es un Linux completo — solo Python

**Veredicto:** Interesante para correr Python generado por LLMs, pero no es un sandbox general.

---

#### 27. Agenvoy — pardnchiu/Agenvoy ⭐ (No es sandbox)

**Descripción:** "One command. Multiple models. Each playing to its strength."

**Análisis detallado:**
- Go-native runtime para multi-modelo
- Dispatcher rutea cada paso al mejor modelo
- Subagentes colaboran en un proceso
- No es un sandbox

**Veredicto:** Es un orchestrator de modelos, no un sandbox.

---

#### 28. tsk-tsk — dtormoen/tsk-tsk ⭐ (No es sandbox)

**Descripción:** No disponible en preview (proyecto de task management)

**Veredicto:** No relevante.

---

#### 29. hazmat — dredozubov/hazmat ⭐ (No es sandbox)

**Descripción:** No disponible en preview

**Veredicto:** No parece relevante.

---

#### 30. pmg — safedep/pmg ⭐ (No es sandbox de agentes)

| Campo | Valor |
|-------|-------|
| **Lenguaje** | Go |
| **Estrellas** | 344 |
| **License** | Apache 2.0 |
| **Forks** | 27 |
| **URL** | https://github.com/safedep/pmg |

**Descripción:** "PMG protects developers, AI agents from malicious open source packages using proxy, sandbox and SafeDep's threat intelligence feed."

**Análisis detallado:**
- Protege contra paquetes npm/pip maliciosos
- Proxy + sandbox + threat intelligence
- Blockea antes de instalar
- No es un sandbox para ejecutar agentes

**Veredicto:** Es seguridad de supply chain, no sandbox para agentes.

---

## Tabla Comparativa Final

| Proyecto | Aislamiento | Setup | Linux | macOS | SDK/API | Agent-ready | Stars |
|----------|-------------|-------|-------|-------|---------|-------------|-------|
| **microsandbox** | microVM (HW) | ⚡ Fácil | ✅ | ✅ | Rust/Python/TS/Go | ✅ MCP+Skills | 6,189 |
| **capsule** | WebAssembly | ⚡ Fácil | ✅ | ✅ | Python/TS | ✅ MCP | 284 |
| **ai-jail** | Namespaces | ⚡ Fácil | ✅ | ✅ | CLI | ✅ Wrapper | 497 |
| **agent-os** | V8/WASM | ⚡ Fácil | ✅ | ✅ | TS/npm | ✅ Nativo | 2,933 |
| **shuru** | microVM | ✅ Medio | ⚠️ Exp. | ✅ | TS | ✅ Skills | 746 |
| **greywall** | Kernel LSM | ✅ Medio | ✅ | ✅ | CLI | ✅ Perfiles | — |
| **leash** | Container | ✅ Medio | ✅ | ✅ | CLI/npm | ✅ MCP | 564 |
| **vibebox** | Sandbox | ✅ Medio | ❌ | ✅ | CLI | ⚠️ | 199 |
| **zeroboot** | KVM/COW | ⚠️ Proto | ✅ | ❌ | Python/TS | ⚠️ | 2,339 |
| **k8s-sandbox** | K8s | 🔧 Complejo | ✅ | ✅ | K8s API | ✅ Nativo | 2,319 |
| **gbox** | Container/ADB | ✅ Medio | ❌ | ✅ | CLI/MCP | ✅ MCP | — |

---

## Dónde está cada archivo README

Los READMEs completos están en `sandbox-readmes/readmes/`:

```
sandbox-readmes/
├── analisis.md                          ← Este archivo
├── search_results.json                  ← Resultados de GitHub API
├── download_readmes.py                  ← Script de descarga
└── readmes/
    ├── superradcompany_microsandbox.md  ★ #1
    ├── capsulerun_capsule.md            ★ #2
    ├── akitaonrails_ai-jail.md          ★ #3
    ├── rivet-dev_agent-os.md            #4
    ├── superhq-ai_shuru.md              #5
    ├── GreyhavenHQ_greywall.md          #6
    ├── strongdm_leash.md                #7
    ├── robcholz_vibebox.md              #8
    ├── ashishb_amazing-sandbox.md       #9
    ├── AkihiroSuda_alcless.md           #10
    ├── zerobootdev_zeroboot.md          #11
    ├── kubernetes-sigs_agent-sandbox.md  #12
    ├── babelcloud_gbox.md               #13
    ├── agent-sandbox_agent-sandbox.md   #14
    ├── TencentCloud_CubeSandbox.md      #15
    ├── xiaods_k8e.md                    #16
    ├── superhq-ai_superhq.md            #17
    ├── aduermael_herm.md                #18
    ├── vrn21_bouvet.md                  #19
    ├── jingkaihe_matchlock.md           #20
    ├── Th0rgal_sandboxed.sh.md          #21
    ├── zhimaAi_ChatClaw.md              #22
    ├── bytedance_vArmor.md              #23
    ├── databendlabs_databend.md         #24
    ├── zunor_paro.md                    #25
    ├── parcadei_ouros.md                #26
    ├── pardnchiu_Agenvoy.md             #27
    ├── dtormoen_tsk-tsk.md              #28
    ├── dredozubov_hazmat.md             #29
    └── safedep_pmg.md                   #30
```

---

## Recomendación Final

```
microsandbox  →  El más completo y fácil. Empieza aquí.
     │
     ├── ¿Solo necesitas ejecutar código? → capsule
     │
     ├── ¿Solo proteger tu agente local?  → ai-jail
     │
     ├── ¿Estás en Mac?                   → shuru
     │
     └── ¿Quieres máxima velocidad?       → agent-os (rivet)
```
