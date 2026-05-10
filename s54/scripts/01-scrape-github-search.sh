#!/usr/bin/env bash
# 01-scrape-github-search.sh — Scrape GitHub search results via browser
# Usage: ./01-scrape-github-search.sh <search-url-or-query>
#   Default: searches AI agent repos (Rust + Go, stars>100, pushed since 2026)
#
# Requires: agent-browser, Chrome, Xvfb, jq (optional)
# Output:   gh_results.json (NDJSON: one {page, count, repos} per line)

set -euo pipefail
cd "$(dirname "$0")/.."
SCRIPTS_DIR="$(dirname "$0")"
source "$SCRIPTS_DIR/lib/browser.sh"

SEARCH_URL="${1:-}"
DEFAULT_QUERY="Ai+agent+stars%3A%3E100+pushed%3A%3E2026-01-01++language%3ARust+language%3Ago"
if [[ -z "$SEARCH_URL" ]]; then
  SEARCH_URL="https://github.com/search?q=${DEFAULT_QUERY}&type=repositories&s=stars&o=desc"
fi

RESULTS_FILE="${RESULTS_FILE:-gh_results.ndjson}"
rm -f "$RESULTS_FILE"

# --- Start browser ---
browser_start
browser_connect

# --- Navigate to search ---
echo "→ Navigating to search URL ..."
agent-browser open "$SEARCH_URL" 2>/dev/null
agent-browser wait --load networkidle 2>/dev/null
sleep 2

# --- Get total pages ---
echo "→ Getting pagination info ..."
TOTAL_PAGES=$(agent-browser eval "
(() => {
  const nav = document.querySelector('nav[aria-label=Pagination]');
  if (!nav) return '1';
  const links = nav.querySelectorAll('a');
  const nums = Array.from(links).map(a => parseInt(a.textContent.trim())).filter(n => !isNaN(n));
  return String(Math.max(...nums, 1));
})()
" 2>/dev/null)
echo "→ Found $TOTAL_PAGES pages"

# --- Extract JS ---
EXTRACTOR_JS=$(cat "$SCRIPTS_DIR/lib/extractor.js")

# --- Page 1 ---
echo "--- Page 1/$TOTAL_PAGES ---"
agent-browser eval "$EXTRACTOR_JS" 2>/dev/null > /tmp/gh_page_tmp.json
python3 -c "
import json
with open('/tmp/gh_page_tmp.json') as f:
    inner = json.loads(f.read().strip())
data = json.loads(inner)
with open('$RESULTS_FILE', 'a') as f:
    f.write(json.dumps({'page':1,'count':len(data),'repos':data}) + '\n')
print(f'  OK: {len(data)} repos')
" || { echo "  ERROR on page 1"; browser_stop; exit 1; }

# --- Pages 2..N ---
BASE_URL="${SEARCH_URL%%&p=*}"
[[ "$BASE_URL" != *"?"* ]] && BASE_URL="${BASE_URL}?"  # ensure query params work

for page in $(seq 2 "$TOTAL_PAGES"); do
  PAGE_URL="${BASE_URL}&p=${page}"
  echo "--- Page $page/$TOTAL_PAGES ---"
  agent-browser open "$PAGE_URL" 2>/dev/null
  agent-browser wait --load networkidle 2>/dev/null
  sleep 1

  agent-browser eval "$EXTRACTOR_JS" 2>/dev/null > /tmp/gh_page_tmp.json
  python3 -c "
import json
with open('/tmp/gh_page_tmp.json') as f:
    inner = json.loads(f.read().strip())
data = json.loads(inner)
with open('$RESULTS_FILE', 'a') as f:
    f.write(json.dumps({'page':$page,'count':len(data),'repos':data}) + '\n')
print(f'  OK: {len(data)} repos')
" || { echo "  ERROR on page $page"; browser_stop; exit 1; }
done

# --- Done ---
browser_stop

# Show stats
python3 -c "
import json
total = 0
with open('$RESULTS_FILE') as f:
    for line in f:
        d = json.loads(line)
        total += d['count']
        pages = d.get('page',0)
print(f'✓ Done: {total} repos across {pages} pages')
print(f'  File: $RESULTS_FILE')
" 2>/dev/null || echo "✓ Done (see $RESULTS_FILE)"
