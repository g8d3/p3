# Autonomous Agent System

Bootstrap script for autonomous economic agents that explore, create value, and earn money.

## Quick Start

```bash
# Install dependencies (using uv - recommended)
uv pip install -r requirements.txt

# Or using pip
python3 -m pip install -r requirements.txt

# Option 1: Launch both (recommended - opens 2 terminals)
./launch.py
# Or interactive:
./run.py

# Option 2: Run agent + TUI manually (two terminals)
# Terminal 1: Run the agent system
./bootstrap.py

# Terminal 2: Run the TUI to monitor and control
./tui.py

# Option 3: Run agent only
./bootstrap.py

# Option 4: Run continuously in background
./bootstrap.py &
```

**IMPORTANT**: The TUI is a monitoring/control interface. It requires `bootstrap.py` to be running for commands to work and logs to appear. The Python launchers automatically handle this.

**TUI Features:**
- Tab 1: Live logs with auto-scroll
- Tab 2: System state, pending tasks, recent actions
- Tab 3: File browser (memory/, creations/, agents/)
- Tab 4: Command input to trigger actions
- Type commands in Chat tab to influence agent behavior

**TUI Commands:**
- `run` / `now` - Trigger immediate agent cycle
- `skip <task_desc>` - Skip a pending task
- `quit` / `stop` - Shutdown system
- Any other text - Added as human input for agent context

**Note:**
- TUI requires a terminal supporting UTF-8 and at least 80x24 characters
- Screenshots saved by agent-browser need absolute paths (e.g., `/home/vuos/code/p3/s18/creations/screenshot.png`)
- `launch.py` finds your terminal automatically (gnome-terminal, konsole, alacritty, kitty, etc.)
- `run.py` offers interactive menu: run both, bootstrap only, or TUI only

**First run behavior:** The system executes immediately without waiting, then uses intervals for subsequent cycles. Default intervals: `[1, 3, 5]` minutes (rotating). The AI can dynamically adjust these intervals.

**Event-driven execution:** When commands fail, they're added to `pending_tasks` and the system immediately retries (no wait). Successful commands are tracked in `task_history`. The AI can skip pending tasks with `skip_pending` field.

## Running Uninterruptedly

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

### Option 2: Screen/Tmux

```bash
# With screen
screen -S agent
./bootstrap.py
# Ctrl+A, D to detach

# Reattach
screen -r agent

# With tmux
tmux new -s agent
./bootstrap.py
# Ctrl+B, D to detach

# Reattach
tmux attach -t agent
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
├── bootstrap.py              # Main script
├── tui.py                   # Terminal UI control panel
├── requirements.txt           # Python dependencies
├── .commands.json           # TUI commands (deleted after processing)
├── state.json                # System state (cycle, intervals, earnings, etc.)
├── logs/                     # Logs (AI decides rotation policy)
├── agents/                   # Agent configurations
├── memory/
│   ├── prompts/              # Dynamic prompts (loaded each cycle)
│   │   └── system.md         # Main system prompt
│   ├── context/              # Agent context
│   ├── knowledge/            # Learned information
│   ├── tools/                # Tool documentation
│   ├── proposals/            # Proposals for human review
│   ├── reasoning/            # Decision reasoning
│   └── human_input.md       # Human input from TUI
└── creations/                # Generated content
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
- Agents modify prompts in `memory/prompts/`
- New agents created in `agents/`
- Tools installed as needed
- Logging policies decided by AI
- **Interval schedules** updated by AI via `intervals` field in response JSON
- Configuration changes applied by updating `state.json`

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
