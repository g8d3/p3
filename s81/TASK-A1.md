# Task for Agent A1: Build `j` core script

Build the main `~/bin/j` bash script at `/home/vuos/code/p3/s81/bin/j`.

## Requirements

Read the architecture: `/home/vuos/code/p3/s81/ARCHITECTURE.md`

### Commands to implement

1. `j init <name>` — Create project at `/home/vuos/code/p3/s<name>/` with:
   - `.j/context.db` (SQLite, create tables if not exist)
   - `.j/tmp/` (project-local temp dir)
   - `.j/log/` (session logs)
   - `HANDOFF.md` (template)
   - `PENDIENTE.md` (template)
   - `README.md` (template)
   - `source ~/.zshrc` message

2. `j go <name>` — Switch to project:
   - Write signal to `.j/switch` (target dir + session id)
   - Do `tmux kill-window` (primary driver)
   - Fallback: print "run: cd <path> && p3-resume"

3. `j list` — List all projects
   - Scan `/home/vuos/code/p3/` for s{N} directories
   - Show name, path, last modified

4. `j help` — Show help

### Important constraints
- Single bash script, no dependencies beyond `sqlite3`, `tmux`
- NO /tmp/ usage
- No hardcoded `crush` binary name
- Must work in tmux on Linux/macOS/WSL
- Output concise (<4 lines for success)

### Test
After creating, verify: `bash ~/bin/j help`
