# Task for Agent A2: Build .j infrastructure and context.db

Build the `.j/` infrastructure and SQLite helper scripts.

Read the architecture: `/home/vuos/code/p3/s81/ARCHITECTURE.md`

## Requirements

### 1. SQLite schema and helpers

Create `/home/vuos/code/p3/s81/bin/j-db` (bash) with functions:

- `j-db init <path>` — Create `.j/context.db` with tables:
  - `handoffs` (id, from_session, to_session, summary, created_at)
  - `context_entries` (id, session_id, project, topic, content, tags, created_at)
  - `projects` (id, name, path, last_session, last_active)

- `j-db add-context <db> <topic> <content> [tags]` — Add context entry
- `j-db get-context <db> [topic]` — Get context entries (all or by topic)
- `j-db add-handoff <db> <from> <to> <summary>` — Record handoff
- `j-db recent-projects <db>` — List recent projects

### 2. Template files

Create `/home/vuos/code/p3/s81/templates/`:
- `HANDOFF.md` — template with sections: Context, Lo que se construyó, Estado actual, Temas pendientes
- `PENDIENTE.md` — template with "## Preguntas para resolver" placeholder
- `README.md` — simple project readme template

### 3. .j directory creation helper

Create `j-init-project <path> <name>` that:
- Creates `.j/`, `.j/tmp/`, `.j/log/`
- Runs `j-db init`
- Copies templates
- Creates `.jignore` (similar to .gitignore but for j tools)

### Important constraints
- `sqlite3` CLI only (no Python, no Node)
- All paths relative, no /tmp/ 
- Template files clear and minimal
