```markdown
# Análisis de ~/.zsh_history (8505 comandos, 506 días)

**Período:** 2025-01-09 → 2026-05-31
**Promedio:** ~17 comandos/día | **Pico:** 15–17 hs
**Días activos:** lun–vie (intenso), sáb–dom (menos)

---

## 1. Herramientas más usadas

### Comandos base (top 30 por frecuencia bruta)

| # | Comando | Ocurrencias | % del total |
|---|---------|-------------|-------------|
| 1 | `l` (ls -la) | 498 | 5.9% |
| 2 | `cd` | 440 | 5.2% |
| 3 | `opencode` | 415 | 4.9% |
| 4 | `vim` | 346 | 4.1% |
| 5 | `mcd` (mkdir+cd) | 336 | 3.9% |
| 6 | `sudo` | 303 | 3.6% |
| 7 | `echo` | 292 | 3.4% |
| 8 | `npm` | 209 | 2.5% |
| 9 | `uv` | 198 | 2.3% |
| 10 | `python` | 158 | 1.9% |
| 11 | `docker` | 148 | 1.7% |
| 12 | `curl` | 146 | 1.7% |
| 13 | `gst` (git status) | 126 | 1.5% |
| 14 | `openclaw` | 117 | 1.4% |
| 15 | `code` (VS Code) | 113 | 1.3% |
| 16 | `node` | 111 | 1.3% |
| 17 | `npx` | 109 | 1.3% |
| 18 | `brave-browser` | 73 | 0.9% |
| 19 | `htop` | 70 | 0.8% |
| 20 | `agent-browser` | 67 | 0.8% |

### Git (alias + nativos)

| Comando | Uso |
|---------|-----|
| `gst` (git status) | 127 |
| `gp` (git push) | 244 |
| `ga` (git add) | 180 |
| `gl` (git log/pull) | 144 |
| `gc` (git commit) | 123 |
| `gd` (git diff) | 24 |
| `git clone` | 15 |
| `git commit -m` | 89 (en cadena `ga .. && gc -m "$(date)" && gpr && gp`) |

**Flujo dominante:** `ga . && gc -m "$(date)" && gpr && gp` — commit+push automático con timestamp.

### AI / LLM

| Herramienta | Uso | Rol |
|-------------|-----|-----|
| `opencode` | 662 | Orquestador principal de código |
| `openclaw` | 163 | Gateway de modelos / MCP |
| `ollama` | 73 | Modelos locales |
| `agent-browser` | 72 | Browser automation (CDP) |
| `gemini` | 62 | Modelo Google |
| `agno` | 51 | Framework multi-agente |
| `aichat` | 50 | CLI chat con LLMs |
| `claude` | 20 | Modelo Anthropic |
| `langchain` | 15 | Framework LangChain |
| `openai` | 14 | API OpenAI |
| `gpt` | 8 | Referencia genérica GPT |

**14 tecnologías AI distintas detectadas.**

### Editores y monitoreo

| Herramienta | Uso |
|-------------|-----|
| `code` (VS Code) | 2057 |
| `vim` | 350 |
| `tmux` | 78 |
| `htop` | 73 |

---

## 2. Flujos de trabajo frecuentes

### 🔁 Commit & Push automatizado (el más repetido ~80x)
```
ga . && gc -m "$(date)" && gpr && gp
```
Commit diario con timestamp, push automático.

### 🐳 Docker: ciclo de contenedores
```
docker rm -f <container>     →  26x
docker run -d <image>        →  19x
docker compose up            →  17x
docker ps -a                 →  14x
docker system prune          →   8x
```
Uso intensivo de Docker para servicios efímeros.

### 🌐 Brave browser + CDP (debugging)
```
brave-browser --user-data-dir=... --remote-debugging-port=9222
```
Apertura de Brave con remote debugging para automation.

### 🤖 agent-browser (CDP control)
```
agent-browser --cdp ... snapshot
agent-browser --cdp ... tab
```

### 📁 Navegación de proyectos (estructura `p3/s{N}`)
```
mcd ~/code/p3/s41
mcd ~/code/p3/s40
mcd ~/code/p3/s20
...
```
Creación y entrada a directorios de proyectos secuenciales (p3/s1–s75).

### 🐍 Python: setup de proyectos
```
uv venv
source .venv/bin/activate
uv pip install -e .
```
Toolchain moderna con `uv` (reemplazando `pip`/`poetry`).

### 🚀 opencode: desarrollo asistido por AI
```
opencode                    →  31x (invocación directa)
opencode --help             →  16x
opencode serve              →  15x (servicio)
opencode web                →   8x
```

---

## 3. Tecnologías que aparecen

### Lenguajes de programación

| Lenguaje | Ocurrencias |
|----------|-------------|
| Python | 967 |
| TypeScript | 379 |
| Go | 180 |
| Node.js | 157 |
| Rust | 63 (cargo) + 11 (rustup) + 10 (rustc) |
| Bun | 33 |
| Deno | 4 |

### Package managers

| Herramienta | Ocurrencias |
|-------------|-------------|
| npm | 252 |
| uv (Python) | 235 |
| pip | 157 |
| apt | 136 |
| npx | 129 |
| cargo (Rust) | 63 |
| pnpm | 50 |
| gem (Ruby) | 77 |

### Infraestructura

| Tecnología | Ocurrencias |
|------------|-------------|
| Docker | 263 |
| systemd/systemctl | 36 |
| Tailscale | 6 |
| Nix/NixOS | indicios |

### Redes y debugging

| Herramienta | Ocurrencias |
|-------------|-------------|
| ss | 237 |
| ip | 162 |
| curl | 162 |
| netstat | 39 |
| ssh | 33 |
| lsof | 24 |
| ifconfig | 18 |

### Bases de datos

| Herramienta | Ocurrencias |
|-------------|-------------|
| sqlite3 | 19 |
| psql (PostgreSQL) | 1 |

### Testing / Build

| Herramienta | Ocurrencias |
|-------------|-------------|
| make | 14 |
| entr (file watcher) | 10 |
| task (task runner) | 7 |
| pytest | 3 |
| jest | 5 |
| just | 2 |

### Custom aliases detectados

| Alias | Expansión probable | Uso |
|-------|--------------------|-----|
| `l` | `ls -la` / `eza -la` | 498 |
| `gst` | `git status` | 127 |
| `ga` | `git add` | 180 |
| `gc` | `git commit` | 123 |
| `gp` | `git push` | 244 |
| `gpr` | `git pull --rebase` | 106 |
| `gl` | `git log` / `git pull` | 144 |
| `mcd` | `mkdir -p && cd` | 336 |
| `gd` | `git diff` | 24 |
| `md` | `mkdir -p` | 38 |
| `pi` | `pip install` | 43 |
| `crush` | script/alias personal | 56 |
| `hermes` | CLI personal para modelos | 46 |

---

## Resumen ejecutivo

**Es un entorno de engineer full-stack + AI.** La persona trabaja principalmente en:
- **Python** (uv/pip + venv) y **TypeScript** (npm/pnpm) como lenguajes principales
- **AI/LLMs** como capa central: opencode (orquestador), openclaw (gateway), agent-browser (automation), ollama/gemini/claude (modelos)
- **Docker** como infraestructura de servicios
- **Git** con workflow automatizado de commit+push
- **Estructura de proyectos secuencial** (`p3/s{N}`) — sugiere iteraciones o sprints numerados
- **Horario laboral** intenso 10–21hs, con picos a las 15–17hs
- **Herramientas de sistema** Linux avanzadas (ss, ip, systemctl, docker, brave-browser con CDP)
```
