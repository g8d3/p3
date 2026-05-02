# Terminal AI Chat Application

A lightweight terminal-based AI chat application with full transparency features.

## Features

- **CRUD Operations** for:
  - Providers (OpenAI, Anthropic, Ollama, Local)
  - Models (per-provider configurations)
  - Agents (custom system prompts)
  - Sessions (chat history persistence)
  - Tools (custom execution tools)
  - Schedules (automated tasks)

- **Transparency Features**:
  - Real-time request/response logging
  - Response timing (latency, TTFT)
  - Token per second metrics
  - Cost tracking
  - All API calls visible

- **Requirements**:
  - Lightweight (minimal dependencies)
  - Terminal-based (curses UI)
  - SQLite persistence
  - Modular provider system

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Controls

- `/` - Command mode
- `c` - Clear chat
- `s` - Switch session
- `a` - Select agent
- `m` - Select model
- `p` - Manage providers
- `g` - Manage agents
- `t` - Manage tools
- `h` or `?` - Help
- `q` - Quit

## Configuration

Default providers and models are created on first run. Set environment variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

## Architecture

```
main.py          - Entry point
core/
  app.py         - Main application
  database.py    - SQLite CRUD
  ui.py          - Terminal UI
  config.py      - Configuration
providers/
  base.py        - Provider interface
  openai.py      - OpenAI implementation
  anthropic.py   - Anthropic implementation
  ollama.py      - Ollama implementation
  local.py       - Local/vLLM implementation
agents/
  base.py        - Agent interface
  agent.py       - Agent implementations
tools/
  base.py        - Tool interface
  tool.py        - Tool implementations
schedules/
  scheduler.py   - Task scheduler
```
