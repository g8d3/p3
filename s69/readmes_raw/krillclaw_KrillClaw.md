<p align="center">
  <img src="https://krillclaw.com/assets/krillclaw-logo.svg" alt="KrillClaw" width="120" />
</p>

<h1 align="center">KrillClaw</h1>
<p align="center"><strong>The AI agent runtime that fits on a microcontroller.</strong></p>

<p align="center">
  <a href="https://github.com/krillclaw/KrillClaw/actions"><img src="https://img.shields.io/github/actions/workflow/status/krillclaw/KrillClaw/test.yml?branch=main&style=flat-square&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSL_1.1-blue?style=flat-square" alt="License: BSL 1.1"></a>
  <img src="https://img.shields.io/badge/language-Zig_0.15+-f7a41d?style=flat-square&logo=zig&logoColor=white" alt="Zig 0.15+">
  <img src="https://img.shields.io/github/languages/code-size/krillclaw/KrillClaw?style=flat-square&color=green" alt="Code size">
  <img src="https://img.shields.io/badge/binary-~450KB-00ff88?style=flat-square" alt="Binary size">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen?style=flat-square" alt="Zero deps">
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#why-krillclaw">Why KrillClaw?</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#profiles">Profiles</a> •
  <a href="#embedded-mode">Embedded</a> •
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

~450KB binary. 0 dependencies. 19 source files. 50+ validated device targets. Runs on a $3 microcontroller or a cloud server.

KrillClaw is an autonomous AI agent runtime written in Zig. It connects to 20+ LLM providers (Claude, OpenAI, Ollama + 17 via `--base-url`), executes tools, and loops until the task is done. Includes cron scheduling, persistent KV store, MCP support, 7 messaging channels, GPIO/hardware control, and BLE/Serial transports for edge devices.

```
 ┌──────────────────────────────────────────────────────┐
 │                                                      │
 │   ~450 KB.  Zero deps.  Boots in <10ms.              │
 │   The entire agent runtime — LLM client, tool        │
 │   executor, JSON parser, SSE streaming, cron,        │
 │   KV store, context mgmt — in 4,576 lines of Zig.   │
 │                                                      │
 └──────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install Zig 0.15+ → https://ziglang.org/download/
# 2. Clone and build (takes ~1 second)
git clone https://github.com/krillclaw/KrillClaw.git
cd KrillClaw
zig build -Doptimize=ReleaseSmall

# 3. Set your API key and go
export ANTHROPIC_API_KEY=sk-ant-...
./zig-out/bin/krillclaw "create a REST API in Go with user auth"
```

That's it. No npm install. No pip. No Docker. Just Zig and a binary.

## Why KrillClaw?

**Every AI agent runtime is massive.** Desktop coding agents ship as 50–500MB bundles with hundreds of dependencies. The actual logic — "call LLM, parse response, execute tools, repeat" — shouldn't need any of that.

KrillClaw proves it doesn't. The same agentic loop that powers desktop tools, compiled to a binary smaller than a JPEG, running on hardware that costs less than a coffee.

**KrillClaw exists because AI agents should run everywhere** — not just on machines with Node.js and 8GB of RAM.

### The Numbers

| | KrillClaw | Typical Edge Runtime | Desktop Agent |
|---|:---:|:---:|:---:|
| **Binary** | **~450 KB** | 2–8 MB | 50–500 MB |
| **RAM** | **~2 MB** | 10–512 MB | 150 MB – 1 GB |
| **Source** | **4,576 LOC** | 5–30K LOC | 30–100K+ LOC |
| **Dependencies** | **0** | 10–100+ | 100–1000+ |
| **Boot time** | **<10 ms** | <1s | 2–5s |
| **Embedded/BLE** | **Yes** | Sometimes | No |
| **Cron/Daemon** | **Yes** | Sometimes | No |

### vs Embedded/Edge Runtimes

