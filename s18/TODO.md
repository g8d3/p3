# TODO / Roadmap

## Completed Tasks

### Python Launchers for System Startup
**Status**: ✅ Completed

Created Python launchers as alternative to tmux:
- `launch.py` - Concise, automatically runs both bootstrap.py and tui.py in separate terminal windows
- `run.py` - Interactive menu to choose: both, bootstrap only, or TUI only
- Auto-detects common terminals (gnome-terminal, konsole, alacritty, kitty, etc.)
- Falls back to manual instructions if no terminal found

**Files created**:
- `/run.py` - Interactive launcher with menu
- `/launch.py` - Automatic launcher for quick startup

## Skipped Items

### High Priority

#### Fix TUI via Interactive Testing
**Status**: Skipped (hard to implement without interactive terminal)

The TUI needs interactive testing and fixing through actual usage. This requires:
- Running tui.py and exploring all tabs
- Finding and fixing UI issues
- Testing edge cases (empty states, large files, etc.)
- Improving error handling and user feedback

**Implementation note**: Would need a way to run TUI interactively and iterate based on feedback.

### Medium Priority

#### Terminal File Explorer Integration
**Status**: Skipped (requires research and integration)

Current file browser uses a simple Tree widget. Better alternatives exist:
- **lf** - Fast terminal file manager written in Go
- **ranger** - Console file manager with vim keybindings
- **yazi** - Blazing fast terminal file manager written in Rust
- **nnn** - n³ - The missing terminal file manager for X

**Implementation note**: Would need to:
1. Research and choose best option
2. Check if it has a library/IPC interface
3. Integrate with TUI (possibly as subprocess or embedded)
4. Handle synchronization between TUI and file explorer

## Known Issues

### TUI Commands Not Working When No Agent Running
**Status**: ✅ Fixed - Documentation improved

The TUI is a monitoring/control interface only. It requires bootstrap.py to be running for commands to take effect.

**Solution**: Run both processes:
```bash
# Option 1: Python launchers (recommended)
./launch.py           # Automatic - opens both
# or
./run.py              # Interactive menu

# Option 2: Manual (two terminals)
# Terminal 1: Run the agent system
./bootstrap.py

# Terminal 2: Run the TUI
./tui.py
```

**Changes made**:
- Created Python launchers (launch.py, run.py)
- Updated README with clear instructions

### Human Input "hi" Does Nothing
**Status**: ✅ Fixed - AI responsiveness improved

When user types non-special commands (like "hi"):
1. TUI writes to `.commands.json`
2. bootstrap.py reads it and writes to `memory/human_input.md`
3. AI incorporates this context in next cycle

**Previous limitations**:
- AI only sees human input at start of cycle
- No immediate feedback/acknowledgment
- May need explicit instructions to respond

**Changes made**:
- Updated system prompt to explicitly tell AI to respond to human input
- Added instructions to acknowledge greetings, answer questions, fulfill requests

## Future Improvements

### Agent Collaboration
- Multi-agent coordination system
- Agent-to-agent communication
- Shared memory and knowledge base

### Enhanced Browser Control
- Better element selection strategies
- Retry logic for transient failures
- Session management across cycles

### State Management
- Database instead of JSON for better performance
- State versioning and rollback
- Automated backups

### Logging
- Structured logging with levels
- Log aggregation and search
- Performance metrics tracking

### TUI Enhancements
- Real-time graphs and charts
- Agent performance visualization
- Earnings dashboard
- Interactive file editing
- Task queue management
