# Autonomy: Running OpenCode Go Non-Interactively

> Research and implementation guide for running opencode on a schedule
> without human interaction.

---

## The Core Discovery: `opencode run`

The key command is:

```bash
opencode run <message> [options]
```

This runs opencode with a one-shot message and exits when done. It:
- Does NOT open the TUI
- Does NOT require interactive input
- Returns exit code on completion (0 = success)
- Can output JSON events with `--format json`
- Can continue from a previous session with `-c` / `--session`
- Supports auto-approve with `--dangerously-skip-permissions`
- Can attach to an already-running server with `--attach`

### ⚠️ Sandbox Recommendation

Running `opencode run` with `--dangerously-skip-permissions` gives the AI
full filesystem access. For production scheduling:

1. **Run inside a container** (Docker/Podman) or VM with limited filesystem
   access — bind-mount only the directories the tasks need.

2. **Use a dedicated system user** with restricted permissions:
   ```bash
   sudo useradd --no-create-home --shell /usr/sbin/nologin opencode-agent
   # Grant access only to specific directories
   ```

3. **Set resource limits** via systemd or ulimit to prevent runaway processes:
   ```
   CPUQuota=50%
   MemoryMax=1G
   ```

4. **Isolate the browser session** — the CDP browser has logged-in accounts.
   Consider a separate Chrome profile for autonomous tasks, or run the
   automated tasks in a container with its own browser instance.

5. **Audit logs** — the scheduler already logs everything. Monitor the logs
   for unexpected file access patterns.

A Docker-based setup is the recommended approach for sustained operation.

### Key Flags for Automation

| Flag | Purpose |
|------|---------|
| `--model provider/model` | Specify model (e.g., `opencode-go/deepseek-v4-flash`) |
| `--format json` | Get machine-parseable output |
| `--dangerously-skip-permissions` | Auto-approve all file ops (required for non-interactive) |
| `--continue / -c` | Continue last session |
| `--session <id>` | Continue specific session |
| `--dir <path>` | Working directory |
| `--file <path>` | Attach file(s) to the message |
| `--agent <name>` | Use a specific agent profile |
| `--attach <url>` | Connect to running headless server |
| `--variant high` | Set reasoning effort |

### Alternative: `opencode serve` + `opencode attach`

A two-process approach:
1. **Server**: `opencode serve --port 4096` (stays running)
2. **Client**: `opencode run "do task" --attach http://localhost:4096`

This is ideal for cron because:
- Server starts once, stays warm
- Each `run` call is fast (no cold start)
- Multiple tasks can queue

---

## Permission Model for Automation

OpenCode agents have permission rules. For non-interactive use:

1. **Create a dedicated agent** with permissive rules:
```bash
opencode agent create autonomous --permission "*" --action "allow"
```

2. **Use `--dangerously-skip-permissions`** — this auto-approves everything.
   Only safe if you trust the prompts being sent.

3. **Current agent permissions** (from `opencode agent list`):
   - `build`: question=deny, plan=deny, read *.env=ask — partially autonomous
   - `plan`: question=allow, edit=deny (except plans) — can plan but not execute
   - `summary`: question=deny — fully autonomous but limited scope

   The `build` agent is closest to what we need, but `question=deny` means
   it can't ask clarifying questions — it will fail on ambiguous requests.

---

## Cron Scheduling Strategy

### Basic Cron Job

```bash
# Every 4 hours, run a content task
0 */4 * * * /home/vuos/code/p3/s46/scheduler/run-task.sh >> /home/vuos/code/p3/s46/scheduler/log.txt 2>&1
```

### Smart Scheduling (Recommended)

Instead of fixed intervals, use a task queue:

1. **Task queue**: `scheduler/tasks/` directory with numbered task scripts
2. **Runner**: Picks a random task or round-robins
3. **Logging**: Each run logs to `scheduler/logs/` with timestamp
4. **Credit awareness**: Check `opencode stats` to see remaining credits

### The Run Script Approach

```bash
#!/bin/bash
# scheduler/run-task.sh — main entry point for cron

TASKS_DIR="/home/vuos/code/p3/s46/scheduler/tasks"
LOG_DIR="/home/vuos/code/p3/s46/scheduler/logs"
DATE=$(date +%Y-%m-%d-%H%M)

# Pick next task (round-robin via a counter file)
COUNTER_FILE="$TASKS_DIR/.counter"
if [ ! -f "$COUNTER_FILE" ]; then
  echo 0 > "$COUNTER_FILE"
fi
COUNTER=$(cat "$COUNTER_FILE")
TASKS=($(ls "$TASKS_DIR"/*.sh 2>/dev/null | sort))
TOTAL=${#TASKS[@]}

if [ $TOTAL -eq 0 ]; then
  echo "No tasks to run"
  exit 0
fi

NEXT=$((COUNTER % TOTAL))
echo $((NEXT + 1)) > "$COUNTER_FILE"
TASK="${TASKS[$NEXT]}"

echo "[$DATE] Running task: $(basename $TASK)" | tee -a "$LOG_DIR/run.log"
bash "$TASK" 2>&1 | tee -a "$LOG_DIR/task-$DATE.log"
echo "[$DATE] Task exit code: $?" | tee -a "$LOG_DIR/run.log"
```

---

## OpenCode Go as an Agent — The Content Piece

This system itself is content. Here's the story arc:

1. **Problem**: "I want my AI to work autonomously, not just when I'm watching"
2. **Discovery**: `opencode run` exists but needs special flags for non-interactive use
3. **Solution**: A cron wrapper + dedicated agent + task queue
4. **Result**: The AI wakes up, checks a task queue, executes work, logs results
5. **Meta**: "I taught myself to run on a schedule — here's how" is publishable

### Key Technical Details to Document

- The `--dangerously-skip-permissions` flag and why it's needed
- The `--format json` output structure for programmatic parsing
- How `opencode serve` keeps a warm server for fast task execution
- Permission rule conflicts (e.g., `read *.env=ask` blocks automation)
- The agent permission system and how to create autonomous agents