| Feature | KrillClaw | MimiClaw | PicoClaw |
|---------|:---------:|:--------:|:--------:|
| **Language** | Zig | Python | Go |
| **Binary size** | ~450 KB | ~2 MB | ~8 MB |
| **RAM usage** | ~2 MB | ~512 KB* | ~10 MB |
| **Dependencies** | 0 | pip | Go modules |
| **BLE transport** | ✅ | ❌ | ❌ |
| **Serial transport** | ✅ | ❌ | ❌ |
| **Multi-provider** | 20+ (Claude, OpenAI, Ollama + 17 via `--base-url`) | 2 | 1 |
| **SSE streaming** | ✅ | ❌ | ❌ |
| **Inline tests** | 60 | 0 | Limited |
| **Sandbox mode** | ✅ | ❌ | ❌ |
| **MCP support** | ✅ | ❌ | ❌ |
| **Channels** | 7 (Telegram, Discord, Slack, WhatsApp, MQTT, WebSocket, Webhook) | 2 | N/A |
| **GPIO / hardware** | ✅ (GPIO, I2C, SPI) | ✅ (GPIO) | ❌ |
| **License** | BSL 1.1 | MIT | MIT |

*Competitor data as of Feb 2026. Check their repos for current numbers.*

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        KrillClaw                             │
│                                                              │
│  ┌─────────┐    ┌──────────┐    ┌────────────┐              │
│  │  main    │───▶│  agent   │───▶│  tools     │              │
│  │  (CLI)   │    │  (loop)  │    │  (dispatch)│              │
│  └─────────┘    └────┬─────┘    └─────┬──────┘              │
│                      │                │                      │
│                 ┌────▼─────┐    ┌─────▼──────────────┐      │
│                 │   api    │    │  tools_coding.zig   │      │
│                 │ (client) │    │  tools_iot.zig      │      │
│                 └────┬─────┘    │  tools_robotics.zig │      │
│                      │          └────────────────────┘      │
│               ┌──────▼──────┐                                │
│               │  transport  │  ◀── vtable dispatch           │
│               └──┬────┬──┬──┘                                │
│                  │    │  │                                    │
│              ┌───▼┐ ┌▼──▼┐                                   │
│              │HTTP│ │BLE │ │Serial│                           │
│              └────┘ └────┘ └──────┘                           │
│                                                              │
│  Support: json.zig │ stream.zig │ context.zig │ config.zig  │
│           types.zig │ arena.zig                              │
└─────────────────────────────────────────────────────────────┘

19 files. 4,576 lines. Zero dependencies.
```

### Source Map

| File | Lines | Role |
|------|------:|------|
| `main.zig` | 198 | CLI, REPL, cron daemon entry point |
| `agent.zig` | 215 | Agent loop + FNV-1a stuck-loop detection |
| `api.zig` | 341 | Multi-provider HTTP client (Claude/OpenAI/Ollama) |
| `stream.zig` | 362 | SSE streaming parser |
| `json.zig` | 519 | Hand-rolled JSON parser/builder — zero deps |
| `tools.zig` | 191 | Tool dispatcher — comptime profile + shared tools |
| `tools_shared.zig` | 362 | Shared tools: time, KV, web search, sessions, OTA (all profiles) |
| `tools_coding.zig` | 484 | Coding profile: bash, read/write/edit, search, list, patch |
| `tools_iot.zig` | 176 | IoT profile: MQTT, HTTP, device info |
| `tools_robotics.zig` | 153 | Robotics profile: commands, e-stop, telemetry |
| `context.zig` | 226 | Token estimation + priority-based truncation |
| `config.zig` | 202 | Config: file → env → CLI precedence |
| `cron.zig` | 206 | Cron/heartbeat scheduler for daemon mode |
| `transport.zig` | 179 | Abstract vtable transport + RPC protocol |
| `types.zig` | 157 | Core types: Provider, Message, Config, ToolDef |
| `ble.zig` | 159 | BLE GATT transport (protocol + simulation) |
| `serial.zig` | 142 | UART/serial transport (Linux/macOS) |
| `arena.zig` | 200 | Fixed arena allocator for embedded targets |
| `react.zig` | 104 | ReAct reasoning loop |

## Profiles

Compile-time profiles select different tool sets. Only the selected profile's code ships in the binary — zero runtime overhead.

```bash
# Coding agent (default)
zig build -Dprofile=coding -Doptimize=ReleaseSmall

# IoT agent — MQTT, HTTP, KV store, device info
zig build -Dprofile=iot -Doptimize=ReleaseSmall

