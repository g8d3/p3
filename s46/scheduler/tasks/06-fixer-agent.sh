#!/bin/bash
# 06-fixer-agent — Run the continuous improvement agent
#
# Scans logs for known error patterns, applies automatic fixes.
# Runs the fixer-agent.sh script which has its own error detection.

TASK_PROMPT=$(cat <<'PROMPT'
Run the fixer agent to detect and fix tool issues:

1. Execute: /home/vuos/code/p3/s46/system/fixer-agent.sh
2. Read the fixer log at /home/vuos/code/p3/s46/scheduler/logs/fixer.log
3. If fixes were applied, test the fixed tool:
   - /home/vuos/code/p3/s46/system/tts-safe.sh "Testing after fix" --output /home/vuos/code/p3/s46/tmp/fixer-test.mp3
4. Write a brief summary of what was detected and fixed (or "nothing found") to:
   /home/vuos/code/p3/s46/content/posts/fixer-report.txt
5. Clean up: rm -f /home/vuos/code/p3/s46/tmp/fixer-test.mp3
PROMPT
)
