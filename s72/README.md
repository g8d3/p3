# NOVA Framework

**Next-gen Omniversal Virtual Architecture** — A self-building web framework that creates applications that build themselves.

## Quick Start

```bash
pip install -e .
python -m nova
```

Open http://localhost:8777 and http://localhost:8777/__dev for DevTools.

## Structure

```
nova/
├── core/          # Runtime, config, structured logging
├── ai/            # Agnostic AI adapter + providers
├── ipc/           # Filesystem-based message bus
├── meta/          # Spec parser, codegen, watcher
├── runtime/       # HTTP server, hot-reloader
├── devtools/      # State inspector, DevTools panel
├── spec/          # Application specs
├── docs/          # Framework design docs
└── tests/         # Test suite

capabilities/
├── video-templator/   # AI video template engine
└── ai-video-studio/   # AI-powered video feed platform
```

## Principles

| Principle | Description |
|-----------|-------------|
| **Meta** | Framework builds itself from spec |
| **Auto** | Apps assemble themselves at runtime |
| **Zero-Friction** | Change → see result in <2s |
| **Total Visibility** | Every layer is observable |
| **Config over Code** | Behavior changes without edits |
| **Agnostic AI** | Providers are interchangeable |
| **Consumption = Production** | Users create by using |
