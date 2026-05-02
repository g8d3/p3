"""
Social Media Posting Module
Handles posting content to various platforms.
Current focus: save to local files (ready for posting).
Future: API-based posting to YouTube, Twitter/X, TikTok, etc.
"""

import json
import os
from pathlib import Path
from datetime import datetime


OUTPUT_DIR = Path(__file__).parent.parent / "output"


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_post_text(content_plan: dict, platform: str = "twitter") -> str:
    """
    Generate platform-appropriate post text from content plan.
    """
    name = content_plan["topic"]["name"]
    hook = content_plan["topic"].get("hook", "check this out")

    posts = {
        "twitter": f"reviewed {name} so you don't have to\n\n{hook}\n\n#SoftwareReview #AI",
        "twitter_short": f"{name}: {hook}. Full review 👇",
        "linkedin": f"I reviewed {name} — here's what I found\n\n{hook}\n\nFull video in comments 👇",
        "tiktok": f"POV: you let an AI review {name} #tech #review #ai",
        "youtube": f"I reviewed {name} so you don't have to | Honest AI Review",
        "mastodon": f"Reviewed {name}: {hook}\n\nFull video: [link] #techreview",
    }

    return posts.get(platform, posts["twitter"])


def save_post(content_plan: dict, video_path: str = None,
              platform: str = "all") -> dict:
    """
    Save a post-ready package to the output directory.
    Includes: video info, post text for each platform, metadata.
    """
    ensure_output_dir()
    content_id = content_plan["content_id"]
    post_dir = OUTPUT_DIR / content_id
    post_dir.mkdir(exist_ok=True)

    # Generate post texts for all platforms
    platforms = ["twitter", "linkedin", "tiktok", "youtube", "mastodon"]
    post_texts = {}
    for plat in platforms:
        post_texts[plat] = generate_post_text(content_plan, plat)

    # Save post package
    post_package = {
        "content_id": content_id,
        "topic": content_plan["topic"]["name"],
        "url": content_plan["topic"]["url"],
        "created": datetime.now().isoformat(),
        "video_path": video_path,
        "post_texts": post_texts,
        "script": content_plan["script"],
    }

    manifest_path = post_dir / "post_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(post_package, f, indent=2)

    # Also save individual post files for easy copy-paste
    for plat in platforms:
        txt_path = post_dir / f"post_{plat}.txt"
        with open(txt_path, "w") as f:
            f.write(post_texts[plat])

    # Save script
    script_path = post_dir / "script.txt"
    with open(script_path, "w") as f:
        f.write(content_plan["script"])

    print(f"  ✓ Post package saved to: {post_dir}")
    print(f"  ✓ {len(platforms)} platform texts generated")

    return post_package


def get_pending_posts() -> list:
    """Get list of posts ready for publishing."""
    ensure_output_dir()
    pending = []
    for d in sorted(OUTPUT_DIR.iterdir()):
        manifest = d / "post_manifest.json"
        if manifest.exists():
            with open(manifest) as f:
                pending.append(json.load(f))
    return pending


def mark_posted(content_id: str):
    """Mark a post as published."""
    post_dir = OUTPUT_DIR / content_id
    posted_flag = post_dir / ".posted"
    posted_flag.touch()


if __name__ == "__main__":
    print(f"Social module ready. Output: {OUTPUT_DIR}")
    pending = get_pending_posts()
    print(f"Pending posts: {len(pending)}")
