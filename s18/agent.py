# Agent

import os
import json
import time
import subprocess
import signal
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import requests

import config

shutdown_flag = False

def signal_handler(signum, frame):
    global shutdown_flag
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def setup_logging():
    config.LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('agent')

logger = setup_logging()

def setup_directories():
    config.AGENTS_DIR.mkdir(exist_ok=True)
    config.MEMORY_DIR.mkdir(exist_ok=True)
    (config.MEMORY_DIR / "context").mkdir(exist_ok=True)
    (config.MEMORY_DIR / "prompts").mkdir(exist_ok=True)
    (config.MEMORY_DIR / "knowledge").mkdir(exist_ok=True)
    (config.MEMORY_DIR / "tools").mkdir(exist_ok=True)
    (config.MEMORY_DIR / "proposals").mkdir(exist_ok=True)
    (config.MEMORY_DIR / "reasoning").mkdir(exist_ok=True)
    config.CREATIONS_DIR.mkdir(exist_ok=True)
    config.LOG_DIR.mkdir(exist_ok=True)

def load_state() -> Dict:
    if config.STATE_FILE.exists():
        state = json.loads(config.STATE_FILE.read_text())
        if "first_run" not in state:
            state["first_run"] = True
        if "intervals" not in state:
            state["intervals"] = config.DEFAULT_INTERVALS
        if "interval_idx" not in state:
            state["interval_idx"] = 0
        if "pending_tasks" not in state:
            state["pending_tasks"] = []
        if "task_history" not in state:
            state["task_history"] = []
        return state
    return {
        "cycle": 0,
        "agents": {},
        "earnings": 0,
        "last_actions": [],
        "logging_policy": None,
        "intervals": config.DEFAULT_INTERVALS,
        "interval_idx": 0,
        "first_run": True,
        "pending_tasks": [],
        "task_history": []
    }

def save_state(state: Dict):
    config.STATE_FILE.write_text(json.dumps(state, indent=2))

