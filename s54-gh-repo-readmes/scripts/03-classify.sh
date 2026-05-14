#!/usr/bin/env bash
# 03-classify.sh — Classify repos using category patterns
# Usage: ./03-classify.sh <input.csv> [categories.conf]
#   Default: gh_search_results.csv, scripts/lib/categories.conf
#
# Adds column: clasificacion_ia
# Falls back to name-based heuristics for unmatched repos.

set -euo pipefail
cd "$(dirname "$0")/.."
SCRIPTS_DIR="$(dirname "$0")"

INPUT="${1:-gh_search_results.csv}"
CONFIG="${2:-$SCRIPTS_DIR/lib/categories.conf}"

if [[ ! -f "$INPUT" ]]; then
  echo "✗ Input file not found: $INPUT"
  exit 1
fi

echo "→ Loading categories from $CONFIG ..."

# Parse categories.conf into Python-compatible dict
python3 << 'PYEOF'
import csv, re, sys

config_file = 'scripts/lib/categories.conf'
input_csv = 'gh_search_results.csv'

# Parse config
categories = []  # [(name, [patterns...]), ...]
current_cat = None
current_patterns = []

with open(config_file) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('#'):
            continue
        if ':' in line:
            # Save previous category
            if current_cat and current_patterns:
                categories.append((current_cat, current_patterns))
            # Parse new category line
            cat, pat = line.split(':', 1)
            current_cat = cat.strip()
            current_patterns = [pat.strip()]
        elif current_cat and line:
            current_patterns.append(line.strip())

if current_cat and current_patterns:
    categories.append((current_cat, current_patterns))

print(f"  {len(categories)} categories loaded")

# Read CSV
rows = []
with open(input_csv) as f:
    reader = csv.DictReader(f)
    fields = [c for c in reader.fieldnames if c != 'clasificacion_ia'] + ['clasificacion_ia']
    for r in reader:
        r.pop('clasificacion_ia', None)

        description = r.get('description', '')
        topics = r.get('topics', '')
        readme = r.get('readme', '')
        name = r.get('name', '')
        text = f"{description} {topics} {readme}".lower()

        classified = False
        for cat, patterns in categories:
            for p in patterns:
                if re.search(p, text, re.IGNORECASE | re.VERBOSE):
                    r['clasificacion_ia'] = cat
                    classified = True
                    break
            if classified:
                break

        if not classified:
            # Name-based fallback
            nl = name.lower()
            if re.search(r'\bai\s+agent|autonomous|multi.agent|agentic\b', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'AI Agent (General)'
            elif re.search(r'\bcli\b|command.line|terminal', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'CLI / Terminal Tools'
            elif re.search(r'\bmcp\b|toolbox', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'MCP / Tools Protocol'
            elif re.search(r'\bbrowser|web\s+agent', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Browser / Web Automation'
            elif re.search(r'\bdatabase\b|\bsql\b|\bdata\s+(store|base|warehouse|lake)\b', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Database / Data Warehouse'
            elif re.search(r'\bsecurity\b|secret|protect|safe\b', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Security / Pentesting'
            elif re.search(r'\borchestrat|\bworkflow\b', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Agent Orchestration / Workflow'
            elif re.search(r'\brag\b|retrieval|knowledge|memory\b', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Memory / Knowledge / RAG'
            elif re.search(r'\bsdk\b|framework.*agent|toolkit', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Agent DevKit / SDK'
            elif re.search(r'\bdocker\b|kubernetes|k8s\b|container', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Infrastructure / DevOps'
            elif re.search(r'\bnetwork\b|observab|ebpf', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Network Observability'
            elif re.search(r'\bexcel\b|google\s+(workspace|drive)|spreadsheet', description, re.IGNORECASE):
                r['clasificacion_ia'] = 'Office / Productivity'
            elif any(w in nl for w in ['agent', 'ai', 'llm', 'gpt', 'claw']):
                r['clasificacion_ia'] = 'AI Agent (General)'
            else:
                r['clasificacion_ia'] = 'AI Agent (General)'

        rows.append(r)

# Save
with open(input_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

# Stats
from collections import Counter
cats = Counter(r['clasificacion_ia'] for r in rows)
print(f"\nTotal: {len(rows)} repos clasificados en {len(cats)} categorias\n")
for cat, count in cats.most_common():
    print(f"  {count:3d}  {cat}")
PYEOF
