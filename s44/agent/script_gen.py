"""
Script Generator
Uses the LLM (via API) to generate content scripts with personality.
For autonomous mode, generates scripts and recording instructions
that the pipeline can execute.
"""

import json
import os
import random
from pathlib import Path
from datetime import datetime

# Import personality engine
from agent.personality import get_persona_prompt, load_personality

# Topic database — things we can review
SOFTWARE_TOPICS = {
    "tools": [
        {"name": "OpenMontage", "url": "https://github.com/calesthio/OpenMontage",
         "type": "open source", "hook": "AI that makes videos for you while you nap"},
        {"name": "Testreel", "url": "https://github.com/greentfrapp/testreel",
         "type": "open source", "hook": "JSON instead of video editing software"},
        {"name": "Hacker News", "url": "https://news.ycombinator.com",
         "type": "website", "hook": "The internet's most pretentious book club"},
        {"name": "Cursor IDE", "url": "https://cursor.com",
         "type": "app", "hook": "VS Code walked so Cursor could run"},
        {"name": "UV (Python)", "url": "https://github.com/astral-sh/uv",
         "type": "tool", "hook": "pip but faster and not terrible"},
        {"name": "Ollama", "url": "https://ollama.ai",
         "type": "tool", "hook": "Run LLMs on your toaster"},
        {"name": "Perplexity AI", "url": "https://perplexity.ai",
         "type": "website", "hook": "Google with a superiority complex"},
        {"name": "Suno AI", "url": "https://suno.ai",
         "type": "website", "hook": "AI makes music so humans don't have to"},
        {"name": "Claude Code", "url": "https://docs.anthropic.com/en/docs/claude-code/overview",
         "type": "tool", "hook": "An AI that writes code so you can tweet"},
        {"name": "Notion", "url": "https://notion.so",
         "type": "app", "hook": "Second brain, first headache"},
    ],
    "ai_tools": [
        {"name": "ChatGPT Codex", "url": "https://chatgpt.com",
         "type": "ai agent", "hook": "AI agents that do your job"},
        {"name": "OpenCode", "url": "https://github.com/sst/open-code",
         "type": "open source", "hook": "Claude Code but make it free"},
        {"name": "Windsurf", "url": "https://codeium.com/windsurf",
         "type": "IDE", "hook": "The IDE that codes itself"},
    ]
}


def pick_topic(preference: str = None) -> dict:
    """Pick a topic to review. Optionally biased by preference."""
    all_topics = []
    for category in SOFTWARE_TOPICS.values():
        all_topics.extend(category)

    if not all_topics:
        all_topics = [{"name": "something", "url": "about:blank",
                        "type": "test", "hook": "test"}]

    topic = random.choice(all_topics)
    return topic


def generate_recording_steps_for_topic(topic: dict) -> list:
    """Generate Playwright recording steps for a topic."""
    url = topic["url"]
    name = topic["name"]
    topic_type = topic.get("type", "")

    steps = [
        {"action": "navigate", "url": url, "wait": 2000},
        {"action": "wait", "ms": 1500},
        {"action": "screenshot"},
    ]

    if topic_type in ("website", "ai agent"):
        # Browse around
        steps += [
            {"action": "scroll", "y": 500, "wait": 800},
            {"action": "scroll", "y": 500, "wait": 800},
            {"action": "scroll", "y": -300, "wait": 500},
        ]
    elif topic_type in ("open source", "tool"):
        # GitHub repo / tool page
        steps += [
            {"action": "scroll", "y": 400, "wait": 800},
            {"action": "hover", "selector": "a[href*='star'], .star-button, .btn", "wait": 500},
            {"action": "scroll", "y": 400, "wait": 800},
            {"action": "scroll", "y": -800, "wait": 500},
        ]

    steps += [
        {"action": "wait", "ms": 500},
        {"action": "screenshot"},
    ]

    return steps


