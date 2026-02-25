#!/usr/bin/env python3
"""
Ingest X.com scraped data into GraphQLite graph database.

Usage:
    python ingest_to_graph.py --likes data/likes.json --bookmarks data/bookmarks.json
    python ingest_to_graph.py --likes data/likes.json  # Just likes
    python ingest_to_graph.py --likes data/likes.json --skip-existing  # Don't re-ingest
"""

import json
import argparse
import re
from datetime import datetime
from pathlib import Path
from graphqlite import Graph

DB_PATH = Path(__file__).parent.parent / "data" / "curation.db"
META_PATH = Path(__file__).parent.parent / "data" / "scrape_meta.json"


def get_existing_urls(graph: Graph) -> set[str]:
    """Get all URLs already in the database."""
    try:
        results = graph.query('MATCH (c:Content) RETURN c.url as url')
        return {r['url'] for r in results}
    except Exception:
        return set()


def load_scrape_meta() -> dict:
    """Load metadata about previous scrapes."""
    if META_PATH.exists():
        with open(META_PATH) as f:
            return json.load(f)
    return {"likes": {}, "bookmarks": {}}


def save_scrape_meta(meta: dict):
    """Save scrape metadata."""
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2)


def extract_topics(text: str) -> list[str]:
    """Extract hashtags and cashtags from text."""
    hashtags = re.findall(r'#(\w+)', text)
    cashtags = re.findall(r'\$(\w+)', text)
    return list(set(hashtags + cashtags))


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    urls = re.findall(r'https?://[^\s\n]+', text)
    return [u for u in urls if 'x.com/status' not in u]


def extract_github_repos(text: str) -> list[str]:
    """Extract GitHub repo references from text."""
    repos = re.findall(r'github\.com/([\w-]+/[\w-]+)', text)
    return list(set(repos))


def ingest_tweets(graph: Graph, tweets: list[dict], relationship: str, existing_urls: set[str] | None = None) -> tuple[int, int]:
    """
    Ingest tweets into graph database with enhanced metadata.
    
    Returns: (new_count, skipped_count)
    """
    user_handle = "@novaisabuilder"
    engaged_at = datetime.now().isoformat()
    
    if existing_urls is None:
        existing_urls = set()
    
    new_count = 0
    skipped_count = 0
    
    # Ensure user exists
    graph.upsert_node(
        user_handle,
        {"handle": user_handle, "name": "Nova Builds"},
        label="Person"
    )
    
    for tweet in tweets:
        tweet_url = tweet.get("url", "")
        
        # Skip if already in database
        if tweet_url in existing_urls:
            skipped_count += 1
            continue  # Skip to next tweet, don't re-ingest
        
        new_count += 1
        
        # Create content node with full metadata
        tweet_id = tweet["url"].split("/")[-1]
        content_id = f"tweet_{tweet_id}"
        
        content_data = {
            # Basic
            "text": tweet.get("text", ""),
            "url": tweet["url"],
            "author_handle": tweet.get("handle", ""),
            "author_name": tweet.get("author", ""),
            # Temporal
            "posted_at": tweet.get("posted_at"),
            "engaged_at": tweet.get("engaged_at", engaged_at),
            "ingested_at": engaged_at,
            # Engagement metrics
            "like_count": tweet.get("like_count", 0),
            "retweet_count": tweet.get("retweet_count", 0),
            "reply_count": tweet.get("reply_count", 0),
            "view_count": tweet.get("view_count", 0),
            "bookmark_count": tweet.get("bookmark_count", 0),
            # Content type
            "has_image": tweet.get("has_image", False),
            "has_video": tweet.get("has_video", False),
            "has_link": tweet.get("has_link", False),
            "link_domain": tweet.get("link_domain", ""),
            "is_retweet": tweet.get("is_retweet", False),
            "is_quote": tweet.get("is_quote", False),
            "media_count": tweet.get("media_count", 0)
        }
        graph.upsert_node(content_id, content_data, label="Content")
        
        # Create relationship from user to content with engagement type
        graph.upsert_edge(
            user_handle,
            content_id,
            {
                "engagement_type": relationship.lower(),
                "timestamp": tweet.get("engaged_at", engaged_at)
            },
            rel_type=relationship
        )
        
        # Create author node and relationship
        if tweet.get("handle"):
            author_id = tweet["handle"]
            graph.upsert_node(
                author_id,
                {"handle": tweet["handle"], "name": tweet.get("author", "")},
                label="Person"
            )
            graph.upsert_edge(
                author_id,
                content_id,
                {"timestamp": tweet.get("posted_at", engaged_at)},
                rel_type="POSTED"
            )
        
        # Extract and create topic nodes
        topics = extract_topics(tweet.get("text", ""))
        for topic in topics:
            topic_id = f"topic_{topic.lower()}"
            topic_type = "Cashtag" if topic.isupper() or topic[0].isdigit() else "Hashtag"
            graph.upsert_node(
                topic_id,
                {"name": topic, "type": topic_type},
                label="Topic"
            )
            graph.upsert_edge(content_id, topic_id, {}, rel_type="HAS_TOPIC")
        
        # Extract and create GitHub repo nodes
        repos = extract_github_repos(tweet.get("text", ""))
        for repo in repos:
            repo_id = f"github_{repo.replace('/', '_')}"
            graph.upsert_node(
                repo_id,
                {"full_name": repo, "url": f"https://github.com/{repo}"},
                label="GitHubRepo"
            )
            graph.upsert_edge(content_id, repo_id, {}, rel_type="MENTIONS_REPO")
        
        # Create Domain node if external link present
        link_domain = tweet.get("link_domain", "")
        if link_domain:
            domain_id = f"domain_{link_domain.replace('.', '_')}"
            graph.upsert_node(
                domain_id,
                {"domain": link_domain, "url": f"https://{link_domain}"},
                label="Domain"
            )
            graph.upsert_edge(content_id, domain_id, {}, rel_type="LINKS_TO")
    
    return new_count, skipped_count


