# Web Framework Design: NOVA

**Next-gen Omniversal Virtual Architecture** — A meta-framework that builds itself and creates applications that build themselves.

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [The Meta-Layer: Framework Self-Building](#3-the-meta-layer-framework-self-building)
4. [The Auto-Layer: Applications That Build Themselves](#4-the-auto-layer-applications-that-build-themselves)
5. [Ultra-High Performance Design](#5-ultra-high-performance-design)
6. [Developer Experience](#6-developer-experience)
7. [User Experience](#7-user-experience)
8. [Agnostic AI Integration](#8-agnostic-ai-integration)
9. [Runtime Architecture](#9-runtime-architecture)
10. [Data Layer](#10-data-layer)
11. [Component Model](#11-component-model)
12. [IPC & Multi-Agent Protocol](#12-ipc--multi-agent-protocol)
13. [Security Model](#13-security-model)
14. [Testing & Observability](#14-testing--observability)
15. [Implementation Roadmap](#15-implementation-roadmap)

---

## 1. Core Philosophy

### 1.1 The Seven Pillars

| Pillar | Principle | Meaning |
|--------|-----------|---------|
| **Meta** | Framework builds itself | The framework generates its own code, tests, and docs from high-level intent |
| **Auto** | Apps build themselves | Applications infer their behavior from data + configuration, not hardcoded logic |
| **Zero-Friction** | Action-to-result in <10s | No build step, no deploy, no ceremony. Change something, see it immediately |
| **Total Visibility** | Everything is observable | Every layer exposes structured state for both humans and AI agents |
| **Config over Code** | Behavior changes without edits | Hot-reloadable configuration drives what code does, not the other way around |
| **Agnostic AI** | Providers are interchangeable | All AI calls go through a unified adapter layer; swap models/providers via config |
| **Consumption = Production** | Users create by using | Every interaction feeds the system, generating value for other users |

### 1.2 The Three-Layer Model

```
┌─────────────────────────────────────────────────────────┐
│                    META-LAYER                            │
│  (framework builds itself — codegen, scaffold, evolve)  │
│                                                         │
│  - Reads intent from spec/memory                        │
│  - Generates application structure                      │
│  - Self-modifies when patterns emerge                   │
│  - Evolves framework itself                             │
├─────────────────────────────────────────────────────────┤
│                    AUTO-LAYER                            │
│  (application builds itself — runtime self-assembly)    │
│                                                         │
│  - Routes auto-discover from data models                │
│  - UI renders from schema, not markup                   │
│  - Pipelines compose from capability registry           │
│  - APIs generate from type definitions                  │
├─────────────────────────────────────────────────────────┤
│                    RUNTIME-LAYER                         │
│  (execution — fast, observable, resilient)              │
│                                                         │
│  - WebAssembly + native extensions for hot paths        │
│  - Event-driven, non-blocking I/O everywhere            │
│  - Structured concurrency (async tasks as DAG)          │
│  - Hot-reload everything (code, config, assets)         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Overview

### 2.1 High-Level Topology

```
                         ┌─────────────────┐
                         │   ORCHESTRATOR   │
                         │  (Meta-Process)  │
                         │                  │
                         │  ┌────────────┐  │
                         │  │ state.db   │  │
                         │  │ spec/      │  │
                         │  │ memory/    │  │
                         │  └────────────┘  │
                         └────────┬─────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
      ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
      │  WEB SERVER │     │  AI ADAPTER │     │  WORKER POOL│
      │  (runtime)  │     │  (agnostic) │     │  (compute)  │
      │             │     │             │     │             │
      │  HTTP/WS    │     │  Provider A │     │  Renderers  │
      │  SSE        │     │  Provider B │     │  Analyzers  │
      │  Static     │     │  Provider C │     │  Generators │
      └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  IPC BUS (FS)   │
                         │  inbox/outbox/  │
                         │  shared/        │
                         └────────┬────────┘
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
      ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
      │  AGENTS     │     │  WEB APP    │     │  EXTERNAL   │
      │  (AI/Code)  │     │  (Browser)  │     │  SERVICES   │
      │             │     │             │     │             │
      │  Builder    │     │  Runtime UI │     │  APIs       │
      │  Tester     │     │  DevTools   │     │  CDPs       │
      │  Reviewer   │     │  Inspector  │     │  Storage    │
      └─────────────┘     └─────────────┘     └─────────────┘
```

### 2.2 Communication Patterns

| Pattern | Channel | Latency | Use Case |
|---------|---------|---------|----------|
| Request/Response | HTTP/Socket | <10ms | API calls, queries |
| Event Stream | Server-Sent Events | <5ms | Real-time UI updates |
| Command | IPC Bus (filesystem) | <100ms | Agent task dispatch |
| Publish/Subscribe | WebSocket | <10ms | Cross-agent broadcast |
| Bulk Data | Shared filesystem | — | Large artifacts |
| Streaming | Chunked HTTP/WebRTC | <1s | Video, audio, large generation |

---

## 3. The Meta-Layer: Framework Self-Building

### 3.1 The Specification Engine

The framework is driven by a living specification — a structured document that the framework itself can read, modify, and execute.

```yaml
# spec/app.yaml — The framework reads this to build itself
meta:
  name: "my-app"
  version: "0.1.0"
  description: "Application built by NOVA"

models:
  - name: "User"
    fields:
      name: { type: "string", required: true }
      email: { type: "email", unique: true }
      preferences: { type: "json", default: "{}" }

  - name: "Post"
    fields:
      title: { type: "string", required: true }
      body: { type: "text" }
    relationships:
      author: { model: "User", cardinality: "many-to-one" }

routes:
  - pattern: "/api/users"
    methods: ["GET", "POST"]
    model: "User"
    permissions: ["authenticated"]

  - pattern: "/api/feed"
    generator: true  # Auto-generated feed from data sources
    ai_powered: true # LLM-curated content

ai:
  providers:
    primary: "deepseek-v4-flash"
    fallback: "gemini-2.5-pro"
  capabilities: ["generate_script", "summarize", "classify"]

ui:
  layout: "feed"  # Framework knows how to render this
  theme: "dark"
  components: ["player", "feed", "settings"]
```

**How it works:**

1. Developer writes/updates `spec/app.yaml`
2. Framework detects change (inotify + git hook)
3. **Meta-agent** reads spec, compares with current codebase
4. Generates any missing pieces:
   - Database models (SQLAlchemy/Prisma/raw SQL)
   - API routes (FastAPI/Express/Go)
   - UI components (React/Vue/Svelte/SwiftUI)
   - Tests (unit + integration + E2E)
   - Documentation
5. Validates generated code compiles/passes tests
6. Hot-reloads the runtime
7. Commits changes with structured message

### 3.2 Self-Evolution Mechanism

When the framework detects repeated patterns, it evolves itself:

```
Pattern detected: User manually wrote 5 validation rules
  → Framework extracts: "These follow X pattern"
  → Framework proposes: "Add a 'validator' field to spec models"
  → If accepted: Framework updates spec parser + codegen + docs
  → Framework retroactively migrates existing code
  → Result: Next time, validators auto-generate from spec
```

**Detection sources:**
- Git history analysis (repeated manual edits)
- Runtime profiling (bottlenecks in generated code)
- Test failures (generated code that doesn't work)
- AI agent suggestions ("I noticed you keep writing X manually")

### 3.3 Intent Compilation

```
┌─────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│ SPEC    │───►│ INTENT   │───►│ GENERATOR │───►│ VALIDATOR│
│ (YAML)  │    │ COMPILER │    │ ENGINE    │    │ (tests)  │
└─────────┘    └──────────┘    └───────────┘    └──────────┘
                     │                │               │
                     ▼                ▼               ▼
              ┌────────────┐   ┌────────────┐   ┌─────────┐
              │ Dependency │   │ Codegen    │   │ Hot-    │
              │ Resolver   │   │ Templates  │   │ Reload  │
              └────────────┘   └────────────┘   └─────────┘
```

**Intent Compiler:** High-level spec → dependency graph of what needs to be generated. Resolves conflicts, detects cycles.

**Generator Engine:** Template-based (Jinja2/Mustache) + AST-based (for complex transformations). Each generator is a capability:

| Generator | Input | Output |
|-----------|-------|--------|
| `model-gen` | Model spec | Python class + DB migration + validation + GraphQL type |
| `route-gen` | Route spec | FastAPI router + Pydantic schemas + OpenAPI docs |
| `ui-gen` | UI spec | Component tree + CSS + Storybook stories |
| `test-gen` | Any spec | Pytest suite + integration tests + E2E scripts |
| `ai-gen` | AI capability spec | Adapter config + prompt templates + fallback logic |

---

## 4. The Auto-Layer: Applications That Build Themselves

### 4.1 Self-Assembling Application Architecture

Once generated, the application doesn't need a developer to configure it. It introspects itself and adapts at runtime.

```python
# Conceptual example — the app discovers itself:
class AutoApp:
    def __init__(self):
        # Introspect data models
        self.models = self.discover_models()
        # Auto-generate CRUD routes
        self.routes = self.generate_routes(self.models)
        # Auto-generate UI screens
        self.ui = self.render_screens(self.models)
        # Auto-connect data sources
        self.sources = self.connect_sources(config)
        # Auto-start pipelines
        self.pipelines = self.start_pipelines()

    def on_new_source_connected(self, source):
        """App adapts automatically when a new data source connects."""
        schema = source.introspect()
        model = self.create_model_from_schema(schema)
        route = self.add_route_for_model(model)
        screen = self.add_screen_for_model(model)
        self.hot_reload()
```

### 4.2 Auto-Discovery Chain

```
New data source connects
  → Introspect API/schema
    → Generate data model
      → Generate CRUD endpoints
        → Generate UI screens
          → Generate tests
            → Generate documentation
              → Update search index
```

All without human intervention. The app discovers, generates, and integrates.

### 4.3 Data-Driven Pipelines

Applications define **pipelines** — DAGs of processing steps — that auto-assemble from available capabilities:

```yaml
pipelines:
  - name: "video_feed"
    trigger: "on_demand"
    stages:
      - fetch_trends: { source: "github" }
      - fetch_trends: { source: "huggingface" }
      - generate_script: { using: "ai", model: "primary" }
      - generate_narration: { using: "edge-tts" }
      - select_assets: { gameplay: "random", music: "random" }
      - compose_video: { engine: "browser-wasm", quality: "720p" }
```

The runtime discovers which capabilities are available (e.g., which source connectors, which AI providers, which render engines) and assembles the pipeline DAG automatically. If a capability is missing, it either:
- Falls back to an alternative
- Prompts the meta-layer to generate it
- Reports the gap to the orchestrator

### 4.4 UI Auto-Rendering

The UI framework renders from schema, not handwritten markup:

```
Schema:
  User: { name: string, email: email, avatar: image }

Auto-renders to:
  ┌────────────────────┐
  │  User Profile       │
  │                     │
  │  [Avatar]           │  ← Type-aware: renders image upload
  │                     │
  │  Name: [__________] │  ← Type-aware: text input
  │  Email: [__________]│  ← Type-aware: email keyboard, validation
  │                     │
  │  [Save]  [Cancel]   │
  └────────────────────┘
```

**Built-in screen types:**

| Screen Type | Description | Auto-generated From |
|-------------|-------------|-------------------|
| `feed` | Infinite scrolling list | Any collection model |
| `player` | Media player with OSD | Media models + pipeline |
| `form` | Data entry/editing | Any data model |
| `dashboard` | Stats + charts | Aggregation queries |
| `detail` | Single entity view | Any data model |
| `settings` | Config panels | System capabilities |

---

## 5. Ultra-High Performance Design

### 5.1 Architecture for Speed

```
                    ┌──────────────────────────────────┐
                    │         REVERSE PROXY             │
                    │    (nginx/h2o — static files,     │
                    │     TLS termination, HTTP/2,      │
                    │     connection pooling)           │
                    └──────────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
       ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
       │  API SERVER │     │  WS SERVER  │     │  STATIC     │
       │  (FastAPI/  │     │  (broadcast)│     │  (pre-built │
       │   uvicorn)  │     │             │     │   + WASM)   │
       └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
              │                    │                    │
       ┌──────▼────────────────────▼────────────────────▼──────┐
       │                  SHARED STATE LAYER                    │
       │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
       │  │ Redis   │  │ SQLite  │  │  inode  │  │  mmap   │  │
       │  │ (cache) │  │ (state) │  │ (IPC)   │  │ (blobs) │  │
       │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │
       └──────────────────────────────────────────────────────┘
```

### 5.2 Performance Targets

| Metric | Target | Method |
|--------|--------|--------|
| Cold start (server) | <50ms | Pre-forked workers, lazy imports, PyO3 nopython modules |
| Request latency (p50) | <2ms | Zero-copy serialization, connection reuse, in-process cache |
| Request latency (p99) | <10ms | Circuit breakers, background warmup, pre-computed paths |
| Concurrent connections | 10k+ | Async everywhere, epoll/kqueue, zero-allocation paths |
| Memory per connection | <10KB | Zero-copy buffers, no per-request allocations |
| First paint (UI) | <500ms | Code-split + lazy load + preconnect + SSR streaming |
| Time to interactive | <1.5s | Island architecture, progressive hydration |
| AI call overhead | <5ms | Response streaming, speculative decoding, prompt caching |

### 5.3 Hot Path Optimizations

**Server hot path (every request):**

1. **Zero-copy JSON parsing** — `simdjson` bindings via PyO3/Rust (sub-microsecond parsing)
2. **Connection pooling** — Reuse connections across requests, no TCP handshake overhead
3. **In-process memoization** — LRU cache for model lookups, config reads, auth checks
4. **Pre-compiled templates** — All templates compiled at build time, no runtime parsing
5. **Response streaming** — SSE early-flush headers, progressive rendering
6. **TLS 1.3 early data** — Allow 0-RTT for repeat connections

**Browser hot path (every interaction):**

1. **Shared memory** — `SharedArrayBuffer` for audio/video buffers between workers
2. **OffscreenCanvas** — Compositing on Web Worker, no main thread blocking
3. **WASM audio pipeline** — Audio mixing/effects in WebAssembly (zero GC pauses)
4. **Video stream via MSE** — `MediaSource` appendBuffer for progressive video
5. **Animation → transforms** — CSS `transform` + `opacity` only, no layout thrash
6. **Predictive preload** — ML model predicts next user action, preloads assets

### 5.4 Memory Management

```python
@zero_alloc  # Decorator triggers static allocation analysis
async def handle_feed_request(user_id: str) -> Response:
    # Pre-allocated buffer pool — no allocations during request
    items = await cache.get(f"feed:{user_id}")
    if not items:
        items = await db.query(...)
        cache.set(f"feed:{user_id}", items, ttl=30)
    # Zero-copy serialization directly to response buffer
    return Response(json_bytes(items))
```

**Memory architecture:**
- Arena allocators for request-scoped data
- Object pools for frequently created/destroyed objects
- mmap for large blobs (video, audio, images)
- Reference counting with cycle detection (no GC pauses)
- Shared immutable state via atomic RCU updates

---

## 6. Developer Experience

### 6.1 The Developer Loop

```
Write spec  →  See app update instantly  →  Tweak config  →  See again
   │                  │                           │               │
   └──────────────────┘                           └───────────────┘
   < 1 second                     < 1 second

When stuck:
   Ask AI ("make this feed sort by popularity")
   → AI reads spec, modifies it, generates code, tests, commits
```

### 6.2 Hot-Reload Everything

| Asset | Reload Method | Latency |
|-------|--------------|---------|
| Code (Python/JS) | Module reload + FastAPI lifespan restart | <100ms |
| Config (YAML/JSON) | inotify watch → runtime config update | <10ms |
| Templates (HTML) | Browser EventSource → DOM patching | <50ms |
| Styles (CSS) | Browser WebSocket → instant injection | <5ms |
| Assets (images/video) | Cache invalidation → next request serves new | — |
| Spec (app.yaml) | Full re-generation pipeline | <2s |

### 6.3 Built-in DevTools

When `NOVA_ENV=dev` the framework automatically injects:

```
┌────────────────────────────────────────────────┐
│  [Your App]                        [⚙] [🐛]    │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │                                          │    │
│  │  (Your app content)                      │    │
│  │                                          │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │ 🐞 DevTools                             │    │
│  │  ┌─────┐ ┌──────┐ ┌──────┐ ┌────────┐  │    │
│  │  │ State│ │Events│ │Network│ │ AI Log │  │    │
│  │  └─────┘ └──────┘ └──────┘ └────────┘  │    │
│  │  ──────────────────────────────────────  │    │
│  │  Route: /api/feed  Status: 200  64ms    │    │
│  │  AI:cached  Model: deepseek-v4-flash     │    │
│  │  Errors: 0  Warnings: 2                 │    │
│  └──────────────────────────────────────────┘    │
└────────────────────────────────────────────────┘
```

**DevTools features:**
- **State inspector** — Browse all models, their relations, current data
- **Event timeline** — Every event that flowed through the system
- **Network panel** — Every request, latency breakdown, response payload
- **AI panel** — AI calls made, model used, latency, tokens, cache hits
- **Pipeline visualizer** — DAG of current processing pipeline with stage timing
- **Capability explorer** — All available capabilities, their status, dependencies
- **Config editor** — LIVE config editing with schema validation + undo

### 6.4 AI-Assisted Development

Every developer interaction can be augmented:

```bash
# Natural language → spec changes → code generation
nova "add a comments model to posts"
  → Reads spec, adds Comment model, adds routes, adds UI, adds tests
  → Validates, hot-reloads, commits

nova "why is the feed slow?"
  → Profiles endpoints, identifies bottleneck, suggests fix

nova "change the theme to match this screenshot"
  → Analyzes screenshot, generates CSS variables, applies live
```

**How it works:**

1. Developer makes request (natural language or spec change)
2. Framework captures current state (spec + code + runtime metrics)
3. AI agent analyzes context, proposes changes
4. Framework validates changes (type check + test)
5. Hot-reloads and commits with structured message
6. Reports summary to developer

---

## 7. User Experience

### 7.1 Zero-Friction User Loop

```
User opens app
  → App is already populated (pre-generated content)
  → User watches/consumes (zero clicks to reach value)
  → User swipes for more (next item loads in <500ms)
  → User tweaks experience (overlay controls, <1tap)
  → App adapts to user behavior (implicit personalization)
  → App generates more of what user engages with
```

### 7.2 The Consumption Interface

The default UI is a **full-screen media player** with invisible controls:

```
┌──────────────────────────────────────────────┐
│                                              │
│                                              │
│                                              │
│              VIDEO CONTENT                   │
│                                              │
│                                              │
│                                              │
│                                              │
│   ┌────────────────────────────────────┐     │
│   │ Subtitles with word highlighting   │     │
│   └────────────────────────────────────┘     │
│                                              │
│   ← ← (swipe)   [progress bar]   → →        │
│                                              │
│   ⚙️ [tap to reveal controls]               │
│     ┌──────────────┐                        │
│     │ Style panel  │                        │
│     │ Voice, font, │                        │
│     │ music, etc   │                        │
│     └──────────────┘                        │
└──────────────────────────────────────────────┘
```

**UX principles:**
- **Content-first** — Content fills the screen; controls are overlay
- **Gesture-driven** — Swipe, tap, pinch — no navigation chrome
- **Immediate** — Every action has instantaneous visual feedback
- **Adaptive** — UI adapts to device (mobile, desktop, TV, VR)
- **Progressive** — Start simple, reveal complexity as needed

### 7.3 The Configuration Spectrum

Users choose where they fall on the autonomy spectrum:

```
Fully automatic  ●─────────────────○  Fully manual
                  │
                  │
             Default: 80% auto
```

**At 80% auto:**
- Content is generated automatically
- Sources are connected automatically
- Style has sensible defaults
- User can override anything with one tap
- Overrides are learned for future automatic choices

**At 100% manual:**
- User writes own scripts
- User selects every asset
- User controls every parameter
- No AI suggestions (or suggestions can be ignored)

### 7.4 Implicit Personalization

The system watches user behavior and adapts without explicit settings:

| Behavior | Adaptation |
|----------|-----------|
| User consistently skips certain topics | Model updates prompt to avoid those topics |
| User lingers on gaming content | Gaming sources get higher weight in trend selection |
| User increases font size | New default font size |
| User watches at certain times | Pre-generate content before those times |
| User shares content | Boost generation of similar content |
| User always changes voice | Offer voice changes proactively |

---

## 8. Agnostic AI Integration

### 8.1 Unified AI Adapter

Every AI call goes through a single abstraction:

```python
# Conceptual API — all providers look the same
class AIAdapter:
    def __init__(self, config: ProviderConfig):
        self.provider = self._load_provider(config)

    async def generate(self, request: AIRequest) -> AIResponse:
        """Unified call — all providers implement this interface."""
        pass

    async def stream(self, request: AIRequest) -> AsyncIterator[AIChunk]:
        """Unified streaming — all providers implement this interface."""
        yield chunk

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Unified embeddings."""
        pass

    async def moderate(self, content: str) -> ModerationResult:
        """Unified content moderation."""
        pass
```

### 8.2 Configuration

```yaml
ai:
  # Primary — fastest, always tried first
  primary:
    provider: "opencode"  # Or: "openai", "anthropic", "gemini", "ollama", "custom"
    model: "deepseek-v4-flash"
    key: "${OPENCODE_API_KEY}"
    endpoint: "https://opencode.ai/zen/go/v1/chat/completions"
    options:
      max_tokens: 4096
      temperature: 0.7

  # Fallback — used when primary fails or is rate-limited
  fallback:
    provider: "gemini"
    model: "gemini-2.5-pro"
    key: "${GEMINI_API_KEY}"
    options:
      max_tokens: 4096
      safety_settings: "medium"

  # Embeddings — separate provider often cheaper
  embeddings:
    provider: "openai"
    model: "text-embedding-3-small"
    key: "${OPENAI_API_KEY}"

  # Moderation — content safety
  moderation:
    provider: "openai"
    model: "omni-moderation-latest"
    key: "${OPENAI_API_KEY}"

  # Local — zero-cost, zero-latency for simple tasks
  local:
    provider: "ollama"
    model: "llama3.2:1b"
    endpoint: "http://localhost:11434"

# Strategy: how to use these providers
strategy:
  pipeline: "primary → fallback → local"  # Cascade on failure
  streaming: true  # Always prefer streaming when available
  cache:
    ttl: 3600
    similar_threshold: 0.95  # Cache similar prompts via embedding similarity
  routing:
    "generate_script": "primary"      # Complex → use best model
    "summarize": "local"              # Simple → use local
    "classify": "local"               # Fast → use local
    "translate": "fallback"           # Specialized → use specific
    "embed": "embeddings"             # Dedicated embedding provider
```

### 8.3 Provider Cascade

```
Request: generate_script(trends_data)
  → Try primary (opencode/deepseek-v4-flash)
    → Success? Return + cache
    → Rate limited? Wait + retry (exponential backoff)
    → Error? Try fallback (gemini/gemini-2.5-pro)
      → Success? Return + cache (mark degraded)
      → Error? Try local (ollama/llama3.2)
        → Success? Return
        → Error? Return cached + flag stale
```

### 8.4 Prompt Management

Prompts are versioned, tested, and optimized:

```yaml
prompts:
  generate_script:
    version: 4
    template: |
      Eres un creador de contenido para {platform}.
      {style_instructions}
      {avoid_topic_instruction}

      Datos de tendencias:
      {trends_data}

      Genera un guión de {duration} segundos.
      {format_instructions}
    variables:
      platform: { default: "TikTok" }
      duration: { type: int, default: 35 }
    tests:
      - input: { trends: "...", platform: "YouTube" }
        expected_output_contains: ["suscríbete"]
        max_tokens: 500
    metrics:
      - "engagement_rate"
      - "char_count"
      - "readability_score"
```

**Prompt lifecycle:**
1. Developer/Agent writes prompt
2. Prompt is registered with test cases + success metrics
3. AI adapter runs tests against current prompt
4. If metrics degrade → alert; if improve → auto-promote
5. A/B testing: run multiple prompt versions in shadow mode

### 8.5 Observability for AI

Every AI interaction is instrumented:

```json
{
  "call_id": "ai_abc123",
  "provider": "opencode",
  "model": "deepseek-v4-flash",
  "prompt_version": 4,
  "latency_ms": 1234,
  "prompt_tokens": 245,
  "completion_tokens": 180,
  "tokens_per_second": 145.9,
  "cached": false,
  "fallback_used": false,
  "error": null,
  "retry_count": 0,
  "timestamp": "2026-05-29T10:00:00Z",
  "cost_estimate": 0.00037
}
```

---

## 9. Runtime Architecture

### 9.1 Process Model

```
                    ┌─────────────────────────────┐
                    │     ORCHESTRATOR (PID 1)     │
                    │  Python asyncio + uvloop     │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │  Spec Watcher (inotify) │  │
                    │  │  Config Hot-Reloader    │  │
                    │  │  Agent Scheduler        │  │
                    │  │  Health Monitor         │  │
                    │  │  State DB (SQLite)      │  │
                    │  └────────────────────────┘  │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
  ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
  │  API SERVER │          │  AI PROXY   │          │  WORKER POOL│
  │  (uvicorn)  │          │  (agnostic) │          │  (subprocs) │
  │             │          │             │          │             │
  │  HTTP/WS    │          │  Rate limit │          │  Renderer   │
  │  SSE        │          │  Cache      │          │  Analyzer   │
  │  REST       │          │  Fallback   │          │  Generator  │
  └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       IPC BUS (FS)           │
                    │  inbox/ /outbox/ /shared/    │
                    └─────────────────────────────┘
```

### 9.2 Concurrency Model

| Level | Mechanism | Granularity |
|-------|-----------|-------------|
| I/O | async/await (uvloop) | Nanosecond-scale |
| CPU | ProcessPoolExecutor | Core-scale |
| AI | Subprocess + streaming | Millisecond-scale |
| Parallel DAG | asyncio.TaskGroup | Task-scale |
| Cross-server | Redis pub/sub | Message-scale |

**Structured concurrency — all tasks are organized in DAGs:**

```python
async def process_feed_package():
    async with TaskGroup() as tg:
        # These run in parallel
        trends_task = tg.create_task(fetch_trends())
        assets_task = tg.create_task(prepare_assets())

    # This runs after both complete
    script = await generate_script(trends_task.result())

    async with TaskGroup() as tg:
        # These run in parallel
        narration = tg.create_task(generate_narration(script))
        subtitles = tg.create_task(generate_subtitles(script))

    # All complete → compose
    video = await compose_video(narration.result(), subtitles.result(), assets_task.result())
```

### 9.3 Startup Sequence

```
1. Orchestrator starts
   a. Load config from YAML
   b. Connect state DB (SQLite)
   c. Start spec watcher (inotify)
   d. Start health monitor

2. Orchestrator spawns API server (uvicorn, pre-forked)
   a. Workers load code lazily
   b. Each worker connects to shared state
   c. Register routes (app-level + meta-level)

3. Orchestrator spawns AI proxy (subprocess)
   a. Connect to configured providers
   b. Warm-up model caches
   c. Run prompt health checks

4. Orchestrator spawns worker pool
   a. N workers based on CPU count + config
   b. Each worker connects to IPC bus
   c. Workers fetch first available tasks

5. Orchestrator signals "ready"
   a. API server starts accepting connections
   b. First load of auto-generated content begins
   c. Health checks pass → load balancer admits traffic
```

**Cold start target: <500ms from process start to first request served.**

### 9.4 Graceful Shutdown

```
Signal received (SIGTERM/SIGINT)
  1. Stop accepting new connections (drain)
  2. Complete in-flight requests (max 10s timeout)
  3. Save in-memory state to SQLite
  4. Cancel background tasks with cleanup
  5. Close all provider connections
  6. Flush logs
  7. Exit
```

---

## 10. Data Layer

### 10.1 Hybrid Storage Architecture

| Data Type | Storage | Access | Durability |
|-----------|---------|--------|------------|
| Application state | SQLite (single file) | ACID, concurrent readers | fsync on write |
| Cache | Redis / in-memory dict | Sub-millisecond | Volatile (LRU) |
| Blobs (media) | Filesystem (mmap) | Zero-copy | Durable |
| IPC messages | Filesystem (inbox/outbox) | Atomic rename (POSIX) | Durable per message |
| Logs | Filesystem (append-only) | Sequential | Durable |
| Metrics | In-memory ring buffer | Sub-microsecond | Flushed periodically |
| Search index | Tantivy / SQLite FTS5 | Sub-millisecond | Durable |

### 10.2 Schema Evolution

```python
# The framework handles migrations automatically
class AutoMigration:
    def detect_changes(self, spec_before, spec_after):
        """Compare two spec versions, produce migration plan."""
        added_models = set(spec_after.models) - set(spec_before.models)
        removed_models = set(spec_before.models) - set(spec_after.models)
        changed_models = detect_field_changes(spec_before, spec_after)
        return MigrationPlan(added_models, removed_models, changed_models)

    def apply(self, plan):
        """Apply migration without data loss."""
        with transaction:
            for model in plan.added:
                self.create_table(model)
            for model in plan.changed:
                self.alter_table(model)
            for model in plan.removed:
                self.backup_and_drop(model)
```

**Migration strategies:**
- **Add field** — Immediate, nullable or default value
- **Remove field** — Mark deprecated, keep data, remove after grace period
- **Rename model** — Create new table, migrate data, drop old (transactional)
- **Split model** — Create child, backfill references, verify, drop old columns
- **Merge models** — Create merged table, migrate data, drop originals

### 10.3 Auto-Discovery for External Data Sources

```python
class AutoSourceConnector:
    """Connects to ANY external API without manual configuration."""

    def connect(self, base_url: str):
        """Discover OpenAPI/Swagger schema, infer capabilities."""
        schema = self.fetch_openapi(base_url)
        self.models = self.infer_models(schema)
        self.routes = self.infer_routes(schema)
        self.auth = self.infer_auth(schema)

    def infer_models(self, schema) -> list[Model]:
        """Convert OpenAPI schemas → internal model definitions."""
        return [Model(name, fields)
                for name, schema_def in schema.components.schemas.items()]

    def sync_to_internal(self):
        """Create or update internal models to match source schema."""
        for model in self.models:
            self.meta_layer.ensure_model(model)
```

---

## 11. Component Model

### 11.1 Capability-Based Architecture

Everything is a **capability** — a self-contained unit of functionality with inputs, outputs, and dependencies:

```yaml
capability:
  id: "tiktok-connector"
  type: "source-connector"
  version: "1.0"
  description: "Fetch trending content from TikTok"

  dependencies:
    - "http-client"
    - "rate-limiter"

  provides:
    - "fetch_trends"
    - "get_user_feed"

  config:
    api_key: { type: "string", required: true }
    rate_limit: { type: "int", default: 10 }

  metrics:
    requests_total: counter
    errors_total: counter
    latency_seconds: histogram
```

### 11.2 Capability Discovery

```
Orchestrator
  → Loads all capability packages (*/capability.yaml)
  → Resolves dependency graph
  → Loads in dependency order
  → Registers each capability's provides[]
  → Reports any missing dependencies
  → Watches for new capability packages (hot-load)
```

### 11.3 Core Capabilities (Built-in)

| Capability | Description | Hot Path? |
|------------|-------------|-----------|
| `http-server` | HTTP/WS/SSE server | Yes |
| `auth-basic` | API key + JWT auth | Yes |
| `model-sqlite` | SQLite model persistence | Yes |
| `cache-memory` | In-memory LRU cache | Yes |
| `ai-adapter` | Agnostic AI provider interface | Yes |
| `source-connector` | Base class for data sources | No |
| `media-compositor` | Video/audio compositing | No |
| `feed-engine` | Content generation pipeline | No |
| `meta-builder` | Self-building code generator | No |

### 11.4 Custom Capabilities

Applications define their own:

```yaml
# myapp/capability.yaml
capability:
  id: "my-app-workflow"
  type: "pipeline"
  dependencies:
    - "ai-adapter"
    - "source-connector"
    - "media-compositor"

  pipeline:
    - step: "fetch-data"
      using: ["github-connector", "huggingface-connector"]
    - step: "generate"
      using: "ai-adapter"
      prompt: "generate_script"
    - step: "produce"
      using: "media-compositor"
```

---

## 12. IPC & Multi-Agent Protocol

### 12.1 Universal Message Contract

```json
{
  "id": "msg_abc123",
  "type": "task | result | log | error | ping | config | event",
  "agent": "backend-1",
  "version": "0.1",
  "timestamp": "2026-05-29T10:00:00Z",
  "ttl_s": 120,
  "trace_id": "trace_xyz",
  "payload": {}
}
```

### 12.2 Transport Layers

| Transport | Direction | Latency | Scope |
|-----------|-----------|---------|-------|
| Filesystem (inbox/outbox) | Bidirectional | <100ms | Local agents |
| stdin/stdout (subprocess) | Bidirectional | <10ms | Child processes |
| WebSocket (WS) | Bidirectional | <10ms | Remote agents, UI |
| SSE (EventSource) | Server → Client | <5ms | UI updates |
| HTTP | Request/Response | <50ms | Direct API |

### 12.3 Agent Types

| Agent | Role | Communication |
|-------|------|--------------|
| **Orchestrator** | Schedules, monitors, routes | Inbox/outbox to all |
| **Builder** | Code generation, spec compilation | stdin/stdout (subprocess) |
| **Integrator** | Testing, validation, debugging | FS + WS |
| **UX Agent** | Reviews experience, suggests improvements | WS (sees UI) |
| **Escenógrafo** | Dashboard, progress visualization | FS + WS |
| **Business Agent** | Market research, strategy | HTTP (web fetch) |

---

## 13. Security Model

### 13.1 Principles

1. **Least privilege** — Every capability only has access to what it needs
2. **No secrets in code** — All secrets via environment variables or vault
3. **Sandboxed execution** — Capabilities run in isolated environments
4. **Audit trail** — Every action is logged with identity + timestamp
5. **Safe defaults** — Everything locked down by default

### 13.2 API Authentication

```yaml
auth:
  api_keys:
    - key: "${API_KEY_1}"
      permissions: ["read:feed", "read:sources"]
    - key: "${API_KEY_2}"
      permissions: ["admin:*"]

  jwt:
    algorithm: "Ed25519"
    ttl: 3600
    public_key: "${JWT_PUBLIC_KEY}"
    private_key: "${JWT_PRIVATE_KEY}"

  rate_limiting:
    default: "100/min"
    admin: "1000/min"
    ai_proxy: "10000/min"
```

### 13.3 AI Safety

```python
class AISafetyLayer:
    """Wraps all AI calls with safety checks."""

    async def safe_generate(self, request: AIRequest) -> AIResponse:
        # 1. Input moderation
        input_check = await self.moderate(request.prompt)
        if input_check.flagged:
            return self.safe_fallback("Input blocked by moderation")

        # 2. Generate
        response = await self.provider.generate(request)

        # 3. Output moderation
        output_check = await self.moderate(response.content)
        if output_check.flagged:
            return self.safe_fallback("Output blocked by moderation")

        # 4. Constraints check
        if not self.validate_constraints(response):
            return self.safe_fallback("Output violated constraints")

        return response
```

---

## 14. Testing & Observability

### 14.1 The Visibility Stack

```
Layer             Tool                    What it shows
─────             ────                    ────────────
Application       DevTools panel          State, events, network, AI
Server            Structured logs         Every request, error, decision
System            htop + iostat           CPU, memory, disk, network
Browser           CDP + console           DOM, network, errors, performance
Agents            IPC bus logs            Every message, task, result
Meta              Spec diff + gen log     What changed, what was generated
```

### 14.2 Structured Logging

```json
{
  "ts": "2026-05-29T10:00:00.123Z",
  "level": "INFO",
  "source": "feed-engine",
  "trace_id": "trace_xyz",
  "span_id": "span_abc",
  "message": "Generated package",
  "data": {
    "pkg_id": "pkg_001",
    "script_len": 285,
    "duration_s": 45,
    "assets": ["gameplay.mp4", "music.mp3"],
    "ai_calls": 1,
    "ai_latency_ms": 1234
  }
}
```

### 14.3 Testing Pyramid

```
     ╱╲
    ╱  ╲          E2E (agent-browser + CDP) — test real browser interactions
   ╱    ╲
  ╱──────╲
 ╱────────╲      Integration (harness suite) — test API + pipelines + IPC
╱──────────╲
╱────────────╲   Unit (pytest) — test individual capabilities
──────────────
```

**Auto-generated tests:**

```
For every model:
  → Test CRUD operations
  → Test validation rules
  → Test relationships

For every route:
  → Test 200 response
  → Test 400 on invalid input
  → Test 401/403 on unauthorized

For every pipeline:
  → Test each stage in isolation
  → Test full DAG execution
  → Test failure recovery
  → Test performance (latency budget)
```

### 14.4 Testing Loop

```
Code change detected
  → Run affected tests (file-watch)
    → Pass? → Report "✅"
    → Fail? → Report diff, rollback if configured
  → Run full suite (every 10 changes / every 5 min)
    → Pass? → Report coverage, commit if clean
    → Fail? → Report regression, alert responsible agent
  → Nightly performance benchmarks
    → Track latency, memory, throughput trends
```

---

## 15. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

- [ ] Core runtime: FastAPI + uvloop + structured concurrency
- [ ] Agnostic AI adapter with cascade strategy
- [ ] IPC bus (filesystem inbox/outbox + shared state)
- [ ] Hot-reload config (inotify + runtime update)
- [ ] Meta-agent: specs → model + route generation
- [ ] Built-in DevTools panel
- [ ] Structured logging + observability

### Phase 2: Auto-Layer (Week 3-4)

- [ ] Self-discovering routes from models
- [ ] UI auto-rendering from schema (feed, player, form, dashboard)
- [ ] Pipeline auto-assembly from capabilities
- [ ] Source connector auto-discovery (OpenAPI → model)
- [ ] Auto-migration (detect spec changes → apply)
- [ ] Consumption interface (full-screen player with OSD)

### Phase 3: Self-Evolution (Week 5-6)

- [ ] Pattern detection from git history + runtime
- [ ] Self-codegen from detected patterns
- [ ] A/B prompt testing
- [ ] Performance regression detection
- [ ] Auto-scaling workers based on load

### Phase 4: Multi-Agent Collaboration (Week 7-8)

- [ ] Multiple agent types with orchestration
- [ ] Token-aware scheduling (respect provider TPS)
- [ ] Agent task dependency resolution
- [ ] Automated code review + testing
- [ ] Dashboard (Escenógrafo agent)

### Phase 5: Production Hardening (Week 9-10)

- [ ] Sandboxed capability execution
- [ ] End-to-end encryption
- [ ] Disaster recovery + backup
- [ ] Performance optimization (WASM hot paths)
- [ ] Documentation auto-generation
- [ ] Deployment automation

---

## Appendix A: Key Metrics & Success Criteria

| Metric | Target |
|--------|--------|
| Time from spec change to working app | <2s |
| Requests per second (single node) | >10,000 |
| P99 latency (API) | <10ms |
| AI provider switch (config change) | <1s (existing connections drain) |
| New model + CRUD + UI from spec | <500ms generation time |
| Cold start to first request | <500ms |
| Test coverage (auto-generated) | >90% |
| Framework self-generated code | >50% of total codebase |

## Appendix B: Relationship to Existing Codebase (s72)

This framework is the **generalization** of the patterns proven in s72 (AI Video Studio). Every principle here emerged from building:

- **IPC Bus** → Generalized from `inbox/outbox/` agent communication
- **Feed Engine** → Generalized from auto-generating video pipeline
- **Auto-Scripting** → Generalized from LLM-powered script generation from trends
- **Browser Compositing** → Generalized from `composer.html` WASM approach
- **Visibility Stack** → Generalized from `visibility.py` + DevTools + CDP integration
- **Config over Code** → Generalized from hot-reloadable `config.py`
- **Multi-Agent Testing** → Generalized from `harness.py` + `watch.sh` + agent-browser
