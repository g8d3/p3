# j — Architecture

## Files

```
~/bin/j              → Entry point (bash, single script)
~/.j/
├── j.db             → SQLite context database
├── templates/       → project templates
└── log/             → agent activity log
```

## Commands

| Command | Description |
|---------|-------------|
| `j init <name>` | Create project with structure |
| `j go <name\|N>` | Switch project (tmux driver) |
| `j list` | List all projects |
| `j context` | Show/add context entries |
| `j log` | Show session log |
| `j help` | Show help |

## Per-project structure (created by `j init`)

```
s{N}/
├── .j/
│   ├── context.db   → local context DB
│   ├── tmp/         → project-local temp (NOT /tmp/)
│   └── log/         → session logs
├── HANDOFF.md       → active handoff
├── PENDIENTE.md     → pending items
├── README.md        → project-specific
└── ...
```

## context.db Schema (SQLite)

```sql
CREATE TABLE handoffs (
  id INTEGER PRIMARY KEY,
  from_session TEXT,
  to_session TEXT,
  summary TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE context_entries (
  id INTEGER PRIMARY KEY,
  session_id TEXT,
  project TEXT,
  topic TEXT,
  content TEXT,
  tags TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE projects (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE,
  path TEXT,
  last_session TEXT,
  last_active TEXT DEFAULT (datetime('now'))
);
```

## Switch mechanism

1. `j go <name>` writes signal to `.j/switch` file
2. Uses `tmux kill-window` (driver) instead of kill/ps
3. Works on macOS/Linux/WSL
4. Fallback: signal file + zsh hook (for non-tmux)

## Key design decisions

- NO /tmp/ usage — everything under `.j/` in project root
- Single bash script for `j` (portable)
- SQLite via `sqlite3` CLI (almost everywhere)
- Drivers: tmux primary, signal-file fallback
- AI-agnostic: no hardcoded `crush` binary name
