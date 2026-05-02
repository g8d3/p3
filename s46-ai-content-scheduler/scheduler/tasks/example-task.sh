#!/bin/bash
# Example: Explore and document a random subproject
#
# This task picks a random subproject from p3, reads its README,
# and generates a content summary + TTS narration.
# It serves as both a template and a working task.

# --- Configuration ---
# Set TASK_PROMPT — this is what gets sent to opencode run
# The prompt should be self-contained and specific.

TASK_PROMPT=$(cat <<'PROMPT'
I want you to explore the projects in /home/vuos/code/p3 and create content about what you find.

1. List all subdirectories of /home/vuos/code/p3 (these are s1 through s46)
2. Pick one at random
3. Read its README.md if it exists, and list its contents
4. Write a 200-word summary of what this project does — as if explaining it to another developer
5. Save the summary to /home/vuos/code/p3/s46/content/posts/project-spotlight.txt
6. Then generate a TTS narration of that summary using the tts-speak command:
   tts-speak "$(cat /home/vuos/code/p3/s46/content/posts/project-spotlight.txt)" --output /home/vuos/code/p3/s46/content/audio/project-spotlight.mp3

Use the af_nicole voice for the narration (expressive, good for storytelling).

If you don't have tts-speak available or it fails, just save the text file.
PROMPT
)
