# Using the Content Agent Prompt with Karpathy-Style Autoresearch

## What is Autoresearch?

Karpathy's "autoresearch" concept describes an autonomous AI agent that follows
a continuous loop: **Research → Plan → Execute → Evaluate → Iterate**.

Applied to content creation, it means the agent:
1. Decides what to create (research trending topics)
2. Plans the content structure
3. Executes the pipeline (record, TTS, assemble)
4. Evaluates the output (quality check, engagement prediction)
5. Learns from results and improves

The master prompt (`CONTENT_AGENT_MASTER_PROMPT.md`) is designed to be the 
foundational instruction set for such an agent. This guide explains how to
integrate it into an autoresearch framework.

---

## Framework Options

### Option 1: Direct LLM Loop (Simplest)

If you're using an AI coding assistant (Claude Code, Cursor, Windsurf, Codex):

```bash
# Run one content cycle
cat CONTENT_AGENT_MASTER_PROMPT.md | your-agent --task "Create a video reviewing UV (Python package manager). Write the script, record the demo, generate voiceover, assemble, and save the post package."
```

The agent reads the prompt, understands the full pipeline, and executes it step
by step using the codebase as tools.

**To make it recursive/autoresearch:**
```bash
# After each run, feed the output back:
your-agent --prompt "$(cat CONTENT_AGENT_MASTER_PROMPT.md)" \
           --task "Review the last video in output/ and the personality in config/personality.yaml. 
                   Decide what to improve. Then create a new video with those improvements."
```

### Option 2: Python Autoresearch Loop

A structured loop that:
1. Reads the master prompt as system context
2. Calls an LLM API to generate the script
3. Executes the pipeline
4. Evaluates the result
5. Updates the personality config
6. Loops

```python
"""
autoresearch_runner.py — Karpathy-style autonomous content loop
"""

import os, json, yaml, subprocess
from pathlib import Path
from datetime import datetime
import requests  # or anthropic, openai, etc.

MASTER_PROMPT = Path("CONTENT_AGENT_MASTER_PROMPT.md").read_text()
PERSONALITY_PATH = Path("config/personality.yaml")

def generate_script_via_llm(topic: str, personality: dict) -> str:
    """Call an LLM API to generate a script using the master prompt as guide."""
    
    system_prompt = MASTER_PROMPT + "\n\n" + \
                    f"Current personality:\n{yaml.dump(personality)}"
    
    user_prompt = f"""Write a review script for {topic}. 
The script should be 45-90 seconds when spoken.
Use the personality defined above.
Mark SFX cues with *asterisks*.
Structure: hook → what is it → good → bad → verdict → CTA."""

    # Example with OpenAI-compatible API:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.9,  # higher = more creative
        }
    )
    return response.json()["choices"][0]["message"]["content"]


def evaluate_video(video_path: str, script: str) -> dict:
    """Evaluate the generated video for quality and viral potential."""
    
    video_size = Path(video_path).stat().st_size if Path(video_path).exists() else 0
    script_words = len(script.split())
    
    # Basic quality metrics (expand with real engagement data)
    evaluation = {
        "video_exists": Path(video_path).exists(),
        "video_size_mb": round(video_size / 1024 / 1024, 1),
        "script_word_count": script_words,
        "has_narration": True,  # check if audio track exists
        "has_captions": True,   # check if subtitles were generated
        "estimated_quality": "good" if script_words > 80 else "needs improvement",
        "viral_score": min(10, script_words / 20),  # simple heuristic
    }
    
    return evaluation


def update_personality(evaluation: dict, personality_path: Path):
    """Feed evaluation results back into personality profile."""
    p = yaml.safe_load(personality_path.read_text())
    
    p["learning"]["iterations"] += 1
    p["learning"]["engagement_history"].append({
        "timestamp": datetime.now().isoformat(),
        "evaluation": evaluation,
    })
    
    # Auto-adjust tone based on quality
    if evaluation.get("estimated_quality") == "needs improvement":
        p["voice"]["energy"] = "high"  # more energy = more engaging
    
    personality_path.write_text(yaml.dump(p, default_flow_style=False, sort_keys=False))


def autoresearch_loop(iterations: int = 5, topic: str = None):
    """Main autoresearch loop."""
    
    for i in range(iterations):
        print(f"\n{'='*60}")
        print(f"  Iteration {i+1}/{iterations}")
        print(f"{'='*60}\n")
        
        # 1. RESEARCH — pick topic
        if not topic:
            # Could use the LLM to pick or rotate through a list
            topics = ["OpenMontage", "Testreel", "Cursor IDE", "UV", "Ollama"]
            topic = topics[i % len(topics)]
        
        # 2. PLAN — load personality + generate script
        personality = yaml.safe_load(PERSONALITY_PATH.read_text())
        print(f"[Research] Topic: {topic}")
        
        script = generate_script_via_llm(topic, personality)
        print(f"[Plan] Script generated ({len(script.split())} words)")
        
        # 3. EXECUTE — run the pipeline
        print(f"[Execute] Running pipeline...")
        result = subprocess.run([
            "python", "run.py", "--topic", topic, "--no-record"
        ], capture_output=True, text=True, timeout=300)
        
        print(result.stdout[-500:] if result.stdout else result.stderr[-500:])
        
        # 4. EVALUATE — check output quality
        video_path = f"tmp/review-{topic.lower().replace(' ', '-')}-*.final.mp4"
        eval_result = evaluate_video(video_path, script)
        print(f"[Evaluate] {json.dumps(eval_result, indent=2)}")
        
        # 5. ITERATE — update personality with learnings
        update_personality(eval_result, PERSONALITY_PATH)
        print(f"[Iterate] Personality updated")
        
        # Brief pause between iterations
        import time
        time.sleep(2)


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    topic = sys.argv[2] if len(sys.argv) > 2 else None
    autoresearch_loop(iterations=n, topic=topic)
```

