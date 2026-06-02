#!/usr/bin/env python3
"""Lightweight agent — calls Opencode Go API directly. ~10MB RAM."""
import json
import os
import sys
import urllib.request
import urllib.error

API_URL = os.environ.get("OPENCODE_GO_BASE_URL") or os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
API_KEY = os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY", "")
MODEL = os.environ.get("OPENCODE_GO_MODEL") or os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")
TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "120"))


def call_llm(system_prompt, user_message):
    """Call the Opencode Go API and return the response text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
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
        r = urllib.request.urlopen(req, timeout=TIMEOUT)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERROR: HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return f"ERROR: {e}"


def main():
    task = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().strip()
    system = (
        "You are a software builder agent. Your task is to write code, "
        "create files, and implement features. Output only the code and "
        "file changes needed. Be concise and precise."
    )
    result = call_llm(system, task)
    print(result)


if __name__ == "__main__":
    main()
