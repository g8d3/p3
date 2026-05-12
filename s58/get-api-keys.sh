#!/usr/bin/env bash
# ── API Key Retrieval Tool ──────────────────────────────────────────────────
# Gets Pexels and Pixabay API keys using your real Chrome browser.
# 
# Usage:
#   ./get-api-keys.sh
#
# What it does:
#   1. Starts Chrome with remote debugging (if not already running)
#   2. Opens Pexels API page → helps you sign up and get your key
#   3. Opens Pixabay API page → helps you sign up and get your key
#   4. Saves both keys to .env
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        API Key Retrieval Tool                    ║"
echo "  ║                                                  ║"
echo "  ║  This script helps you get free API keys for:    ║"
echo "  ║    • Pexels  (stock video backgrounds)           ║"
echo "  ║    • Pixabay (stock video + background music)    ║"
echo "  ║                                                  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Ensure Chrome is running with CDP ─────────────────────────────────
if ! curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
    echo "  Starting Chrome with remote debugging..."
    # Kill any existing Chrome
    pkill chrome 2>/dev/null || true
    sleep 1
    
    # Use a fresh profile for API key setup
    PROFILE_DIR="/tmp/chrome-api-keys"
    mkdir -p "$PROFILE_DIR"
    
    # Launch Chrome
    google-chrome --user-data-dir="$PROFILE_DIR" \
                  --remote-debugging-port=9222 \
                  --disable-features=DownloadRestrictions \
                  --no-first-run \
                  --no-default-browser-check \
                  --disable-sync \
                  > /dev/null 2>&1 &
    
    echo "  ⏳ Waiting for Chrome to start..."
    for i in $(seq 1 20); do
        if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
            echo "  ✓ Chrome ready on port 9222"
            break
        fi
        sleep 1
    done
else
    echo "  ✓ Chrome already running on port 9222"
fi

# ── 2. Run the Node.js retrieval script ───────────────────────────────────
echo ""
if [ ! -f "node_modules/puppeteer-core/package.json" ]; then
    echo "  Installing puppeteer-core..."
    npm install --silent 2>&1 | tail -1
fi

node get-api-keys.js

# ── 3. Load keys into environment ──────────────────────────────────────────
if [ -f ".env" ]; then
    echo ""
    echo "  Keys saved to .env"
    echo "  Run: source .env"
    echo "  Or:  set -a; source .env; set +a"
fi