# Robotics agent — motion commands, e-stop, telemetry
zig build -Dprofile=robotics -Doptimize=ReleaseSmall
```

| Profile | Tools | Binary Size | Security Policy |
|---------|-------|:-----------:|-----------------|
| **coding** | bash, read/write/edit, search, list, patch + shared | ~459 KB | bash behind approval gate, writes restricted to cwd |
| **iot** | MQTT pub/sub, HTTP, GPIO, I2C, SPI, device info + shared | ~463 KB | no bash, no file writes, 30 req/min rate limit |
| **robotics** | robot_cmd, estop, telemetry + shared | ~473 KB | no bash, bounds checking, 10 cmd/s, e-stop |

All profiles include **shared tools** available across every profile:
- `get_current_time` — ISO-8601 timestamp
- `kv_get` / `kv_set` / `kv_list` / `kv_delete` — persistent key-value store

All profiles support sandbox mode: `zig build -Dsandbox=true`

## Cron / Heartbeat (Daemon Mode)

Run KrillClaw as a scheduled agent on edge devices:

```bash
# Run agent every 5 minutes with a custom prompt
krillclaw --cron-interval 300 --cron-prompt "check sensors and report anomalies"

# Heartbeat every 60 seconds + agent every 10 minutes
krillclaw --heartbeat 60 --cron-interval 600

# Run 10 times then exit
krillclaw --cron-interval 120 --cron-max-runs 10 --cron-prompt "collect data"
```

Designed for edge devices running data collection cycles between connectivity windows (BLE, Serial). The scheduler has minimal binary cost (~2KB) and uses no threads.

## Providers

KrillClaw supports **20+ LLM providers** through three protocol backends. Any provider with an OpenAI-compatible API works via `--base-url`.

| Provider | Models | Auth |
|----------|--------|------|
| **Claude** | claude-sonnet-4-5, claude-opus-4, etc. | `ANTHROPIC_API_KEY` |
| **OpenAI** | gpt-4o, gpt-4-turbo, etc. | `OPENAI_API_KEY` |
| **Ollama** | llama3, codellama, mistral, etc. | None (local) |
| **+ 17 more** | via `--base-url` | Provider-specific |

```bash
# Claude (default)
./zig-out/bin/krillclaw "fix the tests"

# OpenAI
export OPENAI_API_KEY=sk-...
./zig-out/bin/krillclaw --provider openai -m gpt-4o "fix the tests"

# Local Ollama
./zig-out/bin/krillclaw --provider ollama -m llama3 "explain this code"

# Groq (ultra-fast inference)
KRILLCLAW_API_KEY=gsk_... ./zig-out/bin/krillclaw \
  --provider openai --base-url https://api.groq.com/openai \
  -m llama-3.3-70b-versatile "optimize this function"

# DeepSeek (cost-effective coding)
KRILLCLAW_API_KEY=sk-... ./zig-out/bin/krillclaw \
  --provider openai --base-url https://api.deepseek.com \
  -m deepseek-chat "refactor this module"

# Together AI (open-source models)
KRILLCLAW_API_KEY=... ./zig-out/bin/krillclaw \
  --provider openai --base-url https://api.together.xyz \
  -m meta-llama/Llama-3.1-70B-Instruct-Turbo "write tests"

# Google Gemini (via OpenAI compatibility layer)
KRILLCLAW_API_KEY=... ./zig-out/bin/krillclaw \
  --provider openai \
  --base-url https://generativelanguage.googleapis.com/v1beta/openai \
  -m gemini-2.0-flash "summarize this repo"
```

See [Docs/PROVIDERS.md](Docs/PROVIDERS.md) for the full list of 20+ supported providers with base URLs, tool calling support, and configuration examples.

## MCP Support

KrillClaw integrates with [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) servers, connecting your agent to 1000+ tools.

```bash
# Configure MCP servers in ~/.krillclaw/mcp_servers.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
    }
  }
}

# Start with MCP tools available
python bridge/bridge.py --serve --channels webhook
```

MCP tools are namespaced as `servername__toolname` and automatically available to the agent. Supports stdio and streamable HTTP transports.

## Channels

7 messaging channels — your agent talks wherever your users are:

| Channel | Library | Auth |
|---------|---------|------|
| **Telegram** | stdlib (urllib) | Bot token |
| **Discord** | discord.py | Bot token |
| **Slack** | slack-bolt | Bot + App token (Socket Mode) |
| **WhatsApp** | Cloud API (Meta) | Business access token |
| **MQTT** | paho-mqtt | Broker config |
| **WebSocket** | websockets | Token auth |
| **Webhook** | stdlib (http.server) | Bearer token |

```bash
# Start multi-channel server
python bridge/bridge.py --serve --channels telegram,discord,webhook
```

## GPIO / Hardware Control

Direct hardware control from AI — GPIO, I2C, SPI:

```bash
# IoT profile includes GPIO tools
zig build -Dprofile=iot -Doptimize=ReleaseSmall

