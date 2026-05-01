#!/bin/bash
# 01-project-spotlight — Pick a random subproject, write a spotlight post + TTS
#
# This task:
# 1. Reads the project index
# 2. Picks a random project from the high-priority list
# 3. Generates a "project spotlight" post
# 4. Creates a TTS narration
# 5. Saves both to content/

TASK_PROMPT=$(cat <<'PROMPT'
You are an AI content creator working in /home/vuos/code/p3/s46.

Your task is to create a "Project Spotlight" post about one of the projects found in the workspace.

1. First, read the project index at /home/vuos/code/p3/s46/knowledge-base/PROJECT-INDEX.md and identify a project that seems interesting. Prefer projects from p3 that have "Content angle: ⭐ High" markers.

2. Navigate to that project's directory. Read its README.md if it exists, and list its structure (key files, subdirectories).

3. Write a compelling thread-style post (300-500 words) that:
   - Introduces the project and what it does
   - Explains the tech stack
   - Highlights what's interesting or unique about it
   - Includes a lesson learned or insight gained
   - Save this to /home/vuos/code/p3/s46/content/posts/project-spotlight.txt

4. Generate a TTS narration of the post using:
   tts-speak "$(cat /home/vuos/code/p3/s46/content/posts/project-spotlight.txt)" \
     --voice af_nicole \
     --output /home/vuos/code/p3/s46/content/audio/project-spotlight.mp3

5. If TTS fails, note it in the post file and continue.

Focus on quality. This will be published.
PROMPT
)
