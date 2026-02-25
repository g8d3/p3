#!/usr/bin/env python3
"""
Integration test for sync.py

Tests: CDP input → scrolling → graph DB output

================================================================================
HOW THE TEST WORKS
================================================================================

Two-phase process (non-blocking for interactive use):

PHASE 1: BASELINE
    $ python test_sync.py --baseline

    - Captures current DB state to test_baseline.json
    - Records: counts, samples by type (liked/bookmarked), newest per type
    - Outputs path to baseline file

PHASE 2: VERIFY (after user action)
    $ python test_sync.py --verify

    - Reads test_baseline.json
    - Captures current DB state
    - Compares before/after
    - Reports: new likes, new bookmarks, any issues

INTERACTIVE TEST FLOW:
    1. AI runs: python test_sync.py --baseline
    2. AI tells user: "Like AND bookmark 20+ new tweets"
    3. User does it, says "done"
    4. AI runs: python sync.py (the actual sync)
    5. AI runs: python test_sync.py --verify
    6. AI reports results

WHAT IT VALIDATES:
    - CDP connection (browser control)
    - Scrolling (needs 20+ to trigger multiple scroll cycles)
    - JS extraction (tweet data from DOM)
    - DB ingestion (nodes/edges created)
    - Incremental sync (detects new vs existing)

BASELINE FORMAT (test_baseline.json):
    {
      "timestamp": "2026-02-24T15:10:00",
      "db_path": "...",
      "total_urls": 439,
      "stats": {
        "nodes": {"Person": 278, "Content": 439, ...},
        "relationships": {"LIKED": 312, "BOOKMARKED": 127, ...}
      },
      "samples": {
        "liked": {
          "top_5": [...],      // 5 most recent likes
          "bottom_5": [...],   // 5 oldest likes
          "newest": "..."      // Single newest liked URL
        },
        "bookmarked": {
          "top_5": [...],
          "bottom_5": [...],
          "newest": "..."
        }
      }
    }

DEBUGGING FAILED TESTS:
    - Check if samples.liked.newest still exists → nothing was deleted
    - Check if new URLs appear after samples.liked.newest → new likes captured
    - Check samples.liked.top_5 matches → order preserved
    - Same logic for bookmarks

================================================================================
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Try to import graphqlite
try:
    from graphqlite import Graph
    HAS_GRAPHQLITE = True
except ImportError:
    HAS_GRAPHQLITE = False

# Paths
SCRIPT_DIR = Path(__file__).parent
DEFAULT_DB = SCRIPT_DIR.parent / "data" / "curation.db"
DEFAULT_CDP = "localhost:9222"
BASELINE_FILE = SCRIPT_DIR / "test_baseline.json"


# ============== DB QUERIES ==============

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


def get_urls_by_relationship(graph: Graph, rel_type: str) -> list[str]:
    """Get URLs for a specific relationship type, ordered by engagement timestamp."""
    query = f'''
        MATCH (p:Person {{id: "@novaisabuilder"}})-[r:{rel_type}]->(c:Content)
        RETURN c.url as url, r.timestamp as ts
        ORDER BY ts DESC
    '''
    try:
        results = graph.query(query)
        return [r['url'] for r in results if r.get('url')]
    except:
        return []


def get_all_urls(graph: Graph) -> set[str]:
    """Get all content URLs."""
    try:
        results = graph.query('MATCH (c:Content) RETURN c.url as url')
        return {r['url'] for r in results if r.get('url')}
    except:
        return set()


def capture_baseline(graph: Graph) -> dict:
    """Capture current DB state for comparison."""
    stats = get_stats(graph)
    
    liked_urls = get_urls_by_relationship(graph, "LIKED")
    bookmarked_urls = get_urls_by_relationship(graph, "BOOKMARKED")
    
    baseline = {
        "timestamp": datetime.now().isoformat(),
        "db_path": str(DEFAULT_DB),
        "total_urls": len(get_all_urls(graph)),
        "stats": stats,
        "samples": {
            "liked": {
                "top_5": liked_urls[:5],
                "bottom_5": liked_urls[-5:] if len(liked_urls) >= 5 else liked_urls,
                "newest": liked_urls[0] if liked_urls else None,
                "count": len(liked_urls)
            },
            "bookmarked": {
                "top_5": bookmarked_urls[:5],
                "bottom_5": bookmarked_urls[-5:] if len(bookmarked_urls) >= 5 else bookmarked_urls,
                "newest": bookmarked_urls[0] if bookmarked_urls else None,
                "count": len(bookmarked_urls)
            }
        }
    }
    
    return baseline


def verify_against_baseline(graph: Graph, baseline: dict) -> dict:
    """Compare current state against baseline."""
    current = capture_baseline(graph)
    
    before = baseline["samples"]
    after = current["samples"]
    
    # Get current URLs to check if old ones still exist
    current_liked_urls = set(get_urls_by_relationship(graph, "LIKED"))
    current_bookmarked_urls = set(get_urls_by_relationship(graph, "BOOKMARKED"))
    
    # Check if old top_5 URLs still exist (not if they're still at the top)
    old_liked_top_5_exist = all(url in current_liked_urls for url in before["liked"]["top_5"])
    old_bookmarked_top_5_exist = all(url in current_bookmarked_urls for url in before["bookmarked"]["top_5"])
    
    results = {
        "baseline_timestamp": baseline["timestamp"],
        "verify_timestamp": current["timestamp"],
        "liked": {
            "before": before["liked"]["count"],
            "after": after["liked"]["count"],
            "new_count": after["liked"]["count"] - before["liked"]["count"],
            "newest_before": before["liked"]["newest"],
            "newest_after": after["liked"]["newest"],
            "old_top_5_exist": old_liked_top_5_exist
        },
        "bookmarked": {
            "before": before["bookmarked"]["count"],
            "after": after["bookmarked"]["count"],
            "new_count": after["bookmarked"]["count"] - before["bookmarked"]["count"],
            "newest_before": before["bookmarked"]["newest"],
            "newest_after": after["bookmarked"]["newest"],
            "old_top_5_exist": old_bookmarked_top_5_exist
        },
        "total_urls": {
            "before": baseline["total_urls"],
            "after": current["total_urls"],
            "new_count": current["total_urls"] - baseline["total_urls"]
        },
        "issues": []
    }
    
    # Check for issues
    if results["liked"]["new_count"] < 0:
        results["issues"].append(f"Likes DECREASED by {abs(results['liked']['new_count'])}")
    if results["bookmarked"]["new_count"] < 0:
        results["issues"].append(f"Bookmarks DECREASED by {abs(results['bookmarked']['new_count'])}")
    if not results["liked"]["old_top_5_exist"]:
        results["issues"].append("Some old liked tweets are missing (possible data loss)")
    if not results["bookmarked"]["old_top_5_exist"]:
        results["issues"].append("Some old bookmarked tweets are missing (possible data loss)")
    
    return results


def print_results(results: dict):
    """Print verification results."""
    print("\n" + "=" * 50)
    print("VERIFICATION RESULTS")
    print("=" * 50)
    
    print(f"\nBaseline: {results['baseline_timestamp']}")
    print(f"Verify:   {results['verify_timestamp']}")
    
    print("\n--- LIKES ---")
    liked = results["liked"]
    print(f"Before:         {liked['before']}")
    print(f"After:          {liked['after']}")
    print(f"New:            {liked['new_count']}")
    print(f"Old top 5 OK:   {'Yes' if liked['old_top_5_exist'] else 'NO!'}")
    
    print("\n--- BOOKMARKS ---")
    bookmarked = results["bookmarked"]
    print(f"Before:         {bookmarked['before']}")
    print(f"After:          {bookmarked['after']}")
    print(f"New:            {bookmarked['new_count']}")
    print(f"Old top 5 OK:   {'Yes' if bookmarked['old_top_5_exist'] else 'NO!'}")
    
    print("\n--- TOTAL ---")
    total = results["total_urls"]
    print(f"URLs:      {total['before']} → {total['after']} (+{total['new_count']})")
    
    if results["issues"]:
        print("\n⚠ ISSUES FOUND:")
        for issue in results["issues"]:
            print(f"  - {issue}")
        return False
    else:
        print("\n✓ No issues detected")
        return True


# ============== CLI ==============

def cmd_baseline():
    """Capture baseline state."""
    if not HAS_GRAPHQLITE:
        print("Error: graphqlite not installed. Run: pip install graphqlite")
        return 1
    
    graph = Graph(str(DEFAULT_DB))
    
    print("Capturing baseline state...")
    baseline = capture_baseline(graph)
    
    with open(BASELINE_FILE, 'w') as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\nBaseline saved to: {BASELINE_FILE}")
    print(f"  Liked:      {baseline['samples']['liked']['count']}")
    print(f"  Bookmarked: {baseline['samples']['bookmarked']['count']}")
    print(f"  Total URLs: {baseline['total_urls']}")
    
    return 0


def cmd_verify():
    """Verify against baseline."""
    if not HAS_GRAPHQLITE:
        print("Error: graphqlite not installed. Run: pip install graphqlite")
        return 1
    
    if not BASELINE_FILE.exists():
        print(f"Error: Baseline file not found: {BASELINE_FILE}")
        print("Run: python test_sync.py --baseline")
        return 1
    
    with open(BASELINE_FILE, 'r') as f:
        baseline = json.load(f)
    
    graph = Graph(str(DEFAULT_DB))
    
    print("Verifying against baseline...")
    results = verify_against_baseline(graph, baseline)
    
    ok = print_results(results)
    
    # Return exit code based on results
    if results["issues"]:
        return 1
    
    return 0


def cmd_interactive():
    """Run interactive test (legacy mode)."""
    if not HAS_GRAPHQLITE:
        print("Error: graphqlite not installed. Run: pip install graphqlite")
        return 1
    
    print("=== SYNC.PY INTERACTIVE TEST ===\n")
    print("This mode is deprecated. Use --baseline and --verify instead.")
    print("\nNew workflow:")
    print("  1. python test_sync.py --baseline")
    print("  2. (like/bookmark 20+ tweets)")
    print("  3. python sync.py")
    print("  4. python test_sync.py --verify")
    
    return 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integration test for sync.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_sync.py --baseline    # Capture current state
    python test_sync.py --verify      # Compare against baseline
        """
    )
    
    parser.add_argument("--baseline", action="store_true",
                        help="Capture current DB state to baseline file")
    parser.add_argument("--verify", action="store_true",
                        help="Verify current state against baseline")
    
    args = parser.parse_args()
    
    if args.baseline:
        return cmd_baseline()
    elif args.verify:
        return cmd_verify()
    else:
        return cmd_interactive()


if __name__ == "__main__":
    sys.exit(main())
