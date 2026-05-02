# AI Agent Testing Guide for Terminal AI Chat App

This document explains how AI agents can interact with and test the Terminal AI Chat App programmatically.

## Running the App in API Mode

```bash
# Start the app with API server (TUI will display, but you can control it via API)
python main.py --api
```

This starts:
1. The interactive terminal UI (visible to human users)
2. An HTTP API server on port 8080

## API Endpoints for Testing

### Data Layer (CRUD Operations)
```bash
# List providers
curl http://localhost:8080/providers

# Create a provider
curl -X POST http://localhost:8080/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "provider_type": "openai"}'

# List models
curl http://localhost:8080/models

# List agents
curl http://localhost:8080/agents

# List sessions
curl http://localhost:8080/sessions
```

### TUI Control Layer (For Interactive Testing)

These endpoints let AI agents send keystrokes to the running TUI and read the screen:

```bash
# Get current screen text
curl http://localhost:8080/screen

# Get TUI state
curl http://localhost:8080/state

# Send a single keystroke
curl -X POST http://localhost:8080/keystroke \
  -H "Content-Type: application/json" \
  -d '{"key": "p"}'

# Send multiple keystrokes
curl -X POST http://localhost:8080/keystrokes \
  -H "Content-Type: application/json" \
  -d '{"keys": ["p", "enter", "escape"], "delay": 0.1}'
```

## Supported Keystrokes

The following keystrokes are supported:
- `enter`, `escape`, `esc`, `tab`
- `up`, `down`, `left`, `right`
- `f1` through `f12`
- Single characters (e.g., `p`, `m`, `a`, `/`, `?`)
- `backspace`, `delete`, `home`, `end`

## Example: AI Agent UX Testing Workflow

```python
import requests
import time

BASE = "http://localhost:8080"

def get_screen():
    """Get current TUI screen."""
    return requests.get(f"{BASE}/screen").json()["screen"]

def send_key(key):
    """Send a keystroke to TUI."""
    return requests.post(f"{BASE}/keystroke", json={"key": key}).json()

# Start at main screen
screen = get_screen()
print("Initial screen:", screen[:200])

# Try to find help
print("\nTrying '?' for help...")
send_key("?")
screen = get_screen()
print(screen)

# Try to open providers
print("\nPressing 'p' for providers...")
send_key("p")
screen = get_screen()
print(screen)

# Check what happened
state = requests.get(f"{BASE}/state").json()
print("\nTUI State:", state)
```

## UX Testing Checklist for AI Agents

An AI agent should test:

1. **Keyboard shortcuts discoverability**
   - Press `?` - Is help displayed?
   - Press `/` - Does it go to chat?
   - Press `p`, `m`, `a`, `s`, `t`, `h` - Do menus open?
   - Are there visible shortcuts shown on screen?

2. **Error handling**
   - What happens with invalid keys?
   - What happens when help command fails?
   - Are error messages clear?

3. **Menu navigation**
   - Can you navigate menus with arrow keys?
   - Does `enter` select items?
   - Does `escape` go back?

4. **Visual feedback**
   - Is there a status bar showing current mode?
   - Are shortcuts visible?
   - Is it clear what mode you're in?

## Automated UX Exploration

Use the `--explore` flag to run automated UX exploration:

```bash
python test_api.py --explore
```

This will:
1. Capture initial screen
2. Try common keystrokes (`?`, `/`, `p`, `m`, `a`, etc.)
3. Capture screen after each keystroke
4. Report potential UX issues

## Example Issues AI Agents Can Find

From user feedback:
- `?` (help) command fails or isn't discoverable
- `//help` does something unexpected
- No on-screen hints about available shortcuts
- User has to "guess" keys like `p` for providers
- No visual feedback when switching modes

## Debugging Tips

If TUI control doesn't work:
1. Check the API server is running: `curl http://localhost:8080/health`
2. Check TUI state: `curl http://localhost:8080/state`
3. Verify keystrokes are accepted: `curl -X POST http://localhost:8080/keystroke -d '{"key":"p"}'`

## Running Tests

```bash
# Basic API tests
python test_api.py --test

# UX exploration
python test_api.py --explore

# Get screen snapshot
python test_api.py --tui-screen

# Send keystrokes
python test_api.py --tui-key --key p
python test_api.py --tui-keys --keys "p,enter,escape"
```
