#!/usr/bin/env python3
"""
X.com Curation Sync Tool

Syncs likes and bookmarks from X.com to a local graph database.

================================================================================
HOW IT WORKS
================================================================================

ARCHITECTURE:
    X.com Browser (CDP) → Scraper → Graph DB (graphqlite) → JSON Export

COMPONENTS:

1. BROWSER CONTROL (CDP)
   - Uses Chrome DevTools Protocol via agent-browser CLI
   - Connects to Chrome running with --remote-debugging-port=9222
   - Commands: navigate, scroll, eval JavaScript

2. SCRAPER (SCRAPER_JS)
   - Injected JavaScript that runs in the browser
   - Extracts from each tweet:
     * Content: text, url, author, handle
     * Metrics: likes, retweets, replies, views, bookmarks
     * Media: has_image, has_video, has_link, link_domain
     * Flags: is_retweet, is_quote
     * Timestamps: posted_at, engaged_at

3. SCROLL PAGINATION (scrape function)
   - Scrolls down to load more tweets
   - Stops when:
     * 4 consecutive empty extractions
     * Page bottom reached
     * 10 consecutive existing tweets (incremental mode)
     * 500 scroll safety limit

4. GRAPH DB INGESTION (ingest_tweets)
   Creates nodes:
     - Content (tweet)
     - Person (author, user)
     - Topic (hashtag, cashtag)
     - GitHubRepo
     - Domain

   Creates relationships:
     - @novaisabuilder -[LIKED]-> Content
     - @novaisabuilder -[BOOKMARKED]-> Content
     - Person -[POSTED]-> Content
     - Content -[HAS_TOPIC]-> Topic
     - Content -[MENTIONS_REPO]-> GitHubRepo
     - Content -[LINKS_TO]-> Domain

================================================================================
USAGE
================================================================================

    python sync.py                    # Incremental sync (if DB exists)
    python sync.py -t likes           # Sync likes only
    python sync.py -t bookmarks       # Sync bookmarks only
    python sync.py --full             # Force full scrape (ignore existing)
    python sync.py --export out.json  # Export DB to JSON

REQUIREMENTS:
    - Chrome running with: --remote-debugging-port=9222
    - pip install graphqlite
    - pip install agent-browser

TESTING:
    See test_sync.py for integration tests

================================================================================
"""

import subprocess
import json
import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Optional import - only needed for sync mode
try:
    from graphqlite import Graph
    HAS_GRAPHQLITE = True
except ImportError:
    HAS_GRAPHQLITE = False


# ============== CONFIG ==============

DEFAULT_CDP = "localhost:9222"
DEFAULT_DB = Path(__file__).parent.parent / "data" / "curation.db"

URLS = {
    "likes": "https://x.com/novaisabuilder/likes",
    "bookmarks": "https://x.com/i/bookmarks"
}

USER_HANDLE = "@novaisabuilder"


# ============== SCRAPER ==============

