# Autonomous Agent System

Bootstrap script for autonomous economic agents that explore, create value, and earn money.

## Quick Start

```bash
# Install dependencies
pip3 install requests

# Run once to test
./bootstrap.py

# Run continuously (uninterrupted)
./bootstrap.py &
```

## Running Uninterruptedly

### Option 1: Systemd (Recommended)

```bash
# Create service file
sudo tee /etc/systemd/system/agent-bootstrap.service > /dev/null <<EOF
[Unit]
Description=Autonomous Agent Bootstrap
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment="GLM_API_KEY=your_key_here"
ExecStart=/usr/bin/python3 $PWD/bootstrap.py
Restart=always
RestartSec=60
StandardOutput=append:$PWD/logs/systemd.log
StandardError=append:$PWD/logs/systemd_error.log

[Install]
WantedBy=multi-user.target
EOF

# Start and enable
sudo systemctl daemon-reload
sudo systemctl enable agent-bootstrap
sudo systemctl start agent-bootstrap

# Check status
sudo systemctl status agent-bootstrap

# View logs
sudo journalctl -u agent-bootstrap -f
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

Edit `.env` file and set your key:
```bash
GLM_API_KEY=your_key_here
```

## Directory Structure

```
.
├── bootstrap.py              # Main script
├── state.json                # System state
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

## Evolution

The system can evolve itself:
- Agents modify prompts in `memory/prompts/`
- New agents created in `agents/`
- Tools installed as needed
- Logging policies decided by AI

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
