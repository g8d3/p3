#!/usr/bin/env python3
"""
AAN Agent — visible, configurable, tests its own work.

Shows system prompt, user task, reasoning, actions, and results.
Writes code to files, runs it, tests it, reports pass/fail.
All visible in tmux window and saved to version output.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

API_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")
WORK_DIR = os.environ.get("AGENT_WORK_DIR", os.path.dirname(os.path.abspath(__file__)))

# Default system prompt — can be overridden via env var
DEFAULT_SYSTEM = """You are a software builder agent. Follow these rules:
1. Output file paths and code clearly, e.g.:
   FILE: hello.py
   ```python
   print("hello")
   ```
2. If the task needs multiple files, list them all.
3. Always include a test or verification step.
4. Be concise. Output only what's needed."""

SYSTEM_PROMPT = os.environ.get("AGENT_SYSTEM_PROMPT", DEFAULT_SYSTEM)


def announce(label, value):
    """Print a visible section to tmux."""
    print(f"\n{'─'*50}")
    print(f"  {label}: {value}")
    print(f"{'─'*50}")


def call_llm(messages, max_tokens=4096, temperature=0.3):
    """Call the LLM with a message list."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        API_URL + "chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "aan-agent/0.2",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=120)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return f"[HTTP {e.code}] {body}"
    except Exception as e:
        return f"[ERROR] {e}"


def extract_files(text):
    """Extract FILE: path and ``` blocks from LLM output."""
    files = {}
    current_file = None
    in_code = False
    code_lines = []

    for line in text.split("\n"):
        if line.startswith("FILE:"):
            if current_file and code_lines:
                files[current_file] = "\n".join(code_lines)
            current_file = line[5:].strip()
            code_lines = []
            in_code = False
        elif line.startswith("```"):
            if in_code:
                in_code = False
            else:
                in_code = True
        elif in_code and current_file:
            code_lines.append(line)

    if current_file and code_lines:
        files[current_file] = "\n".join(code_lines)
    return files


def write_files(files, version_dir):
    """Write extracted files to disk. Returns list of written paths."""
    written = []
    os.makedirs(version_dir, exist_ok=True)
    for path, content in files.items():
        # Prevent path traversal
        safe_path = os.path.normpath(os.path.join(version_dir, path))
        if not safe_path.startswith(os.path.normpath(version_dir)):
            print(f"  ⚠️ Skipping path traversal: {path}")
            continue
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w") as f:
            f.write(content)
        written.append(safe_path)
        size = len(content)
        print(f"  📄 Wrote {path} ({size} bytes)")
    return written


def run_code(filepath, timeout=10):
    """Run a code file and return (exit_code, stdout, stderr)."""
    ext = os.path.splitext(filepath)[1]
    if ext == ".py":
        cmd = ["uv", "run", "python3", filepath]
    elif ext == ".sh":
        cmd = ["bash", filepath]
    elif ext == ".js":
        cmd = ["node", filepath]
    elif ext == ".go":
        cmd = ["go", "run", filepath]
    else:
        return (-1, "", f"Unknown extension: {ext}")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", f"TIMEOUT ({timeout}s)")
    except FileNotFoundError as e:
        return (-1, "", f"Runtime not found: {e}")


def main():
    task_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    vid = sys.argv[2] if len(sys.argv) > 2 else "?"

    # If arg is a file path, read the task from file
    if os.path.isfile(task_arg):
        with open(task_arg) as f:
            task = f.read().strip()
    else:
        task = task_arg or sys.stdin.read().strip()

    # ── Header ──
    print(f"\n{'='*60}")
    print(f"  🤖 AAN Agent {vid}")
    print(f"  Model: {MODEL}")
    print(f"  Task: {task}")
    print(f"{'='*60}")

    # ── Show system prompt ──
    announce("SYSTEM PROMPT", SYSTEM_PROMPT.replace("\n", "\\n")[:200])

    # ── Call LLM ──
    print(f"\n⏳ Calling LLM...", end="", flush=True)
    t0 = time.time()
    response = call_llm([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ])
    elapsed = time.time() - t0
    print(f" done ({elapsed:.1f}s, {len(response)} chars)")

    # ── Show LLM response ──
    announce("LLM RESPONSE", response[:500])
    if len(response) > 500:
        print(f"  ... ({len(response)-500} more chars)")

    # ── Extract files ──
    files = extract_files(response)
    if not files:
        # No FILE: markers — try to extract raw code blocks
        import re
        code_blocks = re.findall(r'```(\w*)\n(.*?)```', response, re.DOTALL)
        if code_blocks:
            ext_map = {'python': 'py', 'bash': 'sh', 'shell': 'sh', 'javascript': 'js', 'go': 'go', 'html': 'html'}
            for lang, code in code_blocks:
                ext = ext_map.get(lang.strip(), 'txt')
                fname = f"script.{ext}"
                files[fname] = code.strip()
            print(f"  📄 Extracted {len(files)} raw code block(s) as files")
        else:
            print("\n⚠️ No code blocks or files extracted. Raw response below.")
            print(response[:500])
            print(f"\n✅ Agent {vid} finished (no files to write)")
            sys.exit(0)

    announce("FILES EXTRACTED", f"{len(files)} file(s)")

    # ── Write files to version directory ──
    version_dir = os.path.join(WORK_DIR, "versions", vid)
    written = write_files(files, version_dir)

    # ── Test each file ──
    announce("TESTING", f"{len(written)} file(s)")
    passed = 0
    failed = 0
    for fp in written:
        ext = os.path.splitext(fp)[1]
        if ext not in (".py", ".sh", ".js"):
            print(f"  ⏭️  Skipping {os.path.basename(fp)} (can't run {ext})")
            continue
        print(f"  ▶️  Running {os.path.relpath(fp, WORK_DIR)}...", end=" ", flush=True)
        code, stdout, stderr = run_code(fp)
        if code == 0:
            print("✅ PASSED")
            passed += 1
            if stdout.strip():
                print(f"  Output: {stdout.strip()[:200]}")
        else:
            print(f"❌ FAILED (exit={code})")
            failed += 1
            if stderr.strip():
                print(f"  Error: {stderr.strip()[:200]}")

    # ── Summary ──
    announce("SUMMARY", f"Agent {vid}")
    print(f"  Files written: {len(written)}")
    print(f"  Tests passed: {passed}")
    print(f"  Tests failed: {failed}")
    print(f"  Response size: {len(response)} chars")
    print(f"  LLM time: {elapsed:.1f}s")
    status = "✅ PASSED" if failed == 0 else "⚠️  HAS FAILURES"
    print(f"\n  {status}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
