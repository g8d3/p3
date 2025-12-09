# AI Agent Guide for Beads

**beads** (command: `bd`) is a Git-backed issue tracker designed for humans and AI agents.
We dogfood our own tool. We use `bd` for **all** task tracking.

**CRITICAL**: Do NOT create markdown TODO lists. Use `bd` for everything.

## Quick Reference

- **Find work**: `bd ready --json` (unblocked high-priority issues)
- **Claim task**: `bd update <id> --status in_progress --json`
- **Create task**: `bd create "Title" -t bug|feature|task -p 0-4 --json`
- **Done**: `bd close <id> --reason "Fixed XYZ" --json`
- **Stuck?**: `bd update <id> --blocked-by <other-id> --json`
- **Sync**: `bd sync` (commit/push DB changes - do this often!)

## Core Workflow

1. **Start Session**:
   - Run `bd ready --json` to see what is unblocked.
   - Pick the highest priority item (lowest number, e.g. P0 > P1).
   - Run `bd update <id> --status in_progress --json`.

2. **During Work**:
   - If you find a new bug or task, create it immediately:
     `bd create "New bug found" --priority 1 --deps discovered-from:<current-task-id> --json`
   - If blocked by something, link it:
     `bd update <current-id> --blocked-by <blocking-id> --json`
   - If the task is too big, break it down:
     `bd create "Subtask 1" --parent <current-id> --json`

3. **End Session**:
   - Close the task if done: `bd close <id> --reason "Completed" --json`
   - Or leave it in_progress if continuing later.
   - **ALWAYS** run `bd sync` to save the state to Git.

## Prioritization

- `0`: **Critical** (Security, data loss, build broken). Drop everything.
- `1`: **High** (Core feature, major bug). Next up.
- `2`: **Medium** (Standard feature, minor bug). Default.
- `3`: **Low** (Nice to have, polish).
- `4`: **Backlog** (Someday).

## Advanced Features

### Dependencies

- `--blocked-by <id>`: Rigid blocking. Task cannot be started.
- `--deps <id>`: Soft dependency or relation.
- `--parent <id>`: Heirarchical grouping.
- `--follows <id>`: Sequence enforcement (creates blocking link).

### Discovery

- When you discover necessary work while doing a task, link it!
  `bd create "Cleanup XYZ" --deps discovered-from:<id>`
  This preserves the context of *why* the task exists.

## Managing AI & Context

### Zero-Config Setup

Beads requires NO configuration.
It stores data in `.beads/beads.db` (SQLite) and syncs to `.beads/issues.jsonl`.
- **Do not commit the .db file**.
- **Do commit the .jsonl file**.

### Minimal Context

When `bd` outputs JSON, it is optimized for context windows.
- No manual export/import needed!

### GitHub Copilot Integration

If using GitHub Copilot, also create `.github/copilot-instructions.md` for automatic instruction loading.
Run `bd onboard` to get the content, or see step 2 of the onboard instructions.

### MCP Server (Recommended)

If using Claude or MCP-compatible clients, install the beads MCP server:

```bash
pip install beads-mcp
```

Add to MCP config (e.g., `~/.config/claude/config.json`):
```json
{
  "beads": {
    "command": "beads-mcp",
    "args": []
  }
}
```

Then use `mcp__beads__*` functions instead of CLI commands.

### Managing AI-Generated Planning Documents

AI assistants often create planning and design documents during development:
- PLAN.md, IMPLEMENTATION.md, ARCHITECTURE.md
- DESIGN.md, CODEBASE_SUMMARY.md, INTEGRATION_PLAN.md
- TESTING_GUIDE.md, TECHNICAL_DESIGN.md, and similar files

**Best Practice: Use a dedicated directory for these ephemeral files**

**Recommended approach:**
- Create a `history/` directory in the project root
- Store ALL AI-generated planning/design docs in `history/`
- Keep the repository root clean and focused on permanent project files
- Only access `history/` when explicitly asked to review past planning

**Example .gitignore entry (optional):**
```
# AI planning documents (ephemeral)
history/
```

**Benefits:**
- ✅ Clean repository root
- ✅ Clear separation between ephemeral and permanent documentation
- ✅ Easy to exclude from version control if desired
- ✅ Preserves planning history for archeological research
- ✅ Reduces noise when browsing the project

### CLI Help

Run `bd <command> --help` to see all available flags for any command.
For example: `bd create --help` shows `--parent`, `--deps`, `--assignee`, etc.

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Store AI planning docs in `history/` directory
- ✅ Run `bd <cmd> --help` to discover available flags
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with planning documents

For more details, see README.md and QUICKSTART.md.
