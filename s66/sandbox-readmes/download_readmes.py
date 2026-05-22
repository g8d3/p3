#!/usr/bin/env python3
"""Download READMEs from all 30 repos."""
import json
import os
import urllib.request
import time

with open("search_results.json") as f:
    data = json.load(f)

repos = [item["full_name"] for item in data["items"]]
dest = "readmes"
os.makedirs(dest, exist_ok=True)

for i, repo in enumerate(repos):
    safe_name = repo.replace("/", "_")
    path = f"{dest}/{safe_name}.md"
    if os.path.exists(path):
        print(f"[{i+1}/30] SKIP {repo} (exists)")
        continue
    url = f"https://api.github.com/repos/{repo}/readme"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3.raw"})
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read().decode("utf-8")
        with open(path, "w") as f:
            f.write(content)
        print(f"[{i+1}/30] OK {repo} ({len(content)} bytes)")
    except Exception as e:
        print(f"[{i+1}/30] FAIL {repo}: {e}")
    time.sleep(0.3)  # rate limiting

print("\nDone!")