def call_ai(messages: List[Dict]) -> str:
    if not config.API_KEY:
        return "No API key available"
    headers = {"Authorization": f"Bearer {config.API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.MODEL, "messages": messages}
    try:
        response = requests.post(f"{config.BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return f"AI error: {e}"

def get_current_files() -> List[Path]:
    files = []
    for base_dir in [config.AGENTS_DIR, config.MEMORY_DIR, config.CREATIONS_DIR]:
        if base_dir.exists():
            files.extend(base_dir.rglob("*"))
    return [f for f in files if f.is_file()]

def load_system_prompt(state: Dict) -> str:
    prompt_file = config.MEMORY_DIR / "prompts" / "system.md"
    if prompt_file.exists():
        prompt = prompt_file.read_text()
        current_files = get_current_files()[:10]
        intervals = state.get("intervals", config.DEFAULT_INTERVALS)
        pending_tasks = state.get("pending_tasks", [])
        task_history = state.get("task_history", [])
        
        human_input = ""
        if config.HUMAN_INPUT_FILE.exists():
            human_input = config.HUMAN_INPUT_FILE.read_text()
        
        return prompt.replace("{{cycle}}", str(state["cycle"])) \
                    .replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) \
                    .replace("{{earnings}}", str(state.get("earnings", 0))) \
                    .replace("{{recent_files}}", json.dumps([str(f.relative_to(config.ROOT_DIR)) for f in current_files], indent=2)) \
                    .replace("{{intervals}}", json.dumps(intervals)) \
                    .replace("{{pending_tasks}}", json.dumps(pending_tasks[:5], indent=2)) \
                    .replace("{{task_history}}", json.dumps(task_history[-config.MAX_STATE_HISTORY:], indent=2)) \
                    .replace("{{human_input}}", human_input or "No recent human input")
    
    return "Explore autonomous opportunities, create value, and earn money legally."

def apply_logging_policy(policy: Dict):
    if policy.get("rotate"):
        for log_file in config.LOG_DIR.glob("*.log"):
            if log_file.stat().st_size > policy.get("max_size_mb", 100) * 1024 * 1024:
                archive_name = f"{log_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                log_file.rename(archive_name)
                logger.info(f"Rotated log: {archive_name}")
    
    keep_days = policy.get("keep_days", 30)
    cutoff = datetime.now().timestamp() - keep_days * 86400
    
    for old_file in config.LOG_DIR.glob("*.*"):
        if old_file.stat().st_mtime < cutoff:
            old_file.unlink()
            logger.info(f"Deleted old log: {old_file.name}")

def execute_command(command: str) -> Dict:
    logger.info(f"  → Executing: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        if result.returncode != 0:
            logger.warning(f"  ✗ Command failed (exit {result.returncode})")
            if result.stderr:
                logger.warning(f"  ✗ Error: {result.stderr.strip()}")
        elif result.stdout:
            logger.info(f"  ✓ Output: {result.stdout.strip()[:200]}")
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        logger.warning(f"  ✗ Command timed out after 120s")
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        logger.warning(f"  ✗ Exception: {e}")
        return {"success": False, "error": str(e)}

def run_agent_cycle(state: Dict, interval_minutes: int):
    setup_directories()
    state["cycle"] += 1
    
    logger.info(f"Starting cycle {state['cycle']} (interval: {interval_minutes}min)")
    
    pending_tasks = state.get("pending_tasks", [])
    if pending_tasks:
        logger.info(f"⚠ Pending tasks: {len(pending_tasks)}")
        for task in pending_tasks:
            logger.info(f"  - {task.get('description', 'No description')[:60]}")
    
    system_prompt = load_system_prompt(state)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Execute cycle {state['cycle']}. Current state: {json.dumps(state, indent=2)}"}
    ]
    
    response = call_ai(messages)
    logger.info(f"AI response received")
    
    state["pending_tasks"] = []
    
    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
        else:
            logger.warning("No JSON found in response")
            result = {}
        
        if thoughts := result.get("thoughts"):
            config.AI_RESPONSES_FILE.parent.mkdir(parents=True, exist_ok=True)
            config.AI_RESPONSES_FILE.write_text(thoughts)
        
        for action in result.get("actions", []):
            action_type = action.get("type")
            description = action.get("description", "")
            command = action.get("command", "")
            
            logger.info(f"Action: {action_type} - {description}")
            
            if command:
                cmd_result = execute_command(command)
                
                if not cmd_result["success"]:
                    state["pending_tasks"].append({
                        "type": action_type,
                        "description": description,
                        "command": command,
                        "error": cmd_result.get("error", "Unknown error"),
                        "attempts": 1,
                        "last_attempt": datetime.now().isoformat()
                    })
                    logger.warning(f"Task added to pending queue (will retry next cycle)")
                    
                    if action_type == "install":
                        logger.info(f"Trying package managers...")
                        for pkg_cmd in [
                            f"apt install -y {command}",
                            f"sudo apt install -y {command}",
                            f"npm install -g {command}",
                            f"pip install {command}"
                        ]:
                            result = execute_command(pkg_cmd)
                            if result["success"]:
                                logger.info(f"Successfully installed via: {pkg_cmd}")
                                state["pending_tasks"].pop()
                                break
                else:
                    task_history = state.get("task_history", [])
                    task_history.append({
                        "type": action_type,
                        "description": description,
                        "command": command,
                        "success": True,
                        "completed": datetime.now().isoformat()
                    })
                    state["task_history"] = task_history[-config.MAX_TASK_HISTORY:]
        
        for update in result.get("file_updates", []):
            file_path = config.ROOT_DIR / update["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(update["content"])
            logger.info(f"Wrote file: {update['path']}")
        
        for proposal in result.get("proposals_for_human", []):
            proposal_file = config.MEMORY_DIR / "proposals" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{proposal['title'].replace(' ', '_')}.json"
            proposal_file.write_text(json.dumps(proposal, indent=2))
            logger.info(f"Created proposal: {proposal['title']}")
        
        if logging_policy := result.get("logging_policy"):
            state["logging_policy"] = logging_policy
            apply_logging_policy(logging_policy)
        
        if intervals := result.get("intervals"):
            if isinstance(intervals, list) and len(intervals) > 0:
                state["intervals"] = intervals
                logger.info(f"Updated intervals: {intervals}")
        
        if skip_pending := result.get("skip_pending"):
            to_skip = [t for t in state["pending_tasks"] if any(s in t.get("description", "") for s in skip_pending)]
            for task in to_skip:
                logger.info(f"Skipping pending task: {task.get('description', '')[:50]}")
            state["pending_tasks"] = [t for t in state["pending_tasks"] if t not in to_skip]
        
        state["last_actions"] = result.get("actions", [])[:5]
        state["earnings"] = state.get("earnings", 0) + result.get("earnings_delta", 0)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        logger.debug(f"Response was: {response[:500]}")
    
    save_state(state)
    logger.info(f"Cycle {state['cycle']} completed")

def process_commands(state: Dict) -> bool:
    if not config.COMMANDS_FILE.exists():
        return False
    
    try:
        commands = json.loads(config.COMMANDS_FILE.read_text())
    except:
        return False
    
    unprocessed = [c for c in commands if not c.get("processed", False)]
    
    for cmd in unprocessed:
        command = cmd.get("command", "").strip().lower()
        logger.info(f"📥 Received command from TUI: {cmd.get('command', '')}")
        
        if command in ["quit", "stop", "exit"]:
            global shutdown_flag
            shutdown_flag = True
            logger.info("🛑 Shutdown requested via TUI")
        elif command in ["run", "execute", "now", "trigger"]:
            state["first_run"] = True
            save_state(state)
            logger.info("▶️ Immediate execution requested via TUI")
        elif command.startswith("skip "):
            task_to_skip = command[5:].strip()
            if skip_pending := state.get("skip_pending"):
                skip_pending.append(task_to_skip)
            else:
                state["skip_pending"] = [task_to_skip]
            save_state(state)
            logger.info(f"⏭️ Skip task requested: {task_to_skip}")
        else:
            logger.info(f"💬 Adding human input to context: {cmd.get('command', '')}")
            human_input_file = config.HUMAN_INPUT_FILE
            existing = human_input_file.read_text() if human_input_file.exists() else ""
            human_input_file.write_text(
                f"{existing}\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{cmd.get('command', '')}\n"
            )
        
        cmd["processed"] = True
    
    processed_commands = [c for c in commands if c.get("processed", False)]
    if len(processed_commands) == len(commands):
        config.COMMANDS_FILE.unlink()
    else:
        config.COMMANDS_FILE.write_text(json.dumps(commands, indent=2))
    
    return len(unprocessed) > 0

def run():
    logger.info("=" * 60)
    logger.info("Starting Openclaw-style Autonomous Agent System")
    logger.info("=" * 60)
    
    state = load_state()
    
    if policy := state.get("logging_policy"):
        apply_logging_policy(policy)
    
    while not shutdown_flag:
        state = load_state()
        
        if process_commands(state):
            state = load_state()
        
        intervals = state.get("intervals", config.DEFAULT_INTERVALS)
        interval_idx = state.get("interval_idx", 0)
        interval = intervals[interval_idx]
        first_run = state.get("first_run", False)
        pending_tasks = state.get("pending_tasks", [])
        
        if first_run:
            logger.info("First run - executing immediately")
            state["first_run"] = False
            save_state(state)
        elif pending_tasks:
            logger.info(f"🔄 Pending tasks detected ({len(pending_tasks)}), retrying immediately")
            time.sleep(5)
        else:
            logger.info(f"Next cycle in {interval} minutes (intervals: {intervals})")
            
            for remaining in range(interval * 60, 0, -5):
                if shutdown_flag:
                    break
                time.sleep(5)
                if process_commands(state):
                    state = load_state()
                    break
            
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
