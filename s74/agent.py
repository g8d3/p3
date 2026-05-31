#!/usr/bin/env python3
"""s74 agent — IA que modifica código en un worktree."""

import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    worktree = Path(sys.argv[1])
    task_desc = sys.argv[2]
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    base_url = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")

    print(f"agent: worktree={worktree} task={task_desc[:60]}...")

    # 1. Leer todos los archivos del worktree
    files = {}
    for fpath in sorted(worktree.rglob("*")):
        if fpath.is_file() and ".git" not in str(fpath) and fpath.suffix in (".py", ".html", ".js", ".css", ".json", ".yaml", ".yml", ".md", ".sh"):
            rel = fpath.relative_to(worktree)
            files[str(rel)] = fpath.read_text()

    # 2. Armar el prompt con solo server.py (el archivo principal)
    # Read relevant files from the version directory
    html_code = files.get("web/index.html", "")
    
    prompt = f"""You are editing a web app. The app's HTML file content is below.

Task: {task_desc}

Current web/index.html (first 100 lines):
{chr(10).join(html_code.split(chr(10))[:100])}
...(total {len(html_code.split(chr(10)))} lines)

Respond with a JSON object containing "edits" - a list of find/replace operations.
Each edit has: {{"file": "web/index.html", "find": "exact text to find", "replace": "replacement text"}}

Example:
{{"edits": [
  {{"file": "web/index.html", "find": "<title>Old Title</title>", "replace": "<title>New Title</title>"}}
]}}

Rules:
- "find" must be an EXACT match of text that exists in web/index.html
- Valid JSON. No markdown, no other text."""

    # Only include web/index.html content
    relevant = {"web/index.html": html_code}
    
    files_section = "\n\n".join(
        f"### {name}\n```\n{content}\n```"
        for name, content in relevant.items()
    )

    print(f"agent: prompt length={len(prompt)}")

    # 3. Llamar a la API"

    # 3. Llamar a la API
    import httpx
    payload = {
        "model": os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash"),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    }

    resp = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        json=payload, headers=headers, timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = (msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
    print(f"agent: LLM response length={len(content)}")

    if not content:
        print("agent: empty LLM response")
        sys.exit(1)

    # 4. Parsear JSON de la respuesta
    # Limpiar posibles ```json ... ``` markers
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if "```" in content:
            content = content.rsplit("```", 1)[0]
    content = content.strip()

    try:
        changes = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON with "files" key from text
        import re
        # Find a JSON object that contains "files"
        start = content.find('{"files"')
        if start < 0:
            start = content.find('{"files"'.lower())
        if start < 0:
            # Try reasoning_content
            reasoning = (msg.get("reasoning_content") or msg.get("reasoning") or "")
            start = reasoning.find('{"files"')
        if start >= 0:
            # Match braces
            depth = 0
            for i in range(start, len(content if start > 0 else reasoning)):
                text = content if start < len(content) else reasoning
                if i >= len(text): break
                if text[i] == '{': depth += 1
                elif text[i] == '}': depth -= 1
                if depth == 0:
                    try:
                        changes = json.loads(text[start:i+1])
                        print(f"agent: extracted JSON from text")
                        break
                    except json.JSONDecodeError:
                        continue
        if not changes:
            print(f"agent: could not extract JSON from response")
            print(f"agent: first 300 chars: {content[:300]}")
            sys.exit(1)
    print(f"agent: changes keys={list(changes.keys()) if isinstance(changes, dict) else 'not_dict'}")
    
    # Support both "files" (full content) and "edits" (find/replace) formats
    if "edits" in changes:
        edits = changes["edits"]
        print(f"agent: applying {len(edits)} edits")
        for edit in edits:
            fpath = worktree / edit["file"]
            if fpath.exists():
                old = fpath.read_text()
                find = edit.get("find", "")
                replace = edit.get("replace", "")
                if find in old:
                    new = old.replace(find, replace, 1)
                    fpath.write_text(new)
                    print(f"agent: edited {edit['file']} ({len(find)}→{len(replace)} chars)")
                else:
                    print(f"agent: WARNING find text not found in {edit['file']}")
                    print(f"agent: first 40 chars of find: {find[:40]}")
            else:
                print(f"agent: WARNING file not found: {edit['file']}")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"agent: {task_desc[:80]}"], cwd=worktree, check=True, capture_output=True)
        print("agent: committed")
        return
    
    # Legacy "files" format
    changed_files = changes.get("files", changes)
    if isinstance(changed_files, dict):
        for fn, fc in list(changed_files.items())[:5]:
            print(f"agent: file={fn} size={len(str(fc))}")

    if not changed_files:
        print("agent: no file changes returned")
        sys.exit(0)

    # 5. Escribir cambios
    for relpath, new_content in changed_files.items():
        fpath = worktree / relpath
        fpath.parent.mkdir(parents=True, exist_ok=True)
        # Si el contenido está envuelto en ```, limpiarlo
        if new_content.startswith("```"):
            lines = new_content.split("\n")
            if len(lines) >= 3:
                new_content = "\n".join(lines[1:-1])
        fpath.write_text(new_content)
        print(f"agent: wrote {relpath} ({len(new_content)} chars)")

    # 6. Commit
    subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"agent: {task_desc[:80]}"], cwd=worktree, check=True, capture_output=True)
    print("agent: committed")


if __name__ == "__main__":
    main()
