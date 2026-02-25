#!/usr/bin/env python3
"""
X.com Likes/Bookmarks Scraper
Extracts tweets from X.com via browser automation (CDP at port 9222)

Usage:
    python x_scraper.py --type likes --count 20
    python x_scraper.py --type bookmarks --count 10 --output data/bookmarks.json
"""

import subprocess
import json
import argparse
import time
from pathlib import Path

CDP_PORT = 9222

SCRAPER_JS = '''
(function() {
    const tweets = [];
    const seen = new Set();
    
    document.querySelectorAll("article[data-testid=\\"tweet\\"]").forEach(article => {
        const textEl = article.querySelector("div[data-testid=\\"tweetText\\"]");
        const linkEl = article.querySelector("a[href*=\\"/status/\\"]");
        const userEl = article.querySelector("div[data-testid=\\"User-Name\\"]");
        
        if (!textEl || !linkEl) return;
        
        const url = "https://x.com" + linkEl.getAttribute("href");
        if (seen.has(url)) return;
        seen.add(url);
        
        // Extract engagement metrics from button aria-labels
        const getMetric = (label) => {
            const btn = article.querySelector(`button[aria-label*="${label}"]`);
            if (!btn) return 0;
            const match = btn.getAttribute("aria-label").match(/[\\d,]+/);
            return match ? parseInt(match[0].replace(/,/g, "")) : 0;
        };
        
        // Check content type
        const hasImage = article.querySelector("div[data-testid=\\"tweetPhoto\\"]") !== null;
        const hasVideo = article.querySelector("div[data-testid=\\"videoComponent\\"]") !== null;
        const linkCard = article.querySelector("div[data-testid=\\"card.wrapper\\"]");
        const hasLink = linkCard !== null || textEl.querySelector("a[href^=\\"http\\"]") !== null;
        
        // Extract external link domain
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
        
        // Extract timestamp
        const timeEl = article.querySelector("time");
        const postedAt = timeEl ? timeEl.getAttribute("datetime") : null;
        
        // Check if retweet/quote
        const isRetweet = article.querySelector("div[data-testid=\\"socialContext\\"]")?.innerText.includes("Reposted") || false;
        const isQuote = article.querySelector("div[data-testid=\\"tweet\\"] div[data-testid=\\"tweet\\"]") !== null;
        
        tweets.push({
            text: textEl.innerText.trim(),
            url: url,
            author: userEl ? userEl.innerText.split("\\n")[0].trim() : "",
            handle: userEl ? (userEl.innerText.match(/@[\\w]+/)?.[0] || "") : "",
            // Temporal
            posted_at: postedAt,
            engaged_at: new Date().toISOString(),
            // Engagement metrics
            like_count: getMetric("Likes") || getMetric("Like"),
            retweet_count: getMetric("reposts") || getMetric("Repost"),
            reply_count: getMetric("Replies") || getMetric("Reply"),
            view_count: getMetric("views") || getMetric("View"),
            bookmark_count: getMetric("Bookmarks") || getMetric("Bookmark"),
            // Content type
            has_image: hasImage,
            has_video: hasVideo,
            has_link: hasLink,
            link_domain: linkDomain,
            is_retweet: isRetweet,
            is_quote: isQuote,
            // Media count
            media_count: (hasImage ? 1 : 0) + (hasVideo ? 1 : 0)
        });
    });
    return JSON.stringify(tweets);
})()
'''

URLS = {
    "likes": "https://x.com/novaisabuilder/likes",
    "bookmarks": "https://x.com/i/bookmarks"
}

def run_browser_cmd(cmd: str) -> str:
    """Run agent-browser command and return output."""
    full_cmd = f"agent-browser --cdp {CDP_PORT} {cmd}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def navigate(url: str):
    """Navigate to URL."""
    run_browser_cmd(f"open '{url}'")
    time.sleep(2)

def scroll(times: int = 1):
    """Scroll down to load more content."""
    for _ in range(times):
        run_browser_cmd("scroll down 1000")
        time.sleep(1)

def extract_tweets() -> list:
    """Extract tweets from current page."""
    result = run_browser_cmd(f"eval '{SCRAPER_JS}'")
    
    # Parse JSON from output (handle quotes and escapes)
    try:
        # Find JSON array in output
        lines = result.strip().split('\n')
        for line in lines:
            if line.startswith('"['):
                # Unescape the JSON string
                json_str = line[1:-1]  # Remove surrounding quotes
                json_str = json_str.encode().decode('unicode_escape')
                return json.loads(json_str)
        return []
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw output: {result[:500]}")
        return []

def check_scroll_end() -> bool:
    """Check if we've reached the bottom of the page."""
    result = run_browser_cmd("eval 'document.documentElement.scrollHeight - window.innerHeight - window.scrollY < 100'")
    return "true" in result.lower()

