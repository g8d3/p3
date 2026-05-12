#!/usr/bin/env python3
"""Fetches trending news/topics from free sources for continuous video generation."""
import json, random, requests, xml.etree.ElementTree as ET, subprocess, sys, os, asyncio
from pathlib import Path
from datetime import datetime

# ── Free news sources (no API key required) ──────────────────────────────
SOURCES = {
    "hackernews": "https://hacker-news.firebaseio.com/v0/topstories.json",
    "techcrunch": "https://techcrunch.com/feed/",
    "wired": "https://www.wired.com/feed/rss",
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
    "theverge": "https://www.theverge.com/rss/index.xml",
}

def fetch_hn_topics(n=15) -> list:
    """Fetch top stories from Hacker News, return (title, url) pairs."""
    try:
        r = requests.get(SOURCES["hackernews"], timeout=15)
        ids = r.json()[:n]
        items = []
        for i in ids:
            ir = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=10)
            item = ir.json()
            if item and item.get("title") and item.get("type") == "story":
                items.append((item["title"], item.get("url", f"https://news.ycombinator.com/item?id={i}")))
        return items
    except Exception as e:
        print(f"  ⚠ HN fetch error: {e}")
        return []

def fetch_rss_topics(url: str, n=5) -> list:
    """Fetch topics from an RSS feed."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
        root = ET.fromstring(r.content)
        items = []
        # Handle both RSS and Atom formats
        for entry in root.findall(".//item")[:n]:
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            if title: items.append((title, link))
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:n]:
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            if title: items.append((title, link))
        return items
    except Exception as e:
        print(f"  ⚠ RSS fetch error ({url[:30]}...): {e}")
        return []

def fetch_all_topics() -> list:
    """Fetch topics from ALL sources and return ranked."""
    print("  HN...", end="", flush=True)
    hn = fetch_hn_topics()
    print(f" {len(hn)} stories")
    all_items = [("HN: " + t, u) for t, u in hn]
    for name, url in SOURCES.items():
        if name == "hackernews": continue
        print(f"  {name}...", end="", flush=True)
        rss = fetch_rss_topics(url)
        print(f" {len(rss)} items")
        all_items.extend(rss)
    random.shuffle(all_items)  # Mix sources
    return all_items

def pick_topic(items: list) -> dict:
    """Pick the most interesting topic from the list."""
    if not items:
        return {"title": "Why AI agents are overhyped (and why they still matter)",
                "url": "https://en.wikipedia.org/wiki/AI_agent"}
    # Use OpenCode Go to pick the most viral/interesting topic
    go_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    if go_key and len(items) > 3:
        from openai import OpenAI
        titles = "\n".join(f"- {t}" for t, u in items[:20])
        client = OpenAI(api_key=go_key, base_url="https://opencode.ai/zen/go/v1")
        try:
            r = client.chat.completions.create(
                model=os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash"),
                max_tokens=256,
                messages=[{"role":"user","content":f"Pick the single most interesting, viral-potential topic from this list for a video script. Reply ONLY with the exact title:\n{titles}"}])
            chosen_title = r.choices[0].message.content.strip()
            for t, u in items:
                if t.strip() == chosen_title:
                    return {"title": t, "url": u}
            # If exact match fails, find closest
            for t, u in items:
                if any(w in t.lower() for w in chosen_title.lower().split()[:3]):
                    return {"title": t, "url": u}
        except: pass
    # Fallback: random pick
    t, u = random.choice(items)
    return {"title": t, "url": u}

# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["plain","json"], default="plain")
    ap.add_argument("--count", type=int, help="Show N topics instead of picking one")
    args = ap.parse_args()

    print("🌐 Fetching trending topics...")
    items = fetch_all_topics()
    print(f"\nTotal: {len(items)} topics")

    if args.count:
        for i, (t, u) in enumerate(items[:args.count], 1):
            print(f"  {i}. {t}")
            print(f"     {u}\n")
    elif args.format == "json":
        topic = pick_topic(items)
        print(json.dumps(topic))
    else:
        topic = pick_topic(items)
        print(f"\n{'='*60}")
        print(f"  Selected topic: {topic['title']}")
        print(f"  URL: {topic['url']}")
        print(f"{'='*60}")
        # Generate the video
        print("\nGenerating video...")
        sys.exit(0)  # Let the pipeline handle it
