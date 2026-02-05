#!/usr/bin/env python3

import os
import json
import time
import random
import subprocess
import signal
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import requests

ROOT_DIR = Path(__file__).parent
AGENTS_DIR = ROOT_DIR / "agents"
MEMORY_DIR = ROOT_DIR / "memory"
CREATIONS_DIR = ROOT_DIR / "creations"
STATE_FILE = ROOT_DIR / "state.json"
LOG_DIR = ROOT_DIR / "logs"

API_KEY = os.environ.get("GLM_API_KEY")
MODEL = "glm-4.7"
BASE_URL = "https://api.z.ai/api/coding/paas/v4"

shutdown_flag = False

def signal_handler(signum, frame):
    global shutdown_flag
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_DIR / 'bootstrap.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('bootstrap')

logger = setup_logging()

def setup_directories():
    AGENTS_DIR.mkdir(exist_ok=True)
    MEMORY_DIR.mkdir(exist_ok=True)
    (MEMORY_DIR / "context").mkdir(exist_ok=True)
    (MEMORY_DIR / "prompts").mkdir(exist_ok=True)
    (MEMORY_DIR / "knowledge").mkdir(exist_ok=True)
    (MEMORY_DIR / "tools").mkdir(exist_ok=True)
    (MEMORY_DIR / "proposals").mkdir(exist_ok=True)
    (MEMORY_DIR / "reasoning").mkdir(exist_ok=True)
    CREATIONS_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

def load_state() -> Dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        if "first_run" not in state:
            state["first_run"] = True
        if "intervals" not in state:
            state["intervals"] = [1, 3, 5]
        if "interval_idx" not in state:
            state["interval_idx"] = 0
        return state
    return {
        "cycle": 0,
        "agents": {},
        "earnings": 0,
        "last_actions": [],
        "logging_policy": None,
        "intervals": [1, 3, 5],
        "interval_idx": 0,
        "first_run": True
    }

def save_state(state: Dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def call_ai(messages: List[Dict]) -> str:
    if not API_KEY:
        return "No API key available"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": messages}
    try:
        response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return f"AI error: {e}"

def get_current_files() -> List[Path]:
    files = []
    for base_dir in [AGENTS_DIR, MEMORY_DIR, CREATIONS_DIR]:
        if base_dir.exists():
            files.extend(base_dir.rglob("*"))
    return [f for f in files if f.is_file()]

def load_system_prompt(state: Dict) -> str:
    prompt_file = MEMORY_DIR / "prompts" / "system.md"
    if prompt_file.exists():
        prompt = prompt_file.read_text()
        current_files = get_current_files()[:10]
        intervals = state.get("intervals", [1, 3, 5])
        
        return prompt.replace("{{cycle}}", str(state["cycle"])) \
                    .replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) \
                    .replace("{{earnings}}", str(state.get("earnings", 0))) \
                    .replace("{{recent_files}}", json.dumps([str(f.relative_to(ROOT_DIR)) for f in current_files], indent=2)) \
                    .replace("{{intervals}}", json.dumps(intervals))
    
    return "Explore autonomous opportunities, create value, and earn money legally."

def apply_logging_policy(policy: Dict):
    if policy.get("rotate"):
        for log_file in LOG_DIR.glob("*.log"):
            if log_file.stat().st_size > policy.get("max_size_mb", 100) * 1024 * 1024:
                archive_name = f"{log_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                log_file.rename(archive_name)
                logger.info(f"Rotated log: {archive_name}")
    
    keep_days = policy.get("keep_days", 30)
    cutoff = datetime.now().timestamp() - keep_days * 86400
    
    for old_file in LOG_DIR.glob("*.*"):
        if old_file.stat().st_mtime < cutoff:
            old_file.unlink()
            logger.info(f"Deleted old log: {old_file.name}")

def execute_command(command: str) -> Dict:
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_agent_cycle(state: Dict, interval_minutes: int):
    setup_directories()
    state["cycle"] += 1
    
    logger.info(f"Starting cycle {state['cycle']} (interval: {interval_minutes}min)")
    
    system_prompt = load_system_prompt(state)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Execute cycle {state['cycle']}. Current state: {json.dumps(state, indent=2)}"}
    ]
    
    response = call_ai(messages)
    logger.info(f"AI response received")
    
    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
        else:
            logger.warning("No JSON found in response")
            result = {}
        
        for action in result.get("actions", []):
            action_type = action.get("type")
            description = action.get("description", "")
            command = action.get("command", "")
            
            logger.info(f"Action: {action_type} - {description}")
            
            if command:
                cmd_result = execute_command(command)
                
                if not cmd_result["success"] and action_type == "install":
                    logger.info(f"Install failed, trying package managers...")
                    for pkg_cmd in [
                        f"apt install -y {command}",
                        f"sudo apt install -y {command}",
                        f"npm install -g {command}",
                        f"pip install {command}"
                    ]:
                        result = execute_command(pkg_cmd)
                        if result["success"]:
                            logger.info(f"Successfully installed via: {pkg_cmd}")
                            break
                
                if cmd_result["error"]:
                    logger.warning(f"Command error: {cmd_result['error']}")
        
        for update in result.get("file_updates", []):
            file_path = ROOT_DIR / update["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(update["content"])
            logger.info(f"Wrote file: {update['path']}")
        
        for proposal in result.get("proposals_for_human", []):
            proposal_file = MEMORY_DIR / "proposals" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{proposal['title'].replace(' ', '_')}.json"
            proposal_file.write_text(json.dumps(proposal, indent=2))
            logger.info(f"Created proposal: {proposal['title']}")
        
        if logging_policy := result.get("logging_policy"):
            state["logging_policy"] = logging_policy
            apply_logging_policy(logging_policy)
        
        if intervals := result.get("intervals"):
            if isinstance(intervals, list) and len(intervals) > 0:
                state["intervals"] = intervals
                logger.info(f"Updated intervals: {intervals}")
        
        state["last_actions"] = result.get("actions", [])[:5]
        state["earnings"] = state.get("earnings", 0) + result.get("earnings_delta", 0)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        logger.debug(f"Response was: {response[:500]}")
    
    save_state(state)
    logger.info(f"Cycle {state['cycle']} completed")

def run():
    logger.info("=" * 60)
    logger.info("Starting Openclaw-style Autonomous Agent System")
    logger.info("=" * 60)
    
    state = load_state()
    
    if policy := state.get("logging_policy"):
        apply_logging_policy(policy)
    
    while not shutdown_flag:
        state = load_state()
        intervals = state.get("intervals", [1, 3, 5])
        interval_idx = state.get("interval_idx", 0)
        interval = intervals[interval_idx]
        first_run = state.get("first_run", False)
        
        if first_run:
            logger.info("First run - executing immediately")
            state["first_run"] = False
            save_state(state)
        else:
            logger.info(f"Next cycle in {interval} minutes (intervals: {intervals})")
            
            for remaining in range(interval * 60, 0, -10):
                if shutdown_flag:
                    break
                time.sleep(10)
            
            if shutdown_flag:
                break
        
        try:
            run_agent_cycle(state, interval)
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
            time.sleep(60)
        
        state = load_state()
        state["interval_idx"] = (interval_idx + 1) % len(intervals)
        save_state(state)
    
    logger.info("Shutting down gracefully...")

if __name__ == "__main__":
    run()
