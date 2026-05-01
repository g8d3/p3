#!/bin/bash
# 08-opencode-review — Review content using OpenCode Go's own model
#
# Uses `opencode run` with a review prompt to get a second opinion
# from the same model (deepseek-v4-flash) that generates the content.
# This provides an independent review from the Gemini-based editor.
#
# Reviews all unreviewed posts and saves scores.

TASK_PROMPT=$(cat <<'PROMPT'
You are a content quality reviewer. Review the posts in /home/vuos/code/p3/s46/content/posts/ that do NOT have a .approved file.

For each unreviewed post:
1. Read the full content
2. Score it 1-5 on: clarity, hook, substance, formatting, length, originality
3. Check if an audio file exists in /home/vuos/code/p3/s46/content/audio/ for this post (same base name, any .mp3)
4. If audio exists, verify it's valid:
   - Run: file /home/vuos/code/p3/s46/content/audio/<filename>.mp3
   - It should say "Audio file" or "RIFF" or "MPEG", not "JSON text data"
5. Check the existing review at /home/vuos/code/p3/s46/content/reviews/ for comparison
6. Write your review as JSON to /home/vuos/code/p3/s46/content/reviews/<postname>.review.opencode.md with format:
   {
     "reviewer": "opencode-go/deepseek-v4-flash",
     "date": "<date>",
     "scores": { "clarity": N, "hook": N, "substance": N, "formatting": N, "length": N, "originality": N },
     "verdict": "approve|revise|reject",
     "audio_valid": true|false,
     "summary": "<1-2 sentences>"
   }

Only approve if total score >= 20 AND audio is valid (or explain why audio is missing).
PROMPT
)
