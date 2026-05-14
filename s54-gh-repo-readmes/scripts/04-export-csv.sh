#!/usr/bin/env bash
# 04-export-csv.sh — Convert NDJSON scrape output → CSV
# Usage: ./04-export-csv.sh [input.ndjson] [output.csv]
#   Default: gh_results.ndjson → gh_search_results.csv

set -euo pipefail
cd "$(dirname "$0")/.."

INPUT="${1:-gh_results.ndjson}"
OUTPUT="${2:-gh_search_results.csv}"

if [[ ! -f "$INPUT" ]]; then
  echo "✗ Input not found: $INPUT"
  echo "  Run 01-scrape first or specify a .ndjson file"
  exit 1
fi

echo "→ Converting $INPUT → $OUTPUT ..."

python3 << PYEOF
import json, csv, sys

input_file = "$INPUT"
output_file = "$OUTPUT"

all_repos = []
with open(input_file) as f:
    for line in f:
        try:
            d = json.loads(line)
            if isinstance(d, str):
                d = json.loads(d)
        except json.JSONDecodeError:
            continue
        repos = d.get('repos', d if isinstance(d, list) else [])
        if isinstance(repos, list):
            all_repos.extend(repos)

if not all_repos:
    print("  ✗ No repos found")
    sys.exit(1)

fields = ['name', 'stars', 'language', 'topics', 'description', 'last_updated', 'readme']
with open(output_file, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in all_repos:
        w.writerow(r)

print(f"  ✓ {len(all_repos)} repos exported")
print(f"  File: {output_file} ({os.path.getsize(output_file):,} bytes)")
PYEOF
