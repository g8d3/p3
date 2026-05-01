#!/bin/bash
# 05-overseer-report — Run the overseer and generate a status report
#
# This task runs the overseer.sh script to check resources,
# detect content overlap, clean up dead agents, and write
# a status report. Unlike other tasks, this one doesn't
# create content — it monitors the system.

TASK_PROMPT=$(cat <<'PROMPT'
You are a system monitor. Run the overseer to check the content generation system.

1. Execute: /home/vuos/code/p3/s46/scheduler/overseer.sh --report

2. Read the generated report at /home/vuos/code/p3/s46/content/overseer-report.md

3. Write a brief summary (100 words) of the system status. Focus on:
   - How many pieces of content have been generated
   - Any resource warnings (CPU, memory, disk)
   - Any content overlap detected
   - Overall health status

4. Save the summary to /home/vuos/code/p3/s46/content/posts/system-status.txt

5. If there are warnings, suggest what to do about them.
PROMPT
)