# GPIO tools route through the Python bridge
# Linux: real hardware via libgpiod
# macOS: simulator mode (logs commands)
```

| Tool | Description |
|------|-------------|
| `gpio_read` | Read a GPIO pin value |
| `gpio_write` | Write a value to a GPIO pin |
| `gpio_list` | List available GPIO pins |
| `i2c_read` | Read from an I2C device |
| `spi_transfer` | Transfer data over SPI |

Safety: pin allowlist via `~/.krillclaw/hardware.json`, rate limiting on writes.

## Embedded Mode

KrillClaw targets microcontrollers. The device runs the agent brain. A phone or laptop bridges to the internet.

```
┌─────────────┐       BLE/UART       ┌──────────────┐      HTTPS      ┌─────────┐
│  KrillClaw  │ ◄──────────────────► │    Bridge     │ ◄────────────► │  LLM    │
│  (device)   │                      │  (phone/PC)   │                │  API    │
│             │  "call bash ls"      │               │                └─────────┘
│ Agent loop  │ ────────────────►    │ Execute tools │
│ JSON parse  │                      │ Return result │
│ State mgmt  │ ◄────────────────   │               │
│    ~50 KB   │  "file1 file2..."    │  bridge.py    │
└─────────────┘                      └───────────────┘
```

### Build for Hardware

```bash
# BLE transport
zig build -Dble=true -Doptimize=ReleaseSmall

# Serial/UART transport
zig build -Dserial=true -Doptimize=ReleaseSmall

# Bare-metal (no OS)
zig build -Dembedded=true -Dtarget=thumb-none-eabi -Doptimize=ReleaseSmall
```

### Target Hardware

| Device | SoC | RAM | Flash | Cost |
|--------|-----|-----|-------|-----:|
| **ESP32-C3** | RISC-V | 400 KB | 4 MB | $3 |
| **Raspberry Pi Pico W** | RP2040 | 264 KB | 2 MB | $6 |
| **Colmi R02** (smart ring) | BlueX RF03 | ~32 KB | ~256 KB | $20 |
| **nRF52840-DK** | nRF52840 | 256 KB | 1 MB | $40 |
| **nRF5340-DK** | nRF5340 | 512 KB | 1 MB | $50 |

### Fixed Arena Allocator

For devices with no OS heap:

```zig
var mem = arena.Arena32K.init();  // 32KB — fits on nRF5340
const alloc = mem.allocator();
// ... use alloc for everything ...
mem.reset();  // Frees everything at once between agent turns
```

Preset sizes: `Arena4K`, `Arena16K`, `Arena32K`, `Arena128K`, `Arena256K`.

## Transport Layers

| Transport | Use Case | Status |
|-----------|----------|--------|
| **HTTP** | Desktop — direct HTTPS to API | Stable |
| **BLE** | Embedded — GATT protocol + desktop simulation via Unix socket | Experimental |
| **Serial** | Dev boards — UART to host machine | Experimental |

> **BLE note:** The BLE transport implements framing and GATT service UUIDs with desktop simulation via Unix sockets. Real hardware integration requires linking against the platform BLE SDK (e.g., Nordic SoftDevice). See `ble.zig` for integration points.

## Multi-Channel Gateway (Phase 3)

The bridge supports multiple message channels simultaneously via `--serve` mode:

```bash
# Start with webhook channel (default)
python bridge/bridge/bridge.py --serve --channels webhook

# Start with multiple channels
python bridge/bridge/bridge.py --serve --channels telegram,webhook,websocket

