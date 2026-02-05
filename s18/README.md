# Autonomous Agent System

Autonomous economic agents that explore, create value, and earn money.

## Quick Start

```bash
# Install dependencies (using uv - recommended)
uv pip install -r requirements.txt

# Or using pip
python3 -m pip install -r requirements.txt

# Run the system (single terminal, auto-starts agent)
./main.py
```

**IMPORTANT**: The UI automatically starts `agent.py` as a background process. Everything runs in one terminal with tabs for:
- Live logs
- System state
- Files
- Schedule - Manage interval schedules (add/remove/edit intervals)
- Chat with agent (shows both your input and AI responses)
- **Ctrl+Q** quits both UI and agent

**TUI Features:**
- Tab 1 (Logs): Live logs with auto-scroll (shows everything happening)
- Tab 2 (State): System state, pending tasks, recent actions
- Tab 3 (Files): File browser (memory/, creations/, agents/)
- Tab 4 (Chat): 
  - Shows AI responses in real-time (extracted from agent thoughts)
  - Send commands, questions, or greetings
  - Type `run`/`now` to trigger immediate cycle
  - Type `skip <task>` to skip pending tasks
  - Type `quit`/`stop` to shutdown
  - AI responses are automatically shown when available

**Note:**
- TUI requires a terminal supporting UTF-8 and at least 80x24 characters
- Screenshots saved by agent-browser need absolute paths (e.g., `/home/vuos/code/p3/s18/creations/screenshot.png`)
- TUI automatically starts bootstrap.py in background (no need for manual startup)

**First run behavior:** The system executes immediately without waiting, then uses intervals for subsequent cycles. Default intervals: `[1, 3, 5]` minutes (rotating). The AI can dynamically adjust these intervals.

**Event-driven execution:** When commands fail, they're added to `pending_tasks` and the system immediately retries (no wait). Successful commands are tracked in `task_history`. The AI can skip pending tasks with `skip_pending` field.

## Running Uninterruptedly (Optional)

Since TUI now starts bootstrap.py automatically, these are optional for production use:

### Option 1: Systemd User Instance (Recommended - inherits your env)

```bash
# Install user service (copy already created)
systemctl --user daemon-reload
systemctl --user enable --now agent-bootstrap

# Check status
systemctl --user status agent-bootstrap

# View logs
journalctl --user -u agent-bootstrap -f
```

Put `GLM_API_KEY=$GLM_API_KEY` in `.env` or set it in your shell profile.

### Option 2: Systemd System Service

```bash
sudo cp agent-bootstrap.service /etc/systemd/system/
# Edit .env with actual key (no variable expansion works here)
sudo systemctl daemon-reload
sudo systemctl enable --now agent-bootstrap
```

### Option 2: Run Agent Only (without UI)

```bash
# For debugging or production use
python3 agent.py
```

### Option 3: Systemd User Instance (Recommended for production)

```bash
# Install user service (copy already created)
systemctl --user daemon-reload
systemctl --user enable --now agent-bootstrap

# Check status
systemctl --user status agent-bootstrap
```

### Option 3: Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip3 install requests

ENV GLM_API_KEY=""
CMD ["python3", "bootstrap.py"]
```

```bash
docker build -t agent-bootstrap .
docker run -d --restart always \
  -e GLM_API_KEY="your_key" \
  -v $(pwd):/app \
  --name agent-bootstrap \
  agent-bootstrap
```

### Option 4: Cron with Wrapper

```bash
# Create wrapper script
cat > run_wrapper.sh <<'EOF'
#!/bin/bash
while true; do
    python3 bootstrap.py
    sleep 10
done
EOF
chmod +x run_wrapper.sh

# Add to crontab (runs at boot)
@reboot cd $PWD && ./run_wrapper.sh >> logs/cron.log 2>&1
```

## Restart on Failures

All methods above handle restarts:

- **Systemd**: `Restart=always` + `RestartSec=60`
- **Docker**: `--restart always`
- **Screen/Tmux**: Wrap in while loop
- **Cron**: Wrapper script with while loop

## Environment Variables

Copy the example and edit:
```bash
cp .env.example .env
nano .env
```

For systemd user instance, use `GLM_API_KEY=$GLM_API_KEY` to inherit from your shell. Or set directly.

## Directory Structure

```
.
├── main.py                  # Entry point (launches UI)
├── ui.py                    # TUI interface (tabs: logs, state, files, chat)
├── agent.py                 # Core agent logic (AI, state, execution)
├── config.py                # Configuration and constants (declarative)
├── requirements.txt          # Python dependencies
├── .commands.json          # UI commands (deleted after processing)
├── state.json               # System state (cycle, intervals, earnings, etc.)
├── logs/                    # Logs (AI decides rotation policy)
├── agents/                  # Agent configurations
├── memory/
│   ├── prompts/             # Dynamic prompts (loaded each cycle)
│   │   └── system.md        # Main system prompt
│   ├── context/             # Agent context
│   ├── knowledge/           # Learned information
│   ├── tools/               # Tool documentation
│   ├── proposals/           # Proposals for human review
│   ├── reasoning/           # Decision reasoning
│   ├── human_input.md      # Human input from UI
│   └── ai_responses.md     # AI responses for UI chat
└── creations/               # Generated content
```

**state.json fields:**
- `cycle`: Current cycle number
- `intervals`: Array of minute values e.g., `[1, 3, 5]`
- `interval_idx`: Current position in intervals array
- `earnings`: Total earnings tracked
- `logging_policy`: Log rotation settings
- `first_run`: Auto-set to false after first execution
- `pending_tasks`: Array of failed tasks waiting retry
- `task_history`: Last 50 successful task executions

## Evolution

The system can evolve itself:
- AI modifies prompts in `memory/prompts/`
- New configurations via `state.json` updates
- Tools installed as needed
- Logging policies decided by AI
- **Interval schedules** updated by AI via `intervals` field in response JSON
- Configuration changes applied by updating `state.json`

To change behavior, edit `config.py` for constants, or update system prompts in `memory/prompts/`.

## Monitoring

```bash
# Tail logs (shows commands with arrows and success/failure)
tail -f logs/bootstrap.log

# Check state (includes pending_tasks, task_history)
cat state.json

# View recent proposals
ls -lt memory/proposals/

# View pending tasks
jq '.pending_tasks' state.json

# View task history
jq '.task_history[-5:]' state.json
```

**Log format:**
```
2026-02-04 23:41:39 - INFO - Action: browser - Navigate to moltyscan.com
2026-02-04 23:41:39 - INFO -   → Executing: agent-browser navigate https://moltyscan.com
2026-02-04 23:41:41 - INFO -   ✓ Output: Navigation successful
```

## Browser Control Options

The `agent-browser` tool supports both headless (default) and visible modes:

```bash
# Run headless (default - faster)
agent-browser navigate https://moltyscan.com

# Run with visible browser (for debugging complex interactions)
agent-browser set headless off
agent-browser navigate https://moltyscan.com

# Set viewport size (useful for responsive testing)
agent-browser set viewport 1920 1080
```

Agents will use headless mode by default for speed, but can switch to visible mode when debugging interactions or capturing screenshots.

## Stopping

```bash
# Systemd
sudo systemctl stop agent-bootstrap

# Screen
screen -r agent
# Ctrl+C

# Docker
docker stop agent-bootstrap

# Direct process
pkill -f bootstrap.py
```

## Customization

Edit `memory/prompts/system.md` to change agent behavior. The agent can also evolve this file.
