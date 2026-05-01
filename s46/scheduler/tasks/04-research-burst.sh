#!/bin/bash
# 04-research-burst — Research-backed post about AI tool comparisons
#
# Generates a comparison post about the best cost-effective AI tools
# across categories (TTS, image, video, GPU, hosting), highlighting
# China-based alternatives that offer better value.

TASK_PROMPT=$(cat <<'PROMPT'
You are an AI content creator working in /home/vuos/code/p3/s46.

Create a thread-style post about the best cost-effective AI tools for content creation.

1. Read the research at /home/vuos/code/p3/s46/knowledge-base/TOOLS.md (the "What We're Missing" section)
2. Also read /home/vuos/code/p3/s44/TEXT_TO_IMAGE_MODELS.md for the pareto frontier analysis

3. Write a 300-500 word comparison post titled "Best Value AI Tools — April 2026" that covers:
   - TTS: Kokoro (free via Chutes) vs Inworld vs Alibaba Qwen3-TTS (1M chars free)
   - Image: Luma Photon at $0.016/image is the pareto frontier (from s44 research)
   - Video: Kling at $6.99/mo or s44's $0 pipeline
   - GPU/SiliconFlow: cheapest inference globally at $0.0014/image
   - Hosting: Hetzner at €3.79/mo for VPS
   - The surprising finding: China-based tools (SiliconFlow, Kling, Alibaba) offer best cost/benefit in many categories
   - The meta story: your own research is itself content

4. Save to: /home/vuos/code/p3/s46/content/posts/research-comparison.txt

5. Generate TTS narration:
   tts-speak "$(cat /home/vuos/code/p3/s46/content/posts/research-comparison.txt)" \
     --voice am_michael \
     --output /home/vuos/code/p3/s46/content/audio/research-comparison.mp3
PROMPT
)