SCRAPER_JS_BATCH = '''
(function() {
    const tweets = [];
    const seen = new Set();
    const articles = document.querySelectorAll("article[data-testid=\\"tweet\\"]");
    
    articles.forEach(article => {
        const textEl = article.querySelector("div[data-testid=\\"tweetText\\"]");
        const linkEl = article.querySelector("a[href*=\\"/status/\\"]");
        const userEl = article.querySelector("div[data-testid=\\"User-Name\\"]");
        
        if (!textEl || !linkEl) return;
        
        const url = "https://x.com" + linkEl.getAttribute("href");
        if (seen.has(url)) return;
        seen.add(url);
        
        // Extract engagement metrics
        const getMetric = (label) => {
            const btn = article.querySelector(`button[aria-label*="${label}"]`);
            if (!btn) return 0;
            const match = btn.getAttribute("aria-label").match(/[\\d,]+/);
            return match ? parseInt(match[0].replace(/,/g, "")) : 0;
        };
        
        // Content type checks
        const hasImage = article.querySelector("div[data-testid=\\"tweetPhoto\\"]") !== null;
        const hasVideo = article.querySelector("div[data-testid=\\"videoComponent\\"]") !== null;
        const linkCard = article.querySelector("div[data-testid=\\"card.wrapper\\"]");
        const hasLink = linkCard !== null || textEl.querySelector("a[href^=\\"http\\"]") !== null;
        
        let linkDomain = "";
        if (linkCard) {
            const domainEl = linkCard.querySelector("[data-testid=\\"card.domain\\"]");
            if (domainEl) linkDomain = domainEl.innerText;
        }
        if (!linkDomain) {
            const extLink = textEl.querySelector("a[href^=\\"http\\"]");
            if (extLink) {
                try { linkDomain = new URL(extLink.href).hostname; } catch(e) {}
            }
        }
        
        const timeEl = article.querySelector("time");
        const postedAt = timeEl ? timeEl.getAttribute("datetime") : null;
        const isRetweet = article.querySelector("div[data-testid=\\"socialContext\\"]")?.innerText.includes("Reposted") || false;
        const isQuote = article.querySelector("div[data-testid=\\"tweet\\"] div[data-testid=\\"tweet\\"]") !== null;
        
        tweets.push({
            text: textEl.innerText.trim(),
            url: url,
            author: userEl ? userEl.innerText.split("\\n")[0].trim() : "",
            handle: userEl ? (userEl.innerText.match(/@[\\w]+/)?.[0] || "") : "",
            posted_at: postedAt,
            engaged_at: new Date().toISOString(),
            like_count: getMetric("Likes") || getMetric("Like"),
            retweet_count: getMetric("reposts") || getMetric("Repost"),
            reply_count: getMetric("Replies") || getMetric("Reply"),
            view_count: getMetric("views") || getMetric("View"),
            bookmark_count: getMetric("Bookmarks") || getMetric("Bookmark"),
            has_image: hasImage,
            has_video: hasVideo,
            has_link: hasLink,
            link_domain: linkDomain,
            is_retweet: isRetweet,
            is_quote: isQuote,
            media_count: (hasImage ? 1 : 0) + (hasVideo ? 1 : 0)
        });
    });
    
    // Batch all DOM queries into single return
    return JSON.stringify({
        tweets: tweets,
        count: articles.length,
        at_bottom: document.documentElement.scrollHeight - window.innerHeight - window.scrollY < 100
    });
})()
'''


def run_browser_cmd(cdp: str, cmd: str) -> str:
    """Run agent-browser command."""
    # Extract port from CDP (handles both "9222" and "localhost:9222")
    port = cdp.split(":")[-1] if ":" in cdp else cdp
    full_cmd = f"agent-browser --cdp {port} {cmd}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def wait_for_page_load(cdp: str, timeout_ms: int = 5000) -> bool:
    """Wait for page to be ready (document.readyState === 'complete')."""
    start = time.monotonic()
    poll_interval = 0.05  # 50ms
    
    while (time.monotonic() - start) * 1000 < timeout_ms:
        result = run_browser_cmd(cdp, "eval 'document.readyState'")
        if "complete" in result.lower():
            return True
        time.sleep(poll_interval)
    
    return False


def navigate(cdp: str, url: str):
    """Navigate to URL with event-based page load detection."""
    run_browser_cmd(cdp, f"open '{url}'")
    wait_for_page_load(cdp, timeout_ms=5000)


def scroll(cdp: str, times: int = 1):
    """Scroll down to load more content."""
    for _ in range(times):
        run_browser_cmd(cdp, "scroll down 1000")


def extract_batch(cdp: str) -> dict:
    """Extract tweets, count, and scroll position in ONE subprocess call.
    
    Returns:
        dict with keys: tweets (list), count (int), at_bottom (bool)
    """
    result = run_browser_cmd(cdp, f"eval '{SCRAPER_JS_BATCH}'")
    
    try:
        lines = result.strip().split('\n')
        for line in lines:
            if line.startswith('"'):
                # Extract JSON from quoted output
                json_str = line[1:-1] if line.endswith('"') else line[1:]
                json_str = json_str.encode().decode('unicode_escape')
                data = json.loads(json_str)
                return {
                    "tweets": data.get("tweets", []),
                    "count": data.get("count", 0),
                    "at_bottom": data.get("at_bottom", False)
                }
        return {"tweets": [], "count": 0, "at_bottom": False}
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return {"tweets": [], "count": 0, "at_bottom": False}


