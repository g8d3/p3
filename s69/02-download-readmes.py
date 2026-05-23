#!/usr/bin/env python3
"""Download all READMEs from raw.githubusercontent.com."""
import json, os, time, urllib.request, urllib.error

REPOS_JSON = "all_384_repos.json"
README_DIR = "readmes_raw"
os.makedirs(README_DIR, exist_ok=True)

with open(REPOS_JSON) as f:
    data = json.load(f)

repos = [(item["full_name"], item["default_branch"]) for item in data["items"]]
total = len(repos)

for i, (full_name, branch) in enumerate(repos):
    safe = full_name.replace("/", "_")
    path = os.path.join(README_DIR, f"{safe}.md")
    if os.path.exists(path) and os.path.getsize(path) > 50:
        print(f"[{i+1}/{total}] SKIP {full_name}")
        continue
    owner, repo = full_name.split("/")
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
    req = urllib.request.Request(url, headers={"User-Agent": "crush-pipeline"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read()
        with open(path, "wb") as f:
            f.write(content)
        print(f"[{i+1}/{total}] OK  {full_name} ({len(content)} bytes)")
    except urllib.error.HTTPError as e:
        # Try main branch
        if branch != "main":
            url2 = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "crush-pipeline"})
            try:
                with urllib.request.urlopen(req2, timeout=15) as r:
                    content = r.read()
                with open(path, "wb") as f:
                    f.write(content)
                print(f"[{i+1}/{total}] OK  {full_name} (main) ({len(content)} bytes)")
            except Exception as e2:
                print(f"[{i+1}/{total}] FAIL {full_name}: {e.status} (main: {e2})")
        else:
            print(f"[{i+1}/{total}] FAIL {full_name}: {e.status}")
    except Exception as e:
        print(f"[{i+1}/{total}] FAIL {full_name}: {e}")
    time.sleep(0.15)

# Summary
downloaded = sum(1 for f in os.listdir(README_DIR) if f.endswith(".md"))
print(f"\nDone! {downloaded}/{total} READMEs downloaded to {README_DIR}/")
