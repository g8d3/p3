# Autonomous Agent System

Bootstrap script for autonomous economic agents that explore, create value, and earn money.

## Quick Start

```bash
# Install dependencies
pip3 install requests

# Run once to test (executes immediately on first run)
./bootstrap.py

# Run continuously (uninterrupted)
./bootstrap.py &
```

**First run behavior:** The system executes immediately without waiting, then uses intervals for subsequent cycles. Default intervals: `[1, 3, 5]` minutes (rotating). The AI can dynamically adjust these intervals.

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
│   └── reasoning/            # Decision reasoning
└── creations/                # Generated content
```

**state.json fields:**
- `cycle`: Current cycle number
- `intervals`: Array of minute values e.g., `[1, 3, 5]`
- `interval_idx`: Current position in intervals array
- `earnings`: Total earnings tracked
- `logging_policy`: Log rotation settings
- `first_run`: Auto-set to false after first execution

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
# Tail logs
tail -f logs/bootstrap.log

# Check state
cat state.json

# View recent proposals
ls -lt memory/proposals/

# Systemd status
sudo systemctl status agent-bootstrap
```

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
