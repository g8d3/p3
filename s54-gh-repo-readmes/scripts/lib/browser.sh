#!/usr/bin/env bash
# browser.sh — Chrome CDP helpers for agent-browser
# Source this file: source scripts/lib/browser.sh

BROWSER_PORT="${BROWSER_PORT:-9222}"
BROWSER_DISPLAY="${BROWSER_DISPLAY:-:99}"
BROWSER_RESOLUTION="${BROWSER_RESOLUTION:-1920x1080x24}"
BROWSER_PROFILE="${BROWSER_PROFILE:-$HOME/apps/test-dec-2025}"
BROWSER_PROFILE_DIR="${BROWSER_PROFILE_DIR:-Profile 1}"
BROWSER_LOG="${BROWSER_LOG:-/tmp/chrome_browser.log}"
XVFB_LOG="${XVFB_LOG:-/tmp/xvfb.log}"

browser_start() {
  echo "→ Starting Xvfb on display $BROWSER_DISPLAY ..."
  Xvfb "$BROWSER_DISPLAY" -screen 0 "$BROWSER_RESOLUTION" &>"$XVFB_LOG" &
  XVFB_PID=$!
  sleep 1

  export DISPLAY="$BROWSER_DISPLAY"

  echo "→ Starting Chrome (profile: $BROWSER_PROFILE) on port $BROWSER_PORT ..."
  google-chrome \
    --user-data-dir="$BROWSER_PROFILE" \
    --profile-directory="$BROWSER_PROFILE_DIR" \
    --remote-debugging-port="$BROWSER_PORT" \
    --disable-features=DownloadRestrictions \
    --new-window about:blank \
    &>"$BROWSER_LOG" &
  CHROME_PID=$!

  # Wait for CDP to be ready
  for i in $(seq 1 10); do
    if curl -s "http://localhost:$BROWSER_PORT/json/version" >/dev/null 2>&1; then
      echo "✓ Chrome ready (PID $CHROME_PID)"
      return 0
    fi
    sleep 1
  done

  echo "✗ Chrome failed to start (check $BROWSER_LOG)"
  return 1
}

browser_stop() {
  echo "→ Stopping Chrome ..."
  pkill -f "google-chrome.*remote-debugging-port=$BROWSER_PORT" 2>/dev/null || true
  sleep 1
  echo "→ Stopping Xvfb ..."
  pkill -f "Xvfb $BROWSER_DISPLAY" 2>/dev/null || true
  echo "✓ Browser stopped"
}

browser_connect() {
  agent-browser connect "$BROWSER_PORT"
}

browser_url() {
  echo "http://localhost:$BROWSER_PORT"
}

# If executed directly, show status
if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
  case "${1:-status}" in
    start)   browser_start ;;
    stop)    browser_stop ;;
    restart) browser_stop; sleep 1; browser_start ;;
    status)
      if curl -s "http://localhost:$BROWSER_PORT/json/version" >/dev/null 2>&1; then
        echo "✓ Browser running on port $BROWSER_PORT"
        curl -s "http://localhost:$BROWSER_PORT/json/version" | python3 -c "import json,sys; print('  Version:', json.load(sys.stdin)['Browser'])"
      else
        echo "✗ Browser not running on port $BROWSER_PORT"
      fi
      ;;
    *)
      echo "Usage: $0 {start|stop|restart|status}"
      exit 1
      ;;
  esac
fi
