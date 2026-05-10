#!/usr/bin/env bash
# pipeline.sh — Full pipeline: scrape → readmes → classify → export → serve
# Usage: ./pipeline.sh [search-url]
#
# Each step is optional — set SKIP=1 to skip:
#   SKIP_SCRAPE=1 SKIP_README=1 SKIP_CLASSIFY=1 SKIP_EXPORT=1 SKIP_SERVE=1
#
# Example (skip browser, use existing data):
#   SKIP_SCRAPE=1 ./pipeline.sh

set -euo pipefail
cd "$(dirname "$0")/.."

SEARCH_URL="${1:-}"
START=$(date +%s)
STEP=0

step() {
  STEP=$((STEP+1))
  echo ""
  echo "══════════════════════════════════════════════════════"
  echo "  STEP $STEP: $1"
  echo "══════════════════════════════════════════════════════"
}

# ── Step 1: Scrape ──
if [[ -z "${SKIP_SCRAPE:-}" ]]; then
  step "Scraping GitHub search results"
  bash scripts/01-scrape-github-search.sh "$SEARCH_URL"
else
  echo "→ SKIP_SCRAPE set, using existing gh_results.ndjson"
fi

# ── Step 2: Fetch READMEs ──
if [[ -z "${SKIP_README:-}" ]]; then
  step "Fetching READMEs (top 50)"
  bash scripts/02-fetch-readmes.sh gh_results.ndjson --top 50
else
  echo "→ SKIP_README set"
fi

# ── Step 3: Export CSV ──
if [[ -z "${SKIP_EXPORT:-}" ]]; then
  step "Exporting NDJSON → CSV"
  bash scripts/04-export-csv.sh
else
  echo "→ SKIP_EXPORT set"
fi

# ── Step 4: Classify ──
if [[ -z "${SKIP_CLASSIFY:-}" ]]; then
  step "Classifying repos"
  bash scripts/03-classify.sh
else
  echo "→ SKIP_CLASSIFY set"
fi

# ── Step 5: Serve ──
if [[ -z "${SKIP_SERVE:-}" ]]; then
  step "Starting servers"
  bash scripts/05-serve.sh
else
  echo "→ SKIP_SERVE set"
fi

ELAPSED=$(( $(date +%s) - START ))
echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✓ Pipeline complete in ${ELAPSED}s"
echo "══════════════════════════════════════════════════════"
echo "  Files:"
ls -lh gh_results.ndjson gh_search_results.csv repo_readmes/ 2>/dev/null | awk '{print "    " $NF " (" $5 ")"}'
echo ""
echo "  Servers:"
echo "    Review page: http://localhost:9090/review.html"
echo "    D-Tale:      http://localhost:8080"
