#!/bin/bash
# 02-browser-bookmarks — Explore x.com bookmarks via CDP browser
#
# This task:
# 1. Opens the browser via CDP
# 2. Reads bookmarks from the browser
# 3. Picks one and researches the topic
# 4. Generates a post + TTS

TASK_PROMPT=$(cat <<'PROMPT'
You are an AI content creator with browser access via Chrome DevTools Protocol on port 9222.

Your task is to explore browser content and create from it.

1. First verify the CDP connection:
   curl -s http://localhost:9222/json/version

2. Use agent-browser with CDP to open a page:
   agent-browser --cdp 9222 open about:blank

3. Try to access bookmarks by using the CDP to navigate:
   agent-browser --cdp 9222 eval "window.location.href = 'chrome://bookmarks/'"
   agent-browser --cdp 9222 snapshot -i

4. If bookmarks aren't accessible, instead:
   - Navigate to x.com and explore your feed/bookmarks
   - Or read any file in /home/vuos/code/p3/s46/knowledge-base/ to find a content topic

5. Write a 200-300 word post about what you found or learned. Save it to:
   /home/vuos/code/p3/s46/content/posts/browser-discovery.txt

6. Generate TTS narration:
   tts-speak "$(cat /home/vuos/code/p3/s46/content/posts/browser-discovery.txt)" \
     --voice am_michael \
     --output /home/vuos/code/p3/s46/content/audio/browser-discovery.mp3
PROMPT
)
