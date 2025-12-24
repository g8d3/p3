#!/bin/bash

echo "Starting Chrome with CDP on port 9222..."

# Kill any existing Chrome instances on port 9222
pkill -f "chrome.*9222" || true

# Start Chrome with CDP enabled
/usr/bin/google-chrome \
  --headless \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --disable-web-security \
  --disable-features=VizDisplayCompositor \
  --user-data-dir=/tmp/chrome-test-profile \
  --disable-extensions \
  --disable-plugins \
  --disable-images \
  --disable-javascript \
  --disable-plugins-discovery \
  --disable-print-preview \
  --disable-component-extensions-with-background-pages \
  --no-first-run \
  --disable-default-apps \
  --disable-sync \
  --disable-translate \
  --hide-scrollbars \
  --metrics-recording-only \
  --mute-audio \
  --no-crash-upload \
  --disable-background-timer-throttling \
  --disable-renderer-backgrounding \
  --disable-backgrounding-occluded-windows \
  --disable-features=TranslateUI \
  --disable-ipc-flooding-protection \
  --disable-background-networking \
  --disable-component-update \
  --disable-hang-monitor \
  --disable-prompt-on-repost \
  --force-fieldtrials=*BackgroundNetworking/Disabled/ \
  --disable-back-forward-cache \
  --disable-hang-monitor \
  --disable-ipc-flooding-protection \
  --disable-popup-blocking \
  --disable-session-crashed-bubble \
  --disable-infobars &

echo "Chrome started with CDP on port 9222"
echo "Waiting for Chrome to be ready..."

# Wait for Chrome to be ready
sleep 3

# Test CDP connection
curl -s http://localhost:9222/json/version > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ Chrome CDP is ready on port 9222"
else
  echo "❌ Chrome CDP failed to start"
  exit 1
fi