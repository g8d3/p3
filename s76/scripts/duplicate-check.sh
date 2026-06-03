#!/bin/bash
# duplicate-check.sh — Find duplicate files by content hash
# Usage: ./duplicate-check.sh [directory]

SEARCH_DIR="${1:-.}"
echo "Scanning for duplicate files in: $SEARCH_DIR"
echo ""

# Find all regular files, compute SHA256, sort by hash
find "$SEARCH_DIR" -type f -not -path '*/\.*' -exec sha256sum {} \; 2>/dev/null \
  | sort \
  | awk '
BEGIN { prev_hash = ""; prev_file = ""; count = 0 }
{
  hash = $1; file = substr($0, index($0,$2))
  if (hash == prev_hash) {
    if (count == 1) print prev_file
    print file
    count++
  } else {
    if (count > 1) print "---"
    prev_hash = hash
    prev_file = file
    count = 1
  }
}
END { if (count > 1) print "---" }
' \
  | awk '
BEGIN { group=0; first=1 }
{
  if ($0 == "---") { group++; first=1 }
  else {
    if (first) { print ""; print "=== Duplicate group #" (group+1) " ==="; first=0 }
    print "  " $0
  }
}
END { if (group == 0) print "  No duplicates found." }
'