def get_stats(graph: Graph) -> dict:
    """Get graph statistics."""
    try:
        # Count nodes by label
        nodes = graph.query("MATCH (n) RETURN labels(n) as label, count(n) as count")
        
        # Count relationships
        rels = graph.query("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        
        return {
            "nodes": nodes,
            "relationships": rels
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Ingest X.com data into graph DB")
    parser.add_argument("--likes", "-l", type=str, help="Path to likes JSON file")
    parser.add_argument("--bookmarks", "-b", type=str, help="Path to bookmarks JSON file")
    parser.add_argument("--stats", "-s", action="store_true", help="Show graph stats after ingestion")
    parser.add_argument("--skip-existing", "-S", action="store_true", 
                        help="Skip tweets already in database (incremental mode)")
    
    args = parser.parse_args()
    
    if not args.likes and not args.bookmarks:
        parser.error("At least one of --likes or --bookmarks is required")
    
    # Initialize graph
    print(f"Opening graph database: {DB_PATH}")
    graph = Graph(str(DB_PATH))
    
    # Get existing URLs if skip-existing mode
    existing_urls = set()
    if args.skip_existing:
        existing_urls = get_existing_urls(graph)
        print(f"Found {len(existing_urls)} existing tweets in DB (will skip)")
    
    total_new = 0
    total_skipped = 0
    
    if args.likes:
        with open(args.likes) as f:
            likes = json.load(f)
        print(f"Processing {len(likes)} likes...")
        new_count, skipped_count = ingest_tweets(graph, likes, "LIKED", existing_urls)
        print(f"  New: {new_count}, Skipped: {skipped_count}")
        total_new += new_count
        total_skipped += skipped_count
    
    if args.bookmarks:
        with open(args.bookmarks) as f:
            bookmarks = json.load(f)
        print(f"Processing {len(bookmarks)} bookmarks...")
        new_count, skipped_count = ingest_tweets(graph, bookmarks, "BOOKMARKED", existing_urls)
        print(f"  New: {new_count}, Skipped: {skipped_count}")
        total_new += new_count
        total_skipped += skipped_count
    
    print(f"\nTotal: {total_new} new, {total_skipped} skipped")
    
    if args.stats:
        stats = get_stats(graph)
        print("\nGraph Stats:")
        print(json.dumps(stats, indent=2))
    
    # Run a sample query
    print("\nSample query - Top topics:")
    try:
        results = graph.query("""
            MATCH (c:Content)-[:HAS_TOPIC]->(t:Topic)
            RETURN t.name as topic, count(c) as count
            ORDER BY count DESC
            LIMIT 10
        """)
        for r in results:
            print(f"  {r['topic']}: {r['count']}")
    except Exception as e:
        print(f"  Query error: {e}")


if __name__ == "__main__":
    main()