# WebSocket gateway for browser-based clients
python bridge/bridge/bridge.py --serve --channels websocket
```

### Available Channels

| Channel | Transport | Use Case |
|---------|-----------|----------|
| **webhook** | HTTP POST | Simplest integration — any HTTP client |
| **websocket** | WebSocket | Browser clients, streaming responses |
| **telegram** | Telegram Bot API | Chat-based interaction |
| **mqtt** | MQTT pub/sub | IoT device messaging |

### WebSocket Wire Protocol

```json
→ {"type": "message", "text": "fix the bug"}
← {"type": "text", "text": "Let me look at that..."}
← {"type": "done"}
```

### Channel Configuration

Per-channel settings via `~/.krillclaw/channels.json`:

```json
{
  "webhook": {"port": 8080, "auth_token": "secret"},
  "websocket": {"port": 8765, "agent_binary": "./zig-out/bin/krillclaw"},
  "telegram": {"token": "bot123:ABC", "allowed_users": [12345]},
  "mqtt": {"broker": "localhost", "subscribe_topic": "krillclaw/in"}
}
```

## Skills / Plugins

Extend the agent with custom Python tools. Drop a `.py` file in `~/.krillclaw/plugins/`:

```python
# ~/.krillclaw/plugins/my_tool.py
TOOL_NAME = "my_custom_tool"
TOOL_DESCRIPTION = "Does something custom."
TOOL_SCHEMA = {"type": "object", "properties": {"input": {"type": "string"}}}

def handle(data: dict) -> dict:
    return {"result": f"processed: {data.get('input', '')}"}
```

Plugins are discovered on bridge startup. Unknown tools from the Zig agent automatically fall through to the bridge, which routes them to the matching plugin handler. Built-in tool names cannot be overridden.

## Configuration

```bash
# Environment variables
export KRILLCLAW_MODEL=claude-opus-4-6
export KRILLCLAW_PROVIDER=claude
export KRILLCLAW_BASE_URL=https://my-proxy.com
export KRILLCLAW_SYSTEM_PROMPT="You are a Go expert..."
```

```json
// .krillclaw.json (project-level config)
{
  "model": "claude-sonnet-4-5-20250929",
  "provider": "claude",
  "max_tokens": 8192,
  "streaming": true
}
```

Config precedence: CLI flags → environment variables → config file.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/quit` `/exit` `/q` | Exit |
| `/model <name>` | Switch model |
| `/provider <name>` | Switch provider |

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hand-rolled JSON** | `std.json` adds unnecessary code. KrillClaw only needs key extraction + body building. 501 lines, zero deps. |
| **Vtable transports** | Same binary works over HTTP, BLE, or Serial. Swap physical layer without touching agent logic. |
| **FNV-1a loop detection** | Detect stuck LLM loops in constant memory (128 bytes). Critical for embedded. |
| **Priority-based truncation** | When context fills, drop assistant text first, keep tool results. Keeps working memory functional. |
| **Substring search, not regex** | Regex engines are ~10K+ lines. `std.mem.indexOf` covers 90%+ of agent search use cases. |

## Testing

```bash
zig build test        # 39 inline unit tests
bash test/integration.sh  # 9 integration tests
```

Tests cover JSON parsing, SSE streaming, arena allocation, context truncation, tool execution, glob matching, and security injection attempts.

CI runs on every push with a binary size gate (<600KB).

## Building

```bash
zig build                              # Debug build
zig build -Doptimize=ReleaseSmall      # Smallest binary
zig build test                         # Run all tests
zig build size                         # Report binary size
```

## Security

KrillClaw executes tools with the permissions of the running user. **Do not run with elevated privileges.** Use profiles and sandbox mode to restrict tool access.

BLE and Serial transports do not currently include encryption or authentication. Use only on trusted networks.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## Known Limitations

- **JSON parser is flat** — finds first matching key at any depth (works for LLM API responses where keys are unambiguous)
- **Token estimation is heuristic** — ~4 chars/token approximation, not billing-accurate
- **Session persistence via bridge** — save/load conversation history through bridge tools
- **BLE transport is protocol-only** — real hardware needs platform BLE SDK linking
- **Serial baud uses `stty`** — Linux/macOS only
- **Requires Zig 0.15+**

## License

[BSL 1.1](LICENSE) — Business Source License. Converts to Apache 2.0 after 3 years (Change Date: 2029-02-17).

KrillClaw is **source-available**, not open source. You can read, build, and modify the code. Commercial use above the license thresholds requires a commercial license. See [LICENSE](LICENSE) for full terms.

## Contributing

Contributions welcome under BSL 1.1. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<p align="center">
  <sub>Built with Zig. No frameworks were harmed in the making of this runtime.</sub>
</p>
