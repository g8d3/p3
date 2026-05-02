# TODO / Roadmap

## Completed Tasks

### Code Reorganization
**Status**: ✅ Completed

Reorganized code into three files with clear separation of concerns:
- `config.py` - Declarative configuration, constants, and paths
- `agent.py` - Core agent logic (AI, state, execution)
- `ui.py` - TUI interface (monitoring, control, chat)
- `main.py` - Entry point (launches UI)

**Benefits:**
- Clear separation of concerns
- Easier to test components independently
- Declarative configuration in one place
- Config can be edited without touching logic

**Files removed:**
- `bootstrap.py` → replaced by `agent.py`
- `tui.py` → replaced by `ui.py`
- `launch.py`, `run.py`, `run-all.sh` → no longer needed (main.py handles everything)

## New Tasks

### Ctrl+Q Quit All Processes
**Status**: ✅ Completed

Implemented Ctrl+Q to quit both UI and agent:
- Added key binding `ctrl+q` in ui.py
- Writes "quit" command to commands file
- Gives agent time to process
- Then exits UI gracefully
- Agent subprocess terminated on UI exit

### AI Responses Not Showing in Chat
**Status**: ✅ Completed

Fixed AI response display in Chat tab:
- Added debug info showing file watching status
- Improved file watching with mtime tracking
- Added notification when new AI response arrives
- Shows last update timestamp
- More robust error handling in watch loop

### Intervals Management UI
**Status**: ✅ Completed

Implemented Schedule tab for interval management:
- View current intervals in readable list format
- See which interval is currently active (marked with [→])
- Add new intervals via input field
- Remove intervals (by index)
- Save changes to state.json
- Reset to default intervals
- Visual status of cycle position

**Features:**
- Real-time state updates
- Add interval validation
- Save/Reset buttons
- Current interval highlight

## Known Issues

### Human Input "hi" Does Nothing
**Status**: ✅ Fixed - AI responsiveness improved

When user types non-special commands (like "hi"):
1. UI writes to `.commands.json`
2. agent.py reads it and writes to `memory/human_input.md`
3. AI incorporates this context in next cycle
4. AI's thoughts are saved to `memory/ai_responses.md`
5. UI should display AI responses in Chat tab

**Previous limitations:**
- AI only sees human input at start of cycle
- No immediate feedback/acknowledgment
- May need explicit instructions to respond

**Changes made:**
- Updated system prompt to explicitly tell AI to respond to human input
- Added instructions to acknowledge greetings, answer questions, fulfill requests
- Created AI responses file that UI watches for real-time display

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
