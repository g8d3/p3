#!/usr/bin/env bash
# 02-fetch-readmes.sh — Download READMEs for repos in a CSV/NDJSON
# Usage: ./02-fetch-readmes.sh [input.ndjson|input.csv] [--top N]
#   --top N   Only fetch first N repos (default: all)
#
# Output:  repo_readmes/ directory with .md files
#          Updates CSV readme column (first 500 chars)
#          Saves full README to repo_readmes/{owner}_{repo}.md

set -euo pipefail
cd "$(dirname "$0")/.."

INPUT="${1:-gh_results.ndjson}"
TOP="${2:-}"  # e.g. --top 50

# Determine input format and convert to CSV
if [[ "$INPUT" == *.ndjson ]]; then
  echo "→ Converting NDJSON → CSV ..."
  python3 -c "
import json, csv
rows = []
with open('$INPUT') as f:
    for line in f:
        d = json.loads(line)
        for r in d.get('repos', []):
            rows.append(r)
with open('/tmp/gh_fetch_input.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['name','description','topics','stars','language','updated','readme'])
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k,'') for k in ['name','description','topics','stars','language','updated','readme']})
print(f'  {len(rows)} repos')
"
  INPUT_CSV='/tmp/gh_fetch_input.csv'
elif [[ "$INPUT" == *.csv ]]; then
  INPUT_CSV="$INPUT"
else
  echo "Usage: $0 <file.ndjson|file.csv> [--top N]"
  exit 1
fi

# Handle --top argument
if [[ "${2:-}" == "--top" ]]; then
  TOP="${3:-}"
fi

README_DIR="repo_readmes"
mkdir -p "$README_DIR"

echo "→ Fetching READMEs ..."
python3 << 'PYEOF'
import csv, os, urllib.request, urllib.error, time, sys

input_csv = '/tmp/gh_fetch_input.csv'
top_n = os.environ.get('TOP', '')
top_n = int(top_n) if top_n.isdigit() else 0

# Read CSV
rows = []
with open(input_csv) as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

if top_n:
    rows = rows[:top_n]

readme_dir = 'repo_readmes'
os.makedirs(readme_dir, exist_ok=True)

ok, total = 0, len(rows)
for i, r in enumerate(rows, 1):
    name = r['name']
    owner, repo = name.split('/')
    safe = name.replace('/', '_')
    filepath = f"{readme_dir}/{safe}.md"

    # Skip if already exists
    if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
        with open(filepath) as f:
            content = f.read()
        r['readme'] = content[:500].replace('\n', ' ').replace('\r', ' ').strip()
        ok += 1
        print(f"  [{i}/{total}] {name} (cached)")
        continue

    content = None
    for branch in ['main', 'master']:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            content = resp.read().decode('utf-8', errors='replace')
            break
        except urllib.error.HTTPError as e:
            if e.code == 404: continue
            elif e.code == 403:
                print(f"  [{i}/{total}] {name}: rate limited, sleeping 60s...")
                time.sleep(60)
                continue
            else:
                print(f"  [{i}/{total}] {name}: HTTP {e.code}")
                break
        except Exception as e:
            print(f"  [{i}/{total}] {name}: {e}")
            break

    if content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        r['readme'] = content[:500].replace('\n', ' ').replace('\r', ' ').strip()
        ok += 1
        print(f"  [{i}/{total}] {name} ✓")
    else:
        print(f"  [{i}/{total}] {name} ✗ no README")

    time.sleep(0.3)

# Save updated CSV
updated_csv = input_csv.replace('/tmp/', '/tmp/gh_fetch_updated_')
with open(updated_csv, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['name','description','topics','stars','language','updated','readme'])
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k,'') for k in ['name','description','topics','stars','language','updated','readme']})

print(f"\n✓ Downloaded {ok}/{total} READMEs to {readme_dir}/")
PYEOF

# If the input was the main CSV, update its readme column
if [[ "$INPUT_CSV" == *gh_search_results.csv ]]; then
  echo "→ Updating main CSV readme column ..."
  python3 -c "
import csv
rows = []
with open('/tmp/gh_fetch_updated_.csv') as f:
    reader = csv.DictReader(f)
    readme_map = {r['name']: r['readme'] for r in reader}
with open('gh_search_results.csv') as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    for r in reader:
        if r['name'] in readme_map and readme_map[r['name']]:
            r['readme'] = readme_map[r['name']]
        rows.append(r)
with open('gh_search_results.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print('  CSV updated')
"
fi

rm -f /tmp/gh_fetch_input.csv /tmp/gh_fetch_updated_.csv
