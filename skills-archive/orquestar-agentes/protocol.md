# Universal Agent Protocol — for all agents (maker, checker, video-maker)

Every agent MUST follow this cycle before and after every action.

## READ → ACT → VERIFY

### 1. READ — check the actual state before assuming

Before doing anything, read the current state:
- `tmux capture-pane -t <target> -p -S -5` — what's the agent seeing?
- `ls /tmp/agent-bus/<name>/in/` — are there pending messages?
- `pgrep -f "crush"` — is the agent process alive?
- `cat /tmp/agent-bus/history/messages.log | tail -5` — what was the last interaction?
- `ls /tmp/agent-bus/agent-states.json` — check supervisor-tracked agent states
- Check for stale servers: `fuser <port>/tcp` before starting a new instance

**Never assume** an agent is stuck, dead, or needs something without reading first.

### 2. ACT — do the minimum necessary

Based on what you READ:
- If agent is alive and at `:::` → send a message, don't restart
- If agent is alive but thinking → wait, don't interrupt
- If agent is dead (no tmux window) → recreate it
- If agent is stuck in a loop (same command repeated) → hard reset
- If server fails with EADDRINUSE → kill old process first: `fuser -k <port>/tcp`
- When ffmpeg keeps dying → check process accumulation: `pgrep -c ffmpeg`, kill duplicates

**Do not cascade.** Never tell an agent to create another agent. Never create agents inside agents.

### 3. VERIFY — confirm the action worked

After acting, verify:
- `tmux capture-pane -t <target> -p -S -3` — did the agent receive the message?
- `grep -c "<expected>" /tmp/agent-bus/history/messages.log` — was it delivered?
- For server changes: `node --check <file>` before restarting
- For HTML changes: `agent-browser snapshot` to check rendered DOM, not just HTTP fetch
- For video: check agent-browser snapshot for "Unable to play media" string
- If verification fails → READ again, don't repeat the same action

## Golden rules

| Rule | Why |
|------|-----|
| READ before you ACT | Assumptions cause cascading failures |
| ACT the minimum | Big actions cause big problems |
| VERIFY after every ACT | Without verification, errors compound |
| Never cascade agent creation | An agent should never create another agent |
| If stuck for >2 cycles, escalate | Don't retry the same broken action |

## Recurring failure patterns (from real sessions)

### 1. Video streaming broken
**Symptoms**: data arrives but video doesn't render, "Unable to play media", 3s loops
**Known causes**:
- ffmpeg process accumulates from restart loop → kill old before starting new
- Init segment (ftyp+moov) truncated at arbitrary byte → capture only ftyp+moov, not moof+mdat
- Codec string mismatch → verify with `ffprobe`, read actual avcC box from file
- Missing endOfStream() after appendBuffer → MSE stays "open", browser waits forever
- `-t 3` segments create looping clips → use continuous fMP4 with `empty_moov+frag_keyframe`

### 2. FIFO blocking event loop
**Symptoms**: server hangs, all API calls time out
**Root cause**: `fs.openSync(fifo, 'r')` on a FIFO with no writer blocks the entire Node.js event loop
**Fix**: Use async `fs.open(fifo, 'r', callback)` — blocks in libuv thread pool, event loop stays free

### 3. Hot-reload killing server during development
**Symptoms**: server dies when editing files, ECONNREFUSED on next request
**Root cause**: `fs.watch` + `process.exit(0)` triggers when any .js file changes (including server.js itself)
**Fix**: Remove or disable hot-reload during active development, or use a debounce

### 4. UI state not refreshing on view switch
**Symptoms**: columns from previous view persist, wrong headers shown
**Root cause**: `setView()` calls `buildColumns()` but not `buildHeaders()` — old `<thead>` stays in DOM
**Fix**: Always reset `sortCol`, `sortDir`, `page` and call `buildHeaders()` before `render()`

### 5. Select dropdown glitching on poll
**Symptoms**: opening a `<select>` feels like a page reload, options disappear
**Root cause**: `refresh()` rewrites `sel.innerHTML` every 2s, nuking the open native dropdown
**Fix**: Compare old/new HTML before replacing, or use DOM diff/add/remove of individual <option> elements

### 6. Server running stale code
**Symptoms**: changes don't take effect, old behavior persists
**Root cause**: `EADDRINUSE` on restart — old server still bound to port, new one fails silently
**Fix**: Always `fuser -k <port>/tcp` before starting, verify new PID matches expectations
