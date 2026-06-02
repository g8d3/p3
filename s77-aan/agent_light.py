#!/usr/bin/env python3
"""
AAN Worker — generates code via LLM API, reviews via CLI agent (opencode/crush).
The user chooses AAN_CLI=api (default, direct LLM call) or AAN_CLI=opencode.
For code generation, 'api' mode is better. For analysis, 'opencode' works.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

CLI_AGENT = os.environ.get("AAN_CLI", "api")
WORK_DIR = os.environ.get("AGENT_WORK_DIR", os.path.dirname(os.path.abspath(__file__)))


def announce(label, value):
    print(f"\n{'─'*50}")
    print(f"  {label}: {value}")
    print(f"{'─'*50}")


# ── API mode (default, for code generation) ──

API_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")

SYSTEM_PROMPT = os.environ.get("AGENT_SYSTEM_PROMPT",
    "You are a software builder. Output code with a FILE:path line before each code block.\n"
    "Example:\nFILE: hello.py\n```python\nprint('hello')\n```\n"
    "Always output the full file content. Then test it yourself.")


def call_api(task):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ],
        "max_tokens": 8192,
        "temperature": 0.3,
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
        return f"[HTTP {e.code}] {e.read().decode()[:300]}"
    except Exception as e:
        return f"[ERROR] {e}"


# ── CLI mode (for analysis, review) ──

def call_cli(task, timeout=300):
    cmd = {"opencode": ["opencode", "run", task],
           "crush": ["crush", "run", task],
           "hermes": ["hermes", "run", task]}.get(CLI_AGENT)
    if not cmd:
        return f"[Unknown CLI agent: {CLI_AGENT}]"
    print(f"  🔧 CLI: {CLI_AGENT}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout or r.stderr or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except FileNotFoundError:
        return f"[{CLI_AGENT} not installed]"


# ── Shared utilities ──

def extract_files(text):
    files, current_file, in_code, code_lines = {}, None, False, []
    for line in text.split("\n"):
        if line.startswith("FILE:"):
            if current_file and code_lines:
                files[current_file] = "\n".join(code_lines)
            current_file = line[5:].strip()
            code_lines, in_code = [], False
        elif line.startswith("```"):
            in_code = not in_code
        elif in_code and current_file:
            code_lines.append(line)
    if current_file and code_lines:
        files[current_file] = "\n".join(code_lines)
    return files


def extract_blocks(text):
    blocks = re.findall(r'```(\w*)\n(.*?)```', text, re.DOTALL)
    if not blocks:
        return {}
    ext_map = {'python': 'py', 'bash': 'sh', 'shell': 'sh', 'javascript': 'js',
               'typescript': 'ts', 'go': 'go', 'html': 'html', 'css': 'css'}
    files = {}
    for lang, code in blocks:
        ext = ext_map.get(lang.strip(), 'txt')
        name = f"script.{ext}"
        if name not in files:
            files[name] = code.strip()
    return files


def write_files(files, version_dir):
    written = []
    os.makedirs(version_dir, exist_ok=True)
    for path, content in files.items():
        safe = os.path.normpath(os.path.join(version_dir, path))
        if not safe.startswith(os.path.normpath(version_dir)):
            print(f"  ⚠️  Skipping: {path}")
            continue
        os.makedirs(os.path.dirname(safe), exist_ok=True)
        with open(safe, "w") as f:
            f.write(content)
        written.append(safe)
        print(f"  📄 {path} ({len(content)} bytes)")
    return written


def test_file(filepath, timeout=15):
    ext = os.path.splitext(filepath)[1]
    runners = {".py": ["uv", "run", "python3"], ".sh": ["bash"],
               ".js": ["node"], ".go": ["go", "run"]}
    cmd = runners.get(ext)
    if not cmd:
        return (-1, "", f"Can't run {ext}")
    try:
        r = subprocess.run(cmd + [filepath], capture_output=True, text=True, timeout=timeout)
        return (r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", f"TIMEOUT ({timeout}s)")


def main():
    task_file = sys.argv[1] if len(sys.argv) > 1 else ""
    vid = sys.argv[2] if len(sys.argv) > 2 else "?"

    if os.path.isfile(task_file):
        with open(task_file) as f:
            task = f.read().strip()
    else:
        task = task_file or sys.stdin.read().strip()

    print(f"\n{'='*60}")
    print(f"  🤖 AAN Worker {vid}")
    print(f"  Mode: {CLI_AGENT}  Model: {MODEL}")
    print(f"  Task: {task[:100]}")
    print(f"{'='*60}")

    if CLI_AGENT == "api":
        # Direct API call (best for code generation)
        announce("SYSTEM PROMPT", SYSTEM_PROMPT.replace("\n", "\\n")[:200])
        print(f"\n⏳ Calling API ({MODEL})...", end="", flush=True)
        t0 = time.time()
        response = call_api(task)
        elapsed = time.time() - t0
        print(f" done ({elapsed:.1f}s, {len(response)} chars)")
        announce("LLM RESPONSE", response[:600])
        if len(response) > 600:
            print(f"  ... ({len(response)-600} more chars)")
    else:
        # CLI agent (better for analysis)
        announce("CLI AGENT", CLI_AGENT)
        t0 = time.time()
        response = call_cli(task)
        elapsed = time.time() - t0
        print(f"  done ({elapsed:.1f}s, {len(response)} chars)")
        announce("CLI OUTPUT", f"{len(response)} chars")
        print(response[:600])
        if len(response) > 600:
            print(f"  ... ({len(response)-600} more chars)")

    # Extract files
    version_dir = os.path.join(WORK_DIR, "versions", vid)
    files = extract_files(response)
    if not files:
        files = extract_blocks(response)

    if files:
        announce("FILES", f"{len(files)} extracted")
        written = write_files(files, version_dir)
        announce("TESTING", f"{len(written)} files")
        passed = failed = 0
        for fp in written:
            code, stdout, stderr = test_file(fp)
            name = os.path.relpath(fp, WORK_DIR)
            if code == 0:
                print(f"  ✅ {name}")
                passed += 1
                if stdout.strip():
                    print(f"     {stdout.strip()[:200]}")
            else:
                print(f"  ❌ {name} (exit={code})")
                failed += 1
                if stderr.strip():
                    print(f"     {stderr.strip()[:200]}")
        announce("SUMMARY", f"Worker {vid}")
        print(f"  Files: {len(written)}, Passed: {passed}, Failed: {failed}")
        print(f"  {'✅ ALL PASSED' if failed == 0 else '⚠️  HAS FAILURES'}")
    else:
        announce("RESULT", "Text response (no files)")
        print(response[:500])

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