def scrape(cdp: str, tweet_type: str, existing_urls: set[str], full_mode: bool = False) -> list:
    """Scrape tweets from X.com.
    
    Optimized: Uses batched DOM queries - only 1 subprocess call per cycle.
    """
    
    if tweet_type not in URLS:
        raise ValueError(f"Unknown type: {tweet_type}")
    
    is_incremental = len(existing_urls) > 0 and not full_mode
    
    if is_incremental:
        print(f"Incremental mode: {len(existing_urls)} existing tweets in DB")
    
    print(f"Navigating to {tweet_type}...")
    navigate(cdp, URLS[tweet_type])
    
    all_tweets = []
    seen_urls = set()
    consecutive_empty = 0
    consecutive_existing = 0
    max_consecutive_empty = 4
    max_consecutive_existing = 10
    total_scrolls = 0
    previous_count = 0
    
    while True:
        # Single batched call: get tweets, count, and scroll position
        batch = extract_batch(cdp)
        tweets = batch["tweets"]
        count = batch["count"]
        at_bottom = batch["at_bottom"]
        
        new_count = 0
        existing_count = 0
        
        for tweet in tweets:
            if tweet["url"] not in seen_urls:
                seen_urls.add(tweet["url"])
                all_tweets.append(tweet)  # Always add for ingestion (to create relationships)
                
                # Track for progress display and stopping logic
                if is_incremental and tweet["url"] in existing_urls:
                    existing_count += 1
                else:
                    new_count += 1
        
        # Handle incremental mode stopping
        if is_incremental:
            if existing_count > 0 and new_count == 0:
                consecutive_existing += 1
                print(f"Found {existing_count} existing (adding relationships) [streak: {consecutive_existing}]")
            else:
                consecutive_existing = 0
                if new_count > 0 or existing_count > 0:
                    consecutive_empty = 0
                    msg = f"Collected {len(all_tweets)} tweets (+{new_count} new"
                    if existing_count > 0:
                        msg += f", {existing_count} existing"
                    msg += ")"
                    print(msg)
            
            if consecutive_existing >= max_consecutive_existing:
                print(f"✓ Stopped at {consecutive_existing} consecutive existing tweets")
                break
        elif new_count > 0:
            consecutive_empty = 0
            print(f"Extracted {len(all_tweets)} tweets (+{new_count})")
        else:
            consecutive_empty += 1
            print(f"Extracted {len(all_tweets)} (+0) [empty: {consecutive_empty}, bottom: {at_bottom}]")
            
            if consecutive_empty >= max_consecutive_empty:
                print(f"✓ Reached end after {total_scrolls} scrolls")
                break
            if at_bottom:
                print(f"✓ Reached page bottom after {total_scrolls} scrolls")
                break
        
        # Scroll and wait for new content
        scroll(cdp, 1)
        total_scrolls += 1
        
        # Simple wait: if count hasn't changed from previous, give more time
        # Otherwise a short delay is sufficient since content loaded
        if count <= previous_count:
            time.sleep(0.15)  # 150ms - content still loading
        # else: content already loaded, proceed immediately
        
        previous_count = count
        
        if total_scrolls > 500:
            print("⚠ Safety limit (500 scrolls)")
            break
    
    return all_tweets


# ============== GRAPH DB ==============

def extract_topics(text: str) -> list[str]:
    """Extract hashtags and cashtags."""
    hashtags = re.findall(r'#(\w+)', text)
    cashtags = re.findall(r'\$(\w+)', text)
    return list(set(hashtags + cashtags))


def extract_github_repos(text: str) -> list[str]:
    """Extract GitHub repo references."""
    return list(set(re.findall(r'github\.com/([\w-]+/[\w-]+)', text)))


def get_existing_urls(graph: Graph) -> set[str]:
    """Get URLs already in database."""
    try:
        results = graph.query('MATCH (c:Content) RETURN c.url as url')
        return {r['url'] for r in results}
    except:
        return set()


