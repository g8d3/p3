"""
Personality Engine
Manages the creator personality profile and refinement loop.
"""

import yaml
import json
import os
from pathlib import Path
from datetime import datetime


PERSONALITY_PATH = Path(__file__).parent.parent / "config" / "personality.yaml"


def load_personality() -> dict:
    """Load the current personality profile."""
    with open(PERSONALITY_PATH) as f:
        return yaml.safe_load(f)


def save_personality(personality: dict):
    """Save updated personality profile."""
    with open(PERSONALITY_PATH, "w") as f:
        yaml.dump(personality, f, default_flow_style=False, sort_keys=False)


def get_persona_prompt() -> str:
    """
    Generate a system prompt for the LLM from the personality profile.
    This is injected when the LLM needs to write content.
    """
    p = load_personality()
    identity = p["identity"]
    voice = p["voice"]
    tactics = p["viral_tactics"]

    prompt = f"""You are {identity['name']}. {identity['tagline']}.

Your persona: {identity['persona']}

Voice:
- Tone: {voice['tone']}
- Energy: {voice['energy']}
- Formality: {voice['formality']}
- Humor style: {voice['humor_style']}

Viral tactics to follow:
{chr(10).join(f'- {t}' for t in tactics)}

Meme preferences: {p['meme_preferences']['style']} style, {p['meme_preferences']['frequency']} frequency.

Write in this voice consistently. Don't break character."""
    return prompt


def record_engagement(iteration: int, content_id: str,
                       views: int = 0, likes: int = 0,
                       shares: int = 0, comments: int = 0):
    """Record engagement data for a content piece."""
    p = load_personality()
    p["learning"]["iterations"] = iteration
    p["learning"]["engagement_history"].append({
        "content_id": content_id,
        "views": views,
        "likes": likes,
        "shares": shares,
        "comments": comments,
        "timestamp": datetime.now().isoformat(),
    })
    save_personality(p)


def refine_personality_from_feedback(feedback: dict):
    """
    Update personality based on engagement feedback.
    This is called after content performance data is available.
    
    feedback: {
        "engagement_rate": float,
        "best_tactics": [str],
        "worst_tactics": [str],
        "suggested_tone_shift": str or None
    }
    """
    p = load_personality()

    # Update viral tactics
    if feedback.get("best_tactics"):
        p["learning"]["best_performing_tactics"] = feedback["best_tactics"]

    if feedback.get("worst_tactics"):
        p["learning"]["worst_performing_tactics"] = feedback["worst_tactics"]

    # Adjust tone based on what works
    if feedback.get("engagement_rate", 0) > 0.05:  # >5% engagement is good
        pass  # Keep current style
    elif feedback.get("suggested_tone_shift"):
        p["voice"]["tone"] = feedback["suggested_tone_shift"]

    # Adjust energy based on engagement
    if feedback.get("engagement_rate", 0) < 0.01 and p["voice"]["energy"] != "high":
        p["voice"]["energy"] = "high"

    p["learning"]["last_refined"] = datetime.now().isoformat()
    save_personality(p)


def iteration_report() -> dict:
    """Get a report on current iteration state."""
    p = load_personality()
    learning = p["learning"]
    history = learning.get("engagement_history", [])

    return {
        "iterations": learning["iterations"],
        "total_content": len(history),
        "best_tactics": learning["best_performing_tactics"],
        "worst_tactics": learning["worst_performing_tactics"],
        "last_refined": learning["last_refined"],
        "current_tone": p["voice"]["tone"],
        "current_energy": p["voice"]["energy"],
    }


if __name__ == "__main__":
    print("Current personality report:")
    report = iteration_report()
    for k, v in report.items():
        print(f"  {k}: {v}")
    print()
    print("=== Persona prompt (for LLM injection) ===")
    print(get_persona_prompt())