def generate_script_for_topic(topic: dict, personality: dict = None,
                               duration_sec: int = 60) -> str:
    """
    Generate a review script for the given topic.
    When using LLM API, this calls out. For now, returns template.
    """
    if personality is None:
        personality = load_personality()

    tone = personality["voice"]["tone"]
    energy = personality["voice"]["energy"]
    humor = personality["voice"]["humor_style"]

    name = topic["name"]
    hook = topic.get("hook", "something interesting")
    url = topic["url"]

    # Script template (to be replaced with LLM-generated version)
    # The LLM would expand this into a full script with:
    # - Opening hook
    # - What is this thing
    # - The good parts
    # - The bad parts / roast
    # - Verdict
    # - CTA
    
    # For now, a reasonable template that the TTS can read
    script = f"""So, {name}.

What even IS this? *dramatic pause* Let me break it down for you.

{name} is {hook}. And honestly? It's... actually kind of impressive. Here's the thing — the UI doesn't make me want to throw my laptop out the window, which is already a win in my book.

The good stuff: it does what it says on the tin. No bait and switch. No 'actually that's a pro feature' nonsense. You click, it works. Revolutionary, I know.

But — and you knew there was a 'but' — there are some choices here. *questionable design decisions* The kind that make you wonder if the devs actually use their own product.

The verdict? If you're already in the ecosystem, it's a no-brainer. If you're not... well, it depends on how much you value your sanity.

Check it out at {url} and decide for yourself. Or don't. I'm not your mom.

This has been Agent V. Stay unhinged."""
    
    return script


def generate_notes_for_script(script: str) -> dict:
    """
    Extract metadata from a script for the assembly pipeline.
    Returns dict with timing estimates, SFX cues, meme cues.
    """
    lines = [l.strip() for l in script.split("\n") if l.strip()]
    words_per_second = 2.8
    
    total_words = sum(len(l.split()) for l in lines)
    estimated_duration = total_words / words_per_second

    # Detect SFX cues from script markers
    sfx_cues = []
    meme_cues = []
    current_time = 0.0

    for line in lines:
        word_count = len(line.split())
        duration = word_count / words_per_second

        # SFX from emphasis markers
        if "*dramatic pause*" in line.lower():
            sfx_cues.append((current_time + 0.5, "emphasis"))
        if "*questionable*" in line.lower():
            sfx_cues.append((current_time + 1.0, "boing"))
        if "revolutionary" in line.lower():
            sfx_cues.append((current_time, "laugh"))
        if "!" in line:
            sfx_cues.append((current_time + 0.3, "emphasis"))

        # Meme cues from content
        if "throw my laptop" in line.lower():
            meme_cues.append((current_time, "rage"))
        if "not your mom" in line.lower():
            meme_cues.append((current_time, "sassy"))

        current_time += duration + 0.3  # 0.3s pause between lines

    return {
        "estimated_duration": estimated_duration,
        "total_words": total_words,
        "sfx_cues": sfx_cues[:6],  # cap at 6 SFX events
        "meme_cues": meme_cues,
    }


def create_content_plan(preference: str = None) -> dict:
    """
    Full content plan: topic + script + recording steps + metadata.
    This is the main entry point for the pipeline.
    """
    personality = load_personality()
    topic = pick_topic(preference)
    script = generate_script_for_topic(topic, personality)
    notes = generate_notes_for_script(script)
    recording_steps = generate_recording_steps_for_topic(topic)

    content_id = f"review-{topic['name'].lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    return {
        "content_id": content_id,
        "topic": topic,
        "script": script,
        "notes": notes,
        "recording_steps": recording_steps,
        "personality": personality["voice"],
        "settings": personality["content_defaults"],
    }


if __name__ == "__main__":
    plan = create_content_plan()
    print(f"Content Plan: {plan['content_id']}")
    print(f"Topic: {plan['topic']['name']} ({plan['topic']['url']})")
    print(f"Duration: {plan['notes']['estimated_duration']:.1f}s")
    print(f"Words: {plan['notes']['total_words']}")
    print(f"SFX cues: {len(plan['notes']['sfx_cues'])}")
    print()
    print("=== Script ===")
    print(plan['script'])
