#!/usr/bin/env python3
"""
AI Content Factory - Smart Topic Generator
Researches trending topics and creates engaging content ideas
"""

import json
import os
import random
import subprocess
from datetime import datetime

# Fallback topic pools (used if no internet)
TOPIC_POOLS = {
    "ai": [
        # Trending AI topics (researched)
        "Build an AI SaaS in 24 Hours",
        "Claude Code Tutorial: Build Real Apps",
        "Cursor AI: Complete Guide 2025",
        "AI Agent Tutorial: Multi-Agent Systems",
        "Build a RAG App with Local Models",
        "Self-Hosted AI: Run Llama3 at Home",
        "AI Coding Workflow with Claude",
        "Build AI Products Without Coding",
        "OpenAI API Mastery Course",
        "AI Side Project Ideas That Make Money",
    ],
    "crypto": [
        # Bittensor & DePIN
        "Bittensor Subnet Development Guide",
        "Run Bittensor Validator Complete Guide",
        "Build on Bittensor API",
        "TAO Token Staking Tutorial",
        "DePIN Projects Explained",
        "AI Crypto Tokens to Watch",
        "Build Blockchain AI App",
    ],
    "robotics": [
        "ROS2 Complete Tutorial",
        "Build Robot with Raspberry Pi",
        "Computer Vision for Robots",
        "SLAM Navigation Tutorial",
        "ESP32 Robotics Projects",
    ],
    "business": [
        "AI Consulting Business Guide",
        "Build AI Agency from Scratch",
        "Freelance AI Developer Guide",
        "Sell AI Services Online",
    ]
}

class SmartTopicGenerator:
    """Generates topics based on web research"""
    
    def __init__(self, niche="ai"):
        self.niche = niche
    
    def research_trending(self):
        """Search for trending topics online"""
        try:
            # Use websearch to find trending topics
            result = subprocess.run([
                "python3", "-c", """
import json
import sys
sys.path.insert(0, '.')
from websearch import websearch
results = websearch({'numResults': 5, 'query': 'trending AI coding tutorials 2025 2026'})
print(json.dumps(results))
"""], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return []
    
    def generate_smart_topic(self):
        """Generate a topic based on what's working"""
        niche_topics = TOPIC_POOLS.get(self.niche, TOPIC_POOLS["ai"])
        
        # Pick a topic and make it specific
        base_topic = random.choice(niche_topics)
        
        # Add specific frameworks/versions for engagement
        enhancements = {
            "ai": [
                "with Claude Code",
                "using Cursor AI",
                "with Ollama",
                "with OpenAI API",
                "2025 Complete Guide",
            ],
            "crypto": [
                "with Python",
                "2025 Tutorial",
                "Step by Step",
                "From Scratch",
            ]
        }
        
        enhancers = enhancements.get(self.niche, enhancements["ai"])
        topic = f"{base_topic} {random.choice(enhancers)}"
        
        # Generate engaging outline
        outline = self._create_engaging_outline(topic)
        
        # Generate hook (for thumbnail/title)
        hook = self._create_hook(topic)
        
        return {
            "id": f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "topic": topic,
            "hook": hook,
            "type": random.choice(["tutorial", "guide", "demo"]),
            "outline": outline,
            "niche": self.niche,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
    
    def _create_engaging_outline(self, topic):
        """Create an outline that matches YouTube best practices"""
        topic_lower = topic.lower()
        
        if "tutorial" in topic_lower or "guide" in topic_lower:
            return [
                "INTRO: What we'll build & why it's valuable (hook)",
                "PREREQUISITES: What you need (tools, accounts)",
                "STEP 1: Setup & Installation (show screen)",
                "STEP 2: Core Concepts (brief explanation)",
                "STEP 3: Implementation (code along)",
                "STEP 4: Testing & Debugging",
                "STEP 5: Deployment/Usage",
                "OUTRO: Summary & CTA (like, subscribe)"
            ]
        elif "build" in topic_lower or "create" in topic_lower:
            return [
                "INTRO: Show the end result (demo first!)",
                "WHY: Why this matters/why learn it",
                "SETUP: Environment setup",
                "BUILD: Step-by-step coding",
                "TEST: Verify it works",
                "DEPLOY: How to share/use",
                "NEXT: How to extend it"
            ]
        else:
            return [
                "HOOK: Grab attention",
                "CONTEXT: Why this topic matters",
                "MAIN: Core content",
                "EXAMPLES: Real examples",
                "PRACTICE: Try it yourself",
                "SUMMARY: Key takeaways"
            ]
    
    def _create_hook(self, topic):
        """Create an engaging YouTube-style hook"""
        hooks = [
            f"🚨 {topic.replace(':', '')} - FULL TUTORIAL",
            f"⚡ {topic.replace(':', '')} in 10 MINUTES",
            f"🔥 {topic.replace(':', '')} - STEP BY STEP",
            f"✅ {topic.replace(':', '')} - COMPLETE GUIDE",
        ]
        return random.choice(hooks)
    
    def generate_batch(self, count=7):
        """Generate topics for the week"""
        topics = []
        for _ in range(count):
            topics.append(self.generate_smart_topic())
        return topics
    
    def save_topics(self, topics, filepath=None):
        """Save topics to file"""
        if not filepath:
            filepath = os.path.expanduser("~/.config/ai-content-factory/data/content_plan.json")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(topics, f, indent=2)
        return filepath


def main():
    import sys
    
    niche = sys.argv[1] if len(sys.argv) > 1 else "ai"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    
    generator = SmartTopicGenerator(niche)
    topics = generator.generate_batch(count)
    
    filepath = generator.save_topics(topics)
    
    print(f"Generated {len(topics)} engaging topics for {niche}")
    print(f"Saved to: {filepath}\n")
    
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic['topic']}")
        print(f"   Hook: {topic.get('hook', '')}")
        print()


if __name__ == "__main__":
    main()