### Option 3: Shell-Based Autoresearch (Lightweight)

```bash
#!/usr/bin/env bash
# autoresearch.sh — lightweight autonomous content loop

set -euo pipefail
cd "$(dirname "$0")"

ITERATIONS=${1:-3}
MASTER_PROMPT=$(cat CONTENT_AGENT_MASTER_PROMPT.md)

for i in $(seq 1 $ITERATIONS); do
    echo "=== Iteration $i/$ITERATIONS ==="
    
    # Read current personality
    TONE=$(python3 -c "import yaml; p=yaml.safe_load(open('config/personality.yaml')); print(p['voice']['tone'])")
    ENERGY=$(python3 -c "import yaml; p=yaml.safe_load(open('config/personality.yaml')); print(p['voice']['energy'])")
    echo "Current state: tone=$TONE energy=$ENERGY"
    
    # Run the pipeline
    source .venv/bin/activate
    python run.py --no-record
    
    # Toggle energy for variety (simple iteration)
    if [ "$ENERGY" = "high" ]; then
        python3 -c "
import yaml
p=yaml.safe_load(open('config/personality.yaml'))
p['voice']['energy'] = 'medium'
p['learning']['iterations'] += 1
yaml.dump(p, open('config/personality.yaml', 'w'), default_flow_style=False, sort_keys=False)
"
    else
        python3 -c "
import yaml
p=yaml.safe_load(open('config/personality.yaml'))
p['voice']['energy'] = 'high'
p['learning']['iterations'] += 1
yaml.dump(p, open('config/personality.yaml', 'w'), default_flow_style=False, sort_keys=False)
"
    fi
    
    echo "=== Iteration $i complete ==="
    sleep 5
done
```

---

## Integrating with Agent Frameworks

### Claude Code / Cursor / Windsurf

1. Place `CONTENT_AGENT_MASTER_PROMPT.md` in your project root
2. When invoking the agent, start with:
   ```
   Read and adopt the persona and workflow in CONTENT_AGENT_MASTER_PROMPT.md.
   Then create a video reviewing [topic].
   ```
3. The agent will use the prompt as its system instructions

### OpenCode / Codex CLI

```bash
opencode --prompt "$(cat CONTENT_AGENT_MASTER_PROMPT.md)" \
         --task "Run the content creation pipeline for a review of Ollama. 
                 Execute the full pipeline: dry-run first, then full run."
```

### AutoGPT / BabyAGI / LangChain Agent

Set the master prompt as the agent's system message and the `run.py` script
as the primary tool/action. The agent plans tasks, executes pipeline stages,
and evaluates results.

### Cron-Based (Fully Autonomous)

Already implemented in `agent/scheduler.py`:
```bash
python agent/scheduler.py set-multi
```
This sets 3 cron jobs (9am, 3pm, 9pm) that run the pipeline automatically.
Each run generates a new video with a randomly selected topic.

---

## Evaluation & Iteration Strategy

The autoresearch loop improves content through:

| Dimension | How to Measure | How to Improve |
|---|---|---|
| Script quality | Word count, hook strength, structure | Use better LLM, higher temperature, more specific prompts |
| TTS quality | Listen test, naturalness score | Upgrade to better voice/backend |
| Video quality | Resolution, duration match, subtitle sync | Tune ffmpeg params, improve timing estimation |
| Engagement (real) | Views, likes, shares, comments | Feed numbers into personality.yaml, adjust tone/energy |
| Engagement (predicted) | Viral score heuristic | A/B test different hooks, structures, tones |

---

## Quick Reference

```bash
# Single run
python run.py

# Dry run (preview)
python run.py --dry-run

# Specific topic
python run.py --topic "Ollama"

# Full autoresearch loop (5 iterations)
python autoresearch_runner.py 5

# Lightweight shell loop
bash autoresearch.sh 3

# Schedule autonomous runs
python agent/scheduler.py set-multi

# View current personality state
python -c "from agent.personality import iteration_report; print(iteration_report())"

# Get the persona prompt (for injecting into other agents)
python -c "from agent.personality import get_persona_prompt; print(get_persona_prompt())"
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTORESEARCH LOOP                             │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ RESEARCH │───→│  PLAN    │───→│ EXECUTE  │───→│ EVALUATE │  │
│  │ (topic)  │    │ (script) │    │ (video)  │    │ (quality)│  │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘  │
│       ↑                                                │        │
│       └────────────────── ITERATE ─────────────────────┘        │
│                          (personality.yaml update)               │
└─────────────────────────────────────────────────────────────────┘
```

---

*This integration guide is designed to work with any LLM that can read 
files and run shell commands. The `CONTENT_AGENT_MASTER_PROMPT.md` file 
contains all the domain knowledge needed — no additional training required.*
