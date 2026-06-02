#!/usr/bin/env python3
"""Lightweight agent — calls Opencode Go API directly. Streams to stdout."""
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
            "User-Agent": "aan-agent/0.1",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERROR HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return f"ERROR: {e}"

def main():
    task = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().strip()
    vid = sys.argv[2] if len(sys.argv) > 2 else "?"
    print(f"⚡ Agent {vid}: starting")
    print(f"📋 Task: {task}")
    print(f"🤖 Model: {MODEL}")
    print(f"⏳ Calling LLM...", end="", flush=True)
    result = call_llm("You are a builder agent. Output only the code.", task)
    print(f" done ({len(result)} chars)")
    print()
    print(result)
    print()
    print(f"✅ Agent {vid} completed")

if __name__ == "__main__":
    main()
