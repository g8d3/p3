#!/usr/bin/env python3
"""Fetch all repos from GitHub API search (paginated)."""
import json, os, time, urllib.request, urllib.error

QUERY = "ai+agent+language:Rust+language:go+language:C%2B%2B+language:zig+language:c+stars:>100+pushed:>2026-01-01"
PER_PAGE = 100
OUT = "all_384_repos.json"
RAW_README_DIR = "readmes_raw"

os.makedirs(RAW_README_DIR, exist_ok=True)

all_items = []
page = 1
while True:
    url = f"https://api.github.com/search/repositories?q={QUERY}&per_page={PER_PAGE}&page={page}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "crush-pipeline"})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP error on page {page}: {e}")
        break
    items = data.get("items", [])
    if not items:
        break
    all_items.extend(items)
    print(f"Page {page}: {len(items)} repos (total: {len(all_items)})")
    if len(all_items) >= data.get("total_count", 0):
        break
    page += 1
    time.sleep(1.2)

# Save full results
result = {"total_count": len(all_items), "incomplete_results": False, "items": all_items}
with open(OUT, "w") as f:
    json.dump(result, f, indent=2)
print(f"\nSaved {len(all_items)} repos to {OUT}")
