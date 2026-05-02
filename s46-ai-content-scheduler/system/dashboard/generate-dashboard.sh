#!/bin/bash
# ============================================================
# generate-dashboard.sh — Build dashboard data and serve it
#
# Generates current-state.json from live data and optionally
# starts a simple HTTP server for the dashboard.
#
# Usage:
#   ./generate-dashboard.sh          # Update JSON only
#   ./generate-dashboard.sh --serve  # Update + start HTTP server
#   ./generate-dashboard.sh --open   # Update + open in browser
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Update state JSON (reuses event-monitor's check)
"$PROJECT_DIR/system/event-monitor.sh" --status > /dev/null 2>&1

# Get content file sizes
TOTAL_SIZE=$(du -sh "$PROJECT_DIR/content" 2>/dev/null | awk '{print $1}')
APPROVED=$(find "$PROJECT_DIR/content/posts" -name '*.txt.approved' 2>/dev/null | wc -l)
POSTS=$(find "$PROJECT_DIR/content/posts" -name '*.txt' 2>/dev/null | wc -l)
AUDIO=$(find "$PROJECT_DIR/content/audio" -name '*.mp3' -o -name '*.wav' 2>/dev/null | wc -l)

# Build extended state
STATE_FILE="$SCRIPT_DIR/current-state.json"
if [ -f "$STATE_FILE" ]; then
  python3 -c "
import json
with open('$STATE_FILE') as f:
    d = json.load(f)
d['content']['approved'] = $APPROVED
d['content']['total_size'] = '$TOTAL_SIZE'
# Add posts list
import os, glob
posts = []
for f in sorted(glob.glob('$PROJECT_DIR/content/posts/*.txt'), reverse=True)[:10]:
    name = os.path.basename(f)
    size = os.path.getsize(f)
    words = len(open(f).read().split())
    approved = os.path.exists(f + '.approved')
    mtime = os.path.getmtime(f)
    posts.append({'name': name, 'size': size, 'words': words, 'approved': approved, 'mtime': mtime})
d['posts'] = posts
with open('$STATE_FILE', 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null
fi

case "${1:-}" in
  --serve)
    echo "Starting dashboard at http://localhost:9090"
    echo "Open in browser: http://localhost:9090/system/dashboard/"
    cd "$PROJECT_DIR"
    python3 -m http.server 9090 --bind 127.0.0.1
    ;;
  --open)
    xdg-open "$SCRIPT_DIR/index.html" 2>/dev/null || \
      sensible-browser "$SCRIPT_DIR/index.html" 2>/dev/null || \
      echo "Open manually: $SCRIPT_DIR/index.html"
    ;;
  *)
    echo "Dashboard data updated. Use --serve to start the server or --open to open the file."
    ;;
esac
