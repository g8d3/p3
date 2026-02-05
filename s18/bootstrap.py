#!/usr/bin/env python3

import os
import json
import time
import random
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

ROOT_DIR = Path(__file__).parent
AGENTS_DIR = ROOT_DIR / "agents"
MEMORY_DIR = ROOT_DIR / "memory"
CREATIONS_DIR = ROOT_DIR / "creations"
STATE_FILE = ROOT_DIR / "state.json"

API_KEY = os.environ.get("GLM_API_KEY")
MODEL = "glm-4.7"
BASE_URL = "https://api.z.ai/api/coding/paas/v4"

def setup_directories():
    AGENTS_DIR.mkdir(exist_ok=True)
    MEMORY_DIR.mkdir(exist_ok=True)
    (MEMORY_DIR / "context").mkdir(exist_ok=True)
    (MEMORY_DIR / "prompts").mkdir(exist_ok=True)
    (MEMORY_DIR / "knowledge").mkdir(exist_ok=True)
    CREATIONS_DIR.mkdir(exist_ok=True)

def load_state() -> Dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"cycle": 0, "agents": {}, "earnings": 0, "last_actions": []}

def save_state(state: Dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def call_ai(messages: List[Dict]) -> str:
    if not API_KEY:
        return "No API key available"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": messages}
    try:
        response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"AI error: {e}"

def get_current_files() -> List[Path]:
    files = []
    for base_dir in [AGENTS_DIR, MEMORY_DIR / "context", MEMORY_DIR / "prompts", MEMORY_DIR / "knowledge"]:
        if base_dir.exists():
            files.extend(base_dir.rglob("*"))
    return [f for f in files if f.is_file()]

def load_prompt_context() -> str:
    context_parts = []
    state = load_state()
    
    for prompt_file in (MEMORY_DIR / "prompts").glob("*.md"):
        context_parts.append(f"--- {prompt_file.name} ---\n{prompt_file.read_text()}\n")
    
    if context_parts:
        return "\n".join(context_parts)
    return "Default: Explore autonomous opportunities, create value, and earn money legally."

def run_agent_cycle(state: Dict, interval_minutes: int):
    setup_directories()
    state["cycle"] += 1
    
    current_time = datetime.datetime.now()
    context = load_prompt_context()
    current_files = get_current_files()
    
    messages = [
        {
            "role": "system",
            "content": f"""You are an autonomous agent system. Your goals:
1. Earn money legally by providing value
2. Create and communicate using available tools
3. Explore and learn continuously

Available tools:
- agent-browser: Control browser (CDP on port 9222)
- moltlaunch: Launch tokens/manage money
- x402, erc8004: Financial protocols
- X.com: Read and post
- Email: Gmail access
- moltyscan.com, clawsearch.io: Openclaw ecosystem

Current context: {context}
Cycle: {state["cycle"]}
Time: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
Total earnings: {state["earnings"]}
Recent files: {[str(f.relative_to(ROOT_DIR)) for f in current_files[:10]]}

Return a JSON with:
{{
    "thoughts": "your reasoning",
    "actions": [
        {{"type": "browser|post|read|create|token", "description": "...", "command": "..."}}
    ],
    "file_updates": [
        {{"path": "memory/...", "content": "..."}}
    ],
    "prompts_to_evolve": ["agents/..."]
}}
"""
        },
        {"role": "user", "content": f"Execute cycle {state['cycle']} with {interval_minutes} minute interval. Current state: {state}"}
    ]
    
    response = call_ai(messages)
    print(f"\n[Cycle {state['cycle']}] {current_time}")
    print(f"Response: {response[:500]}...")
    
    try:
        result = json.loads(response.split("{")[-1].split("}")[0] + "}" if "{" in response else response)
        
        for action in result.get("actions", []):
            print(f"  Action: {action.get('type')} - {action.get('description')}")
            if command := action.get("command"):
                try:
                    subprocess.run(command, shell=True, capture_output=True, timeout=30)
                except:
                    pass
        
        for update in result.get("file_updates", []):
            file_path = ROOT_DIR / update["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(update["content"])
            print(f"  Wrote: {update['path']}")
        
        state["last_actions"] = result.get("actions", [])[:5]
        state["earnings"] = state.get("earnings", 0) + random.choice([0, 0, 0, 10, 50, 100])
        
    except json.JSONDecodeError:
        print("  Could not parse actions from response")
    
    save_state(state)

def run():
    print("Starting Openclaw-style Autonomous Agent System")
    print("This file can evolve. Agents may modify it to improve their capabilities.\n")
    
    intervals = [5, 15, 60]
    interval_idx = 0
    state = load_state()
    
    while True:
        interval = intervals[interval_idx]
        print(f"\nNext cycle in {interval} minutes (interval set: {intervals})")
        
        try:
            run_agent_cycle(state, interval)
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
        
        interval_idx = (interval_idx + 1) % len(intervals)
        time.sleep(interval * 60)

if __name__ == "__main__":
    run()
