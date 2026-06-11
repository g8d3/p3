---
name: agent-light
description: Lightweight Python agent that calls inference APIs directly (~10MB RAM). Use for multi-agent parallelism instead of heavy CLI tools.
---

# Lightweight Agent

When you need multiple agents working in parallel, don't launch heavy CLI tools (opencode = ~200MB RAM each). Build a lightweight Python agent that calls the inference API directly via `urllib` (~10MB RAM).

## Template

```python
#!/usr/bin/env python3
"""Lightweight agent — calls API directly. ~10MB RAM."""
import json, os, sys, urllib.request

API_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")

def call_llm(system, message):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        API_URL + "chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "agent-light/0.1",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().strip()
    print(call_llm("You are a builder agent.", task))
```

## Orchestrator pattern

```python
import subprocess, threading

def launch_agent(task, output_file):
    def run():
        result = subprocess.run(
            ["uv", "run", "python3", "agent_light.py", task],
            capture_output=True, text=True, timeout=300
        )
        with open(output_file, "w") as f:
            f.write(result.stdout or result.stderr)
    threading.Thread(target=run, daemon=True).start()
```

## When to use

- **Parallel agents**: launch many without exhausting RAM
- **Simple tasks**: code generation, text analysis, classification
- **Background jobs**: agents that run without user interaction

## When NOT to use

- **Complex multi-step reasoning**: use Crush or opencode instead
- **Tasks needing tools**: file access, web browsing, code execution
- **Interactive debugging**: where you need to see agent thinking in real-time