def ingest_tweets(graph: Graph, tweets: list[dict], relationship: str) -> tuple[int, int]:
    """Ingest tweets into graph DB. Returns (new_content_count, existing_content_count).
    
    A URL can have multiple relationships (LIKED, BOOKMARKED, or both).
    - Creates Content node only if URL doesn't exist (avoid duplicate data)
    - Always creates the relationship edge for that URL
    """
    
    existing = get_existing_urls(graph)
    new_count = 0
    existing_count = 0
    engaged_at = datetime.now().isoformat()
    
    # Ensure user exists
    graph.upsert_node(USER_HANDLE, {"handle": USER_HANDLE, "name": "Nova Builds"}, label="Person")
    
    for tweet in tweets:
        url = tweet.get("url", "")
        tweet_id = url.split("/")[-1]
        content_id = f"tweet_{tweet_id}"
        
        url_exists = url in existing
        
        if url_exists:
            existing_count += 1
        else:
            new_count += 1
            
            # Content node (only create if new)
            graph.upsert_node(content_id, {
                "text": tweet.get("text", ""),
                "url": url,
                "author_handle": tweet.get("handle", ""),
                "author_name": tweet.get("author", ""),
                "posted_at": tweet.get("posted_at"),
                "engaged_at": tweet.get("engaged_at", engaged_at),
                "ingested_at": engaged_at,
                "like_count": tweet.get("like_count", 0),
                "retweet_count": tweet.get("retweet_count", 0),
                "reply_count": tweet.get("reply_count", 0),
                "view_count": tweet.get("view_count", 0),
                "bookmark_count": tweet.get("bookmark_count", 0),
                "has_image": tweet.get("has_image", False),
                "has_video": tweet.get("has_video", False),
                "has_link": tweet.get("has_link", False),
                "link_domain": tweet.get("link_domain", ""),
                "is_retweet": tweet.get("is_retweet", False),
                "is_quote": tweet.get("is_quote", False),
                "media_count": tweet.get("media_count", 0)
            }, label="Content")
            
            # Author (only create for new content)
            if tweet.get("handle"):
                graph.upsert_node(tweet["handle"], {
                    "handle": tweet["handle"],
                    "name": tweet.get("author", "")
                }, label="Person")
                graph.upsert_edge(tweet["handle"], content_id, {
                    "timestamp": tweet.get("posted_at", engaged_at)
                }, rel_type="POSTED")
            
            # Topics (only create for new content)
            for topic in extract_topics(tweet.get("text", "")):
                topic_id = f"topic_{topic.lower()}"
                topic_type = "Cashtag" if topic.isupper() or topic[0].isdigit() else "Hashtag"
                graph.upsert_node(topic_id, {"name": topic, "type": topic_type}, label="Topic")
                graph.upsert_edge(content_id, topic_id, {}, rel_type="HAS_TOPIC")
            
            # GitHub repos (only create for new content)
            for repo in extract_github_repos(tweet.get("text", "")):
                repo_id = f"github_{repo.replace('/', '_')}"
                graph.upsert_node(repo_id, {"full_name": repo, "url": f"https://github.com/{repo}"}, label="GitHubRepo")
                graph.upsert_edge(content_id, repo_id, {}, rel_type="MENTIONS_REPO")
            
            # Domains (only create for new content)
            if tweet.get("link_domain"):
                domain_id = f"domain_{tweet['link_domain'].replace('.', '_')}"
                graph.upsert_node(domain_id, {"domain": tweet["link_domain"], "url": f"https://{tweet['link_domain']}"}, label="Domain")
                graph.upsert_edge(content_id, domain_id, {}, rel_type="LINKS_TO")
        
        # Always create the relationship edge (LIKED or BOOKMARKED)
        # This allows a URL to have multiple relationships
        graph.upsert_edge(USER_HANDLE, content_id, {
            "engagement_type": relationship.lower(),
            "timestamp": tweet.get("engaged_at", engaged_at)
        }, rel_type=relationship)
    
    return new_count, existing_count


def get_stats(graph: Graph) -> dict:
    """Get database statistics."""
    stats = {"nodes": {}, "relationships": {}}
    
    for label in ["Person", "Content", "Topic", "GitHubRepo", "Domain"]:
        try:
            cnt = graph.query(f'MATCH (n:{label}) RETURN count(n) as cnt')[0]['cnt']
            stats["nodes"][label] = cnt
        except:
            stats["nodes"][label] = 0
    
    for rel in ["LIKED", "BOOKMARKED", "POSTED", "HAS_TOPIC", "MENTIONS_REPO", "LINKS_TO"]:
        try:
            cnt = graph.query(f'MATCH ()-[r:{rel}]->() RETURN count(r) as cnt')[0]['cnt']
            stats["relationships"][rel] = cnt
        except:
            stats["relationships"][rel] = 0
    
    return stats