def get_existing_urls() -> set[str]:
    """Get URLs already in the graph database."""
    try:
        from graphqlite import Graph
        db_path = Path(__file__).parent.parent / "data" / "curation.db"
        if not db_path.exists():
            return set()
        g = Graph(str(db_path))
        results = g.query('MATCH (c:Content) RETURN c.url as url')
        return {r['url'] for r in results}
    except Exception:
        return set()

def scrape(tweet_type: str, count: int = 0, output: str | None = None, verify_complete: bool = False, incremental: bool = False) -> list:
    """
    Scrape tweets of specified type.
    
    Args:
        tweet_type: 'likes' or 'bookmarks'
        count: Max tweets to scrape (0 = scrape all)
        output: Output file path
        verify_complete: Print verification that all tweets were scraped
        incremental: Stop when hitting tweets already in DB (for sync mode)
    """
    if tweet_type not in URLS:
        raise ValueError(f"Unknown type: {tweet_type}. Use 'likes' or 'bookmarks'")
    
    # Load existing URLs for incremental mode
    existing_urls = set()
    if incremental:
        existing_urls = get_existing_urls()
        print(f"Found {len(existing_urls)} existing tweets in DB (incremental mode)")
    
    print(f"Navigating to {tweet_type}...")
    navigate(URLS[tweet_type])
    
    all_tweets = []
    seen_urls = set()
    consecutive_empty = 0
    consecutive_existing = 0  # Track consecutive tweets already in DB
    max_consecutive_empty = 4
    max_consecutive_existing = 10  # Stop after 10 consecutive existing tweets
    total_scrolls = 0
    
    while True:
        tweets = extract_tweets()
        
        new_count = 0
        existing_count = 0
        for tweet in tweets:
            if tweet["url"] not in seen_urls:
                seen_urls.add(tweet["url"])
                
                # In incremental mode, check if already in DB
                if incremental and tweet["url"] in existing_urls:
                    existing_count += 1
                    continue  # Skip this tweet
                
                all_tweets.append(tweet)
                new_count += 1
        
        # Track consecutive existing tweets for incremental mode
        if incremental:
            if existing_count > 0 and new_count == 0:
                consecutive_existing += 1
                print(f"Skipped {existing_count} existing tweets [existing streak: {consecutive_existing}]")
            else:
                consecutive_existing = 0
                if new_count > 0:
                    consecutive_empty = 0
                    print(f"Extracted {len(all_tweets)} tweets (+{new_count} new)" + 
                          (f", skipped {existing_count} existing" if existing_count > 0 else ""))
            
            if consecutive_existing >= max_consecutive_existing:
                print(f"\n✓ INCREMENTAL: Stopped after {consecutive_existing} consecutive existing tweets")
                print(f"  New tweets found: {len(all_tweets)}")
                break
        elif new_count > 0:
            consecutive_empty = 0
            print(f"Extracted {len(all_tweets)} tweets (+{new_count} new)")
        else:
            consecutive_empty += 1
            at_bottom = check_scroll_end()
            print(f"Extracted {len(all_tweets)} tweets (+0 new) [empty streak: {consecutive_empty}, at_bottom: {at_bottom}]")
            
            if consecutive_empty >= max_consecutive_empty:
                if verify_complete:
                    print(f"\n✓ VERIFIED: Reached end after {total_scrolls} scrolls")
                    print(f"  Total unique tweets: {len(all_tweets)}")
                break
            
            if at_bottom:
                if verify_complete:
                    print(f"\n✓ VERIFIED: At page bottom after {total_scrolls} scrolls")
                    print(f"  Total unique tweets: {len(all_tweets)}")
                break
        
        # Check if we hit the requested count
        if count > 0 and len(all_tweets) >= count:
            print(f"\n⚠ Reached requested limit ({count}). May have more tweets.")
            break
        
        # Scroll to load more
        scroll(1)
        total_scrolls += 1
        
        # Safety limit (prevent infinite loops)
        if total_scrolls > 500:
            print(f"\n⚠ Safety limit reached (500 scrolls). Stopping.")
            break
    
    result = all_tweets if count == 0 else all_tweets[:count]
    
    if output:
        output_path = Path(str(output))
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved {len(result)} tweets to {output}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape X.com likes or bookmarks")
    parser.add_argument("--type", "-t", choices=["likes", "bookmarks"], required=True,
                        help="Type of tweets to scrape")
    parser.add_argument("--count", "-c", type=int, default=0,
                        help="Number of tweets to extract (0 = all)")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Scrape all tweets (equivalent to --count 0)")
    parser.add_argument("--verify", "-v", action="store_true",
                        help="Verify that all tweets were scraped (print confirmation)")
    parser.add_argument("--incremental", "-i", action="store_true",
                        help="Stop when hitting tweets already in DB (for sync)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output JSON file path")
    
    args = parser.parse_args()
    
    count = 0 if args.all else args.count
    tweets = scrape(args.type, count, args.output, verify_complete=args.verify, incremental=args.incremental)
    
    if not args.output:
        print(json.dumps(tweets, indent=2))


if __name__ == "__main__":
    main()
