# Bitwarden Popout Automation

**Single, tested script** to automatically open Bitwarden extension and pop it out to a new window.

## Usage

### Requirements
- Browser must be running with remote debugging enabled on port 9222
- Bitwarden extension must be installed
- Playwright Node.js package

### Start Browser with CDP
```bash
# For Chrome/Brave/Edge:
chrome --remote-debugging-port=9222

# Or Brave:
brave --remote-debugging-port=9222
```

### Run the Script
```bash
# Install dependencies if needed
npm install playwright

# Run the popout script
node bitwarden-popout.js
```

## What the script does:

1. **Connects to existing browser** on CDP port 9222
2. **Opens Bitwarden extension** in a new tab
3. **Finds and clicks** the "Pop out to new window" button
4. **Confirms popout window opened** with `uilocation=popout` in URL

## Testing Status
✅ **Tested and working** - Successfully finds and clicks the popout button using multiple detection methods

## Features

- **Multiple detection methods**: Text, aria-label, title, and JavaScript fallbacks
- **Robust error handling**: Continues through different approaches if one fails
- **Clean disconnection**: Disconnects from CDP but keeps browser open
- **Informative output**: Shows progress and success/failure clearly

## Extension Details
- **Extension ID**: `nngceckbapebfimnlniiiahkandclblb` (Bitwarden)
- **Popout indicator**: URL contains `uilocation=popout`

## Troubleshooting

1. **"Browser connection ended"** - Normal, script closes connection after success
2. **"Make sure browser is running with CDP"** - Start browser with `--remote-debugging-port=9222`
3. **"Popout button not found"** - Check if Bitwarden extension is installed and has correct ID

## Example Output
```
🚀 Bitwarden Popout Script - Starting...
🔗 Connecting to browser on CDP port 9222...
✅ Connected to browser successfully
📍 Navigating to Bitwarden extension...
✅ Bitwarden extension loaded
🔍 Looking for pop out button...
✅ Found and clicked popout button!
✅ Script completed successfully!
🎯 Bitwarden should now be opened in a popped-out window
```