def print_stats(graph: Graph):
    """Print formatted stats."""
    stats = get_stats(graph)
    
    print("\n=== DATABASE STATS ===")
    print("Nodes:")
    for label, cnt in stats["nodes"].items():
        print(f"  {label}: {cnt}")
    print("Relationships:")
    for rel, cnt in stats["relationships"].items():
        print(f"  {rel}: {cnt}")
    
    # Top topics
    try:
        results = graph.query('MATCH (c:Content)-[:HAS_TOPIC]->(t:Topic) RETURN t.name as topic, count(c) as cnt ORDER BY cnt DESC LIMIT 5')
        if results:
            print("\nTop topics:")
            for r in results:
                print(f"  {r['topic']}: {r['cnt']}")
    except:
        pass


def export_to_json(graph: Graph, output_path: str):
    """Export database to JSON file."""
    
    print(f"Exporting to {output_path}...")
    
    # Get all content with relationships
    content = graph.query('MATCH (c:Content) RETURN c')
    
    # Get topics for each content
    export_data = []
    for item in content:
        node = item.get('c', {})
        props = node.get('properties', {})
        
        # Get topics
        try:
            topics = graph.query(f'MATCH (Content {{id: "{props.get("id")}"}})-[:HAS_TOPIC]->(t:Topic) RETURN t.name as name')
            props['topics'] = [t['name'] for t in topics]
        except:
            props['topics'] = []
        
        export_data.append(props)
    
    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported {len(export_data)} tweets to {output_path}")


# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(
        description="X.com Curation Sync Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python sync.py                    # Incremental sync (if DB exists) or full
    python sync.py -t likes           # Sync likes only
    python sync.py --full             # Force full scrape
    python sync.py --export out.json  # Export DB to JSON
        """
    )
    
    parser.add_argument("-i", "--input", default=DEFAULT_CDP,
                        help=f"CDP URL (default: {DEFAULT_CDP})")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help=f"DB path (default: {DEFAULT_DB})")
    parser.add_argument("-t", "--type", choices=["likes", "bookmarks", "all"], default="all",
                        help="What to sync (default: all)")
    parser.add_argument("--full", action="store_true",
                        help="Force full scrape (ignore existing DB)")
    parser.add_argument("--export", type=str, default=None,
                        help="Export DB to JSON file (no scraping)")
    
    args = parser.parse_args()
    
    # Determine DB path
    db_path = Path(args.output) if args.output else DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not HAS_GRAPHQLITE:
        print("Error: graphqlite not installed. Run: pip install graphqlite")
        return 1
    
    # Open database
    graph = Graph(str(db_path))
    
    # Export mode
    if args.export:
        export_to_json(graph, args.export)
        print_stats(graph)
        return 0
    
    # Sync mode
    existing_urls = get_existing_urls(graph) if db_path.exists() and not args.full else set()
    
    types_to_sync = ["likes", "bookmarks"] if args.type == "all" else [args.type]
    
    total_new = 0
    total_skipped = 0
    
    for tweet_type in types_to_sync:
        print(f"\n=== SYNCING {tweet_type.upper()} ===")
        
        # Scrape
        tweets = scrape(args.input, tweet_type, existing_urls, full_mode=args.full)
        
        # Ingest
        if tweets:
            print(f"Ingesting {len(tweets)} tweets...")
            relationship = "LIKED" if tweet_type == "likes" else "BOOKMARKED"
            new_count, skipped_count = ingest_tweets(graph, tweets, relationship)
            print(f"  New: {new_count}, Skipped: {skipped_count}")
            total_new += new_count
            total_skipped += skipped_count
        else:
            print("No new tweets to ingest")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total new: {total_new}")
    print(f"Total skipped: {total_skipped}")
    
    print_stats(graph)
    
    return 0


if __name__ == "__main__":
    exit(main())
