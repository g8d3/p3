---
name: sesion-base
version: 3
description: "⭐ SESIÓN BASE — Load ONCE per session (first turn only), not on every turn. If SKILL.md was modified (version changed) since last load in this session, reload. Without this skill the agent has no system context (environment, tools, API keys, git, tmux, VACS, directories, skills). Trigger: session start, version change detection."
---

# Base Session Configuration

Loaded once at session start. If modified by another agent (version bumped), reload on next turn.

---

## Index

- [System Inventory](#system-inventory)
- [Environment & Tools](#environment--tools)
- [Inference Providers](#inference-providers)
- [GitHub CLI & Git](#github-cli--git)
- [tmux & Mobile](#tmux--mobile)
- [AI Agents](#ai-agents)
- [Development Principles: VACS](#development-principles-vacs)
- [Vision 🖼️](#vision-️)
- [Token Savings](#token-savings)
- [Directory Structure](#directory-structure)
- [Chat History / Logs](#chat-history--logs)
- [Software Installation](#software-installation)
- [Active Research](#active-research)
- [Skills](#skills)
- [How skills are loaded by agents](#how-skills-are-loaded-by-agents-agnostic)
- [How to test skills load in a new agent](#how-to-test-skills-load-in-a-new-agent)
- [send-keys vs inline command](#send-keys-vs-inline-command)
- [Immediate Pending](#immediate-pending)
- [Roadmap](#roadmap)

---

## System Inventory

### AI Agents

| Agent | Status | Version | Installation |
|--------|--------|---------|-------------|
| **crush** | ✅ activo | v0.74.1 | `~/.nvm/versions/node/v24.16.0/bin/crush` |
| **opencode** | ✅ activo | v1.15.12 | `~/.opencode/bin/opencode` |
| **hermes** | ✅ actualizado | v0.15.1 | `~/.hermes/` (`hermes update` ejecutado 2026-05-31) |
| **pi** | ❌ no instalado | — | desinstalado, no reintentar |
| **opencode-go** | ❌ no instalado | — | no es un binario separado, es el provider |

### Runtimes / Lenguajes

| Herramienta | Versión | Ruta |
|-------------|---------|------|
| node | v24.16.0 | nvm (`~/.nvm/versions/node/v24.16.0`) |
| npm | 11.15.0 | via nvm |
| go | 1.22.2 | `/usr/local/go` |
| rust | 1.93.1 | rustup (`~/.cargo/bin`) |
| uv | 0.5.18 | `~/.local/share/uv/bin/uv` |
| python | ❌ no system | solo via `uv` |
| bun | ✅ | `~/.bun/bin/bun` |
| deno | ✅ | `~/.deno/bin/deno` |
| java | ✅ | SDKMAN |
| gradle | ✅ | SDKMAN |

### Repositorios Git (SSH)

| Repo | URL | Estado |
|------|-----|--------|
| p1 | `git@github.com:g8d3/p1.git` | ✅ activo |
| p2 | `git@github.com:g8d3/p2.git` | ✅ activo |
| p3 | `git@github.com:g8d3/p3.git` | ✅ activo (principal) |
| agents | `git@github.com:g8d3/agents.git` | ✅ nuevo (skills) |

⚠️ **Git config global no personalizada**: `user.name=Your Name`, `user.email=you@example.com`. Si haces commits fuera de estos repos, los autores saldrán genéricos.

### API Keys / Proveedores (en entorno)

| Variable | Proveedor |
|----------|-----------|
| `OPENCODE_GO_*` (API key, URL, model) | Opencode Go (primario) |
| `OPENCODE_API_KEY` | OpenCode (alias del mismo key) |
| `ZAI_API_KEY` | Z.ai (secundario) |
| `CO_API_KEY` | Cohere |
| `CHUTES_API_TOKEN` | Chutes.ai (MiMo, etc.) |
| `FIRECRAWL_API_KEY` | Firecrawl (web scraping) |
| `GITHUB_TOKEN` | ⚠️ INVALIDO — comentado en ~/.secrets/.env, usar gh auth |
| `HL_API_KEY` | Hyperliquid |
| `FISH_AUDIO_API_KEY` | Fish Audio (TTS) |
| `CEREBRAS_API_KEY` | Cerebras |
| `AGNO_API_KEY` | Agno |
| `BFL_API_KEY` | BFL | 

⚠️ `GOOGLE_API_KEY` y `GEMINI_API_KEY` usan el **mismo valor** (duplicado). Crush usa `GOOGLE_API_KEY`. No hay conflicto real, pero GEMINI_API_KEY es redundante.

### Chat History / Logs Disponibles

| Fuente | Archivo | Tamaño | # Entradas |
|--------|---------|--------|------------|
| OpenCode prompts | `~/.local/state/opencode/prompt-history.jsonl` | 27 KB | ~50 prompts |
| OpenCode frecency | `~/.local/state/opencode/frecency.jsonl` | 1.8 KB | — |
| Factory (historial) | `~/.factory/history.json` | 27 KB | 385 entradas |
| Factory (sesiones) | `~/.factory/sessions/` | varios | ~25 archivos |
| Claude | `~/.claude/history.jsonl` | pequeño | 3 entradas |
| Zsh history | `~/.zsh_history` | 377 KB | ~8500 líneas |
| Crush DB | `~/.crush/crush.db` | 104 KB | SQLite (poco uso) |
| Crush logs | `~/.crush/logs/crush.log` | 14 líneas | minimal |

### Crush Sessions (scattered `.crush` dirs)

Crush guarda una base de datos SQLite por directorio de trabajo. Las sesiones están en:

| Directorio | Base | Tamaño |
|------------|------|--------|
| `~/code/.crush/` | `crush.db` | 844 KB |
| `~/code/p3/s73/.crush/` | `crush.db` | 2.8 MB |
| `~/code/p3/s74/.crush/` | `crush.db` | 6.9 MB |
| `~/code/p3/s75/.crush/` | `crush.db` | ~5 MB (activo) |
| `~/code/aicli/opencode/t1/.crush/` | `crush.db` | 3.9 MB |
| `~/code/p1/s3-web3-w/t7-opencode/.crush/` | `crush.db` | 3.9 MB |

**Total ~23 MB** de historial de sesiones Crush distribuido en 6 bases de datos SQLite.

### Crush Health & Performance

**Crush uses 4 distinct directory locations:**

| Path | Role | Versioned? |
|------|------|-----------|
| `~/.crush/` | Home session DB (legacy) | No |
| `~/.local/share/crush/` | Auto-generated config (providers, projects, models) | No |
| `~/.config/crush/` → `~/code/.agents/dotfiles/crush/` | Manual user config | **Yes** (agents repo) |
| `{project}/.crush/` | Per-project session DB | No |

**If Crush feels slow or CPU is high:**

1. **Check I/O**: `cat /proc/{PID}/io` — look for `write_bytes` > 100MB in short time
2. **Check SQLite WAL**: `ls -lh .crush/crush.db-wal` — large WAL = excessive writes
3. **`auto_summarize`**: Enabled by default. Each turn generates a summary + writes to DB.
4. **Multiple providers**: Crush auto-detects providers in `providers.json`. 9+ providers = health check overhead.

**Config versioning (dotfiles strategy):**

User config under `~/.config/<tool>/` is symlinked into `~/code/.agents/dotfiles/<tool>/` for git tracking:
```bash
mkdir -p ~/code/.agents/dotfiles
mv ~/.config/crush ~/code/.agents/dotfiles/crush
ln -s ~/code/.agents/dotfiles/crush ~/.config/crush
```
This gives `git log` and `git blame` for every config change.

---

## Entorno y Herramientas

- **Python**: Usar siempre `uv` (`uv pip install ...`, `uv run ...`, `uv add ...`, etc.). No hay python3 del sistema.
- **Shell/Comandos**: Preferir comandos event-driven sobre long polling.
- **Mobile-friendly**: Output in ~80 cols, no hover/click dependency, vertically readable Markdown.
- **Rule**: After creating or modifying code, **always run and test it**.
- **Persistence**: Agent-created files go in the **current working directory**, never in `/tmp/` (cleared on reboot).
- **Language**: All output, code, documentation, and comments **must be in English**. The user speaks Spanish, but everything I produce goes in English.
- **Testability**: The agent must run tests and verification commands itself, then show the result. Never ask the user to run commands to verify work.
- **Browser-test before delivery**: Any web app must be loaded and verified in the browser (via Python urllib or similar) before telling the user. Never assume it works — prove it.
- **Human-like testing**: Test everything like a human would — load the page, click buttons, fill forms, check error cases, verify mobile rendering. Don't just run unit tests and assume the UI works.
- **Browser console check**: After loading a page, verify there are no JavaScript console errors (try/catch issues, undefined variables, network errors) and no server-side errors. If you can't use a headless browser, at minimum validate JS syntax and all endpoint responses.
- **Lightweight agents**: For multi-agent parallelism, don't launch heavy CLIs (opencode = ~200MB RAM each). Build a lightweight Python agent (~10MB RAM) that calls the inference API directly via `urllib`. Keep in the project as `agent_light.py`.

### Command transparency (anti-silence)

Before running a potentially slow command:

1. **Announce** what will run and why
2. **Estimate time** (e.g., "git push → 2-5s", "npm install → 30-60s")
3. **Use tmux window with `-d`** for commands >30s or that might hang (git, npm, docker)
4. **Don't leave the user in silence** while it runs

```bash
# Good: announce + visible window
echo "→ git push to g8d3/agents (estimated: 5s)"
tmux new-window -d -n push 'git push 2>&1 | tee push.log; tmux wait-for -S push'
tmux wait-for push
```

### Small commits with multiple agents

When multiple AI agents work on the same project, each change must be committed **atomically and frequently**:

- One commit per logical change (don't batch everything at the end)
- Descriptive message: what changed and why
- Enables: reverting specific changes, understanding history, avoiding agent conflicts
- Prefer `git commit -am "message"` for simple changes
- Push autonomously — don't wait for confirmation

## Inference Providers

- **Opencode go** (primary): Credentials in `OPENCODE_GO_BASE_URL`, `OPENCODE_GO_API_KEY`, `OPENCODE_GO_MODEL`. Provider URL: `https://opencode.ai/zen/go/v1/`. Model: `deepseek-v4-flash`.
- **zai** (secondary): Use only when specified. API key in `ZAI_API_KEY`.

## GitHub CLI & Git

- `gh` v2.45.0 installed and authenticated as `g8d3` (device flow, keyring).
- **Important**: `gh` defaults to HTTPS. Existing repos use SSH. Prefer SSH.
- If using `gh repo create`, switch remote to SSH afterward: `git remote set-url origin git@github.com:{user}/{repo}.git`.
- `GITHUB_TOKEN` env var is **invalid** — `gh` ignores it (uses keyring token). For manual operations, `unset GITHUB_TOKEN` before using `gh` or git.

## tmux & Mobile

- Always use windows, never panes — mobile friendly.
- The agent creates and manages tmux windows, not the user.

### Event-driven tmux pattern (no focus stealing)

Always use `-d` to avoid changing the current window's focus:

```bash
tmux new-window -d -n my-process \
  'bash -c "command; touch my-process.done; tmux wait-for -S my-process"'
tmux wait-for my-process
cat my-process.done
```

**Forbidden**: `sleep N`, `read` at the end. Always `-d`. Files in current directory, never `/tmp/`.

### Multi-agent orchestration via tmux

For large tasks (e.g., processing all sessions), launch separate agents in tmux windows:

```bash
# 1. Prepare input data
uv run python3 extractor.py > task.txt

# 2. Launch analyzer agent
tmux new-window -d -n analysis \
  'opencode run "Analyze this file: task.txt" > result.txt 2>/dev/null; touch analysis.done; tmux wait-for -S analysis'

# 3. Wait (event-driven)
tmux wait-for analysis

# 4. Read result
cat result.txt
```

Each agent works in its own window with its own context. The coordinator (me) waits for signals and synthesizes results.

### Danger: orphaned processes

Commands that spawn children (git, npm, docker) can leave **orphans** that re-parent to Crush and freeze the TUI. **Do not run directly via bash tool**. Use a separate tmux window:

```bash
tmux new-window -d -n git-push \
  'git push origin main > git-push.log 2>&1; touch git-push.done; tmux wait-for -S git-push'
tmux wait-for git-push
cat git-push.log
```

### Resource responsibility

Whoever opens a tmux window, background process, or any resource is responsible for closing/cleaning it after use. This includes tmux windows, `nohup` processes, temp files, and test logs. If not explicitly closed, the resource remains orphaned.

**High-risk commands**: `git push/clone/fetch` (HTTPS), `npm install`, `docker build/pull`, `ssh`, `nohup ... &`.

### Current working directory

All files created by agents go in the current working directory:
- Command logs: `git-push.log`
- Analysis results: `task-result.txt`
- Install scripts: `install-{name}.sh`
- Signal files: `{task}.done`

**Never use `/tmp/`** — it clears on reboot. Files persist in the current project directory.

## AI Agents

Preference order: **crush → opencode → hermes → pi**

1. **crush** — primary agent
2. **opencode** — robust alternative, with plugin system (oh-my-opencode-slim)
3. **hermes** — experimental, outdated (run `hermes update`)
4. **pi** — not installed, do not use

## Development Principles: VACS

| Principle | Description |
|-----------|-------------|
| **V**isibility | Logs, metrics, tracing. Everything observable. |
| **A**utonomy | Self-execution, self-recovery, no constant human intervention. |
| **C**onfigurability | Nothing hardcoded: YAML/JSON/env vars for everything. |
| **S**elf-improvement | Auto-tuning, evolution, learning from errors, skills from history. |

Research stack: orchestration, persistent memory, security/sandboxing, multi-agent frameworks.

## Vision 🖼️

Per own benchmarks: **Mimo v2.5** (non-pro) is best in speed/cost for vision tasks.

## Token Savings

- Structured output (JSON) over free text
- Compressed prompts
- Frequent response caching
- Small models for simple tasks
- Minimum necessary context

## Estructura de Directorios

```
~/
  .agents/        → skills + config (git: g8d3/agents)
  .crush/         → Crush home session DB
  .config/crush/  → Crush manual config → symlink to ~/code/.agents/dotfiles/crush/
  .config/opencode/ → OpenCode config
  .hermes/        → Hermes agent (config.yaml, logs)
  .factory/       → Factory agent (history, sessions, config)
  .plano/         → Plano (task runner)
  .claude/        → Claude Code data

  code/
    .agents/ → symlink to ~/.agents/
    p1/ → git@github.com:g8d3/p1.git
    p2/ → git@github.com:g8d3/p2.git (single project)
    p3/ → git@github.com:g8d3/p3.git (~2GB, 50+ projects)
    aicli/ → opencode experiments
    ctrader/ → gpt-researcher fork
    keys/ → JSON keys
    Siftly/ → Next.js app
    spacebot/ → Rust projects
    trojandocs/ → documentation
```

### Internal p{N} structure

```
p{N}/
  s{NN}-{name}/
    README.md
    src/ or app/ or backend/ + frontend/
  FOLDER_INDEX.md  (p3 only)
  reindex.sh       (p3 only)
```

### Tip: symlink `code/.agents` → `~/.agents`

`~/code/.agents` is a symlink to `~/.agents/`. Used so filex (which serves `~/code/` as root) can expose the skills folder in the browser.

```
~/code/.agents -> ~/.agents
```

If filex's root changes, the symlink may not be needed. If removed, recreate with:
```bash
ln -s ~/.agents ~/code/.agents
```

## Chat History / Logs

Available history sources (for eventual pattern extraction and auto-skills):

| Source | Path | Type |
|--------|------|------|
| OpenCode | `~/.local/state/opencode/prompt-history.jsonl` | JSONL prompts |
| OpenCode (logger) | `~/.local/state/opencode/assistant-history.jsonl` | JSONL plugin |
| Factory | `~/.factory/history.json` | JSON command array |
| Factory sessions | `~/.factory/sessions/` | Per-project directories |
| Shell | `~/.zsh_history` | Text |
| Claude | `~/.claude/history.jsonl` | JSONL (~3 entries) |
| Crush | `~/.crush/crush.db` | SQLite (minimal history) |

## Software Installation

When the agent cannot install directly:

1. Create a self-contained script at `install-{name}.sh`
2. Script must be idempotent, with validations, no interaction
3. Run in a separate tmux window (event-driven pattern)
4. Don't use `read` or wait for input

## Active Research

Active research topics:
- Multi-agent orchestration
- Persistent memory and RAG
- Security and sandboxing
- Agent frameworks (Agno, LangChain, CrewAI)
- Model benchmarking (vision, code, reasoning, cost)
- Token savings strategies

## Skills

### How skills are loaded by agents (agnostic)

Each agent (Crush, OpenCode, Hermes) decides when to load a skill based on **semantic matching** between the `description:` in the frontmatter and the user's current message. The agent reads the description, compares it to what the user asks, and if it matches, loads the SKILL.md.

**Key rule**: the description should describe the **activation condition** (when to load), not the skill's content. If the description says "contains system configuration", the model only loads the skill when the user explicitly asks about configuration. If it says "always load on any message", the model understands to load it even with a "hello".

**Working formula**:
```
description = activation condition + consequence of not loading
```

Example: `"MANDATORY: load on receiving ANY message. Without this skill the agent has no system context."`

### How to test skills load in a new agent

```bash
# 1. Open tmux window with the agent (env vars NOT inherited)
tmux new-window -d -n test-agent

# 2. Send keys: source env + start agent
tmux send-keys -t test-agent 'source ~/.secrets/.env && crush' Enter

# 3. Send a generic initial message
tmux send-keys -t test-agent 'hello, prepare the environment' Enter

# 4. Verify it responded with the skill loaded
sleep 5
tmux capture-pane -t test-agent -p -S -20

# 5. Close window when done
tmux kill-window -t test-agent
```

**Note**: agents in a new tmux window **don't inherit `~/.secrets/.env`** because tmux doesn't run full `.zshrc`. Always `source` it first, or the agent will appear with no providers configured.

### send-keys vs inline command

| Method | Advantage | Disadvantage |
|--------|-----------|-------------|
| `tmux new-window -d -n x 'command'` | Simple, event-driven | No env inheritance, hard with interactive |
| `tmux send-keys -t x 'cmd' Enter` | Simulates real typing, works with interactive | More steps, not event-driven |

For **interactive agents** (crush, opencode), always use `send-keys`. For **batch commands** (git, npm), use inline with event-driven pattern.

### Active

| Skill | Path | Purpose |
|-------|------|---------|
| `sesion-base` | `.agents/skills/sesion-base/` | ⭐ This — base session configuration |
| `cdp` | `.agents/skills/cdp/` | Chrome DevTools Protocol + agent-browser |
| `screen-debug` | `.agents/skills/screen-debug/` | GUI debugging (vision + accessibility) |
| `reindex-proyectos` | `.agents/skills/reindex-proyectos/` | Reindex projects in p3 |

### Disabled (installed but inactive)

`agent-browser`, `browser`, `simplify`, `agent-test`, `obs`, `video-review`, `webreel`, `tts-chutes`

---

## Immediate Pending

### ✅ Resolved (2026-05-31)
- [x] **Git config**: user.name = g8d3, user.email = g8d3@users.noreply.github.com
- [x] **GITHUB_TOKEN**: commented out in `~/.secrets/.env` (invalid). `gh` uses keyring.
- [x] **Hermes update**: v0.13.0 → v0.15.1 (1833 commits)
- [x] **GOOGLE_API_KEY vs GEMINI_API_KEY**: same value, no conflict
- [x] **tmux focus**: documented use `-d` in new-window to not steal focus
- [x] **Crush sessions**: identified 6 distributed databases (~23 MB total)

### ✅ Resolved (2026-06-01)
- [x] **Crush config**: Moved to `~/code/.agents/dotfiles/crush/` with symlink from `~/.config/crush/`
- [x] **Skill versioning**: Added `version` field to frontmatter; description now says "load once per session, reload on version change"
- [x] **Language rule**: All output, code, docs, and comments in English

### Pending
- [ ] **Extract patterns from history**: Use Crush session DBs + OpenCode history + Factory history to create auto-skills

---

## Roadmap

### Short term
- [ ] `auto-skills`: Extract patterns from history and generate skills
- [ ] Improve `screen-debug` (vision/debugging)
- [ ] Fix global git config
- [ ] Update hermes
- [ ] Decide GOOGLE_API_KEY vs GEMINI_API_KEY

### Medium term
- [ ] Sandbox for code execution
- [ ] Persistent memory between sessions (RAG)
- [ ] Token savings dashboard
- [ ] Centralized logging system for agents

### Long term
- [ ] Auto-evolution of skills from full history
- [ ] Multi-agent orchestrator with VACS
- [ ] Automated vision benchmarks
- [ ] Project-to-video/content conversion
- [ ] Integrate .factory legacy data with current system

---

*Review completed 2026-05-31. Next review: when tools or structure change.*

### Python web server pitfalls

When building an HTTP server with `http.server`:

- **`HTTPServer` is single-threaded**: SSE blocks all requests. Use `ThreadingHTTPServer`.
- **`_respond()` must handle bytes**: `isinstance(data, bytes)` → `wfile.write(data)` directly. Never JSON-serialize bytes.
- **SQLite + threads**: `check_same_thread=False` when using from threaded handlers.
- **Content-Type matters**: HTML → `text/html`. Wrong type = raw text in browser.
