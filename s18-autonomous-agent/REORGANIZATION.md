# Reorganization Summary

## New File Structure

```
config.py (36 lines)  - Declarative configuration
agent.py (387 lines) - Core agent logic
ui.py (299 lines)     - TUI interface
main.py (58 lines)    - Entry point
```

## Removed Files

- `bootstrap.py` → replaced by `agent.py`
- `tui.py` → replaced by `ui.py`
- `launch.py` → no longer needed
- `run.py` → no longer needed
- `run-all.sh` → no longer needed

## How to Run

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run the system
./main.py
```

The UI automatically starts `agent.py` in the background.

## File Responsibilities

| File | Purpose | Key Functions |
|------|----------|---------------|
| config.py | Declarative | Paths, API settings, defaults, constants |
| agent.py | Business Logic | AI calls, state management, command execution, cycles |
| ui.py | Presentation | TUI, tabs, chat, logs, subprocess management |
| main.py | Entry | Launch UI, handle initialization |

## Benefits

1. **Separation of Concerns**: Each file has a clear, single responsibility
2. **Declarative Config**: All configuration in one place, easy to modify
3. **Independent Testing**: Can test agent.py or ui.py separately
4. **Easier Maintenance**: Logic separate from presentation
5. **Better Organization**: Follows common software architecture patterns
