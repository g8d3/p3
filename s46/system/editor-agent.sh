#!/bin/bash
# ============================================================
# editor-agent.sh — Content Review & Iteration Agent
#
# Reviews generated content for quality and either approves
# it or requests revisions. Can use a different AI model
# (Gemini API) for a second opinion.
#
# Usage:
#   ./editor-agent.sh                              # Review latest post
#   ./editor-agent.sh <file>                       # Review specific post
#   ./editor-agent.sh --all                        # Review all unreviewed posts
#   ./editor-agent.sh --approve <file>             # Mark as approved
#   ./editor-agent.sh --council <file>             # Review with 2 models (fast + deep), compare
#   ./editor-agent.sh --council --all              # Council review all unreviewed
#   ./editor-agent.sh --status                     # Show review status
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTENT_DIR="$PROJECT_DIR/content"
REVIEW_DIR="$CONTENT_DIR/reviews"
POSTS_DIR="$CONTENT_DIR/posts"
TMPDIR="${TMPDIR:-$PROJECT_DIR/tmp}"
mkdir -p "$REVIEW_DIR" "$TMPDIR"

GEMINI_API="${GEMINI_API_KEY:-}"
# Latest models as of April 2026:
#   gemini-3.1-flash-lite-preview — fast, cheap, good for first pass
#   gemini-3.1-pro-preview       — deep analysis, second opinion
#   gemini-3-flash-preview       — middle ground
# Available as of April 2026 (tested working):
#   gemini-3-flash-preview  — latest flash, fast and capable
#   gemini-2.5-flash         — stable, good second opinion
GEMINI_MODEL_FAST="${GEMINI_MODEL_FAST:-gemini-3-flash-preview}"
GEMINI_MODEL_DEEP="${GEMINI_MODEL_DEEP:-gemini-2.5-flash}"

# ─── Review Criteria ───
QUALITY_CRITERIA=(
  "Clarity: Is the post well-structured and easy to follow?"
  "Hook: Does it have a compelling opening that grabs attention?"
  "Substance: Does it provide real insight or value?"
  "Formatting: Is the thread/X format correct (numbered parts, line breaks)?"
  "Length: Is it the right length for the platform? (200-500 words for X threads)"
  "Originality: Does it offer a unique perspective or angle?"
)

# ─── Call Gemini for review ───
gemini_review() {
  local model="$1"
  local content="$2"
  local outfile="$3"  # write response here to avoid bash variable mangling

  local prompt_text="You are a content editor reviewing a post for quality. Score each criterion 1-5.

Post content:
---
${content}
---

Respond in this exact JSON format:
{
  \"scores\": {
    \"clarity\": <1-5>,
    \"hook\": <1-5>,
    \"substance\": <1-5>,
    \"formatting\": <1-5>,
    \"length\": <1-5>,
    \"originality\": <1-5>
  },
  \"verdict\": \"approve|revise|reject\",
  \"summary\": \"<1-2 sentences>\",
  \"feedback\": \"<specific improvement suggestions, or empty if approved>\"
}

Be honest and critical. Only approve if all scores are 3+ and total >= 20."

  # Write prompt safely to temp file and use Python for the API call
  python3 "$PROJECT_DIR/system/_gemini_call.py" "$model" "$prompt_text" "$outfile" 2>/dev/null || {
    # Fallback if Python script doesn't exist — use direct curl
    local tmpf="${outfile}.raw"
    curl -s "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API}" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "
import json
prompt = '''$prompt_text'''
print(json.dumps({'contents': [{'parts': [{'text': prompt}]}]}))
")" > "$tmpf" 2>/dev/null
    python3 -c "
import json, sys
with open('$tmpf') as f:
    data = json.load(f)
try:
    text = data['candidates'][0]['content']['parts'][0]['text'].strip()
    # Extract JSON from the response text
    if '\`\`\`json' in text:
        text = text.split('\`\`\`json')[1].split('\`\`\`')[0].strip()
    elif '\`\`\`' in text:
        text = text.split('\`\`\`')[1].split('\`\`\`')[0].strip()
    result = json.loads(text)
    with open('$outfile', 'w') as out:
        json.dump(result, out, indent=2)
except Exception as e:
    with open('$outfile', 'w') as out:
        json.dump({'error': str(e), 'raw_raw': text[:500] if 'text' in dir() else 'parse failed'}, out)
" 2>/dev/null
  }
}

# ─── Review with a single model ───
review_post() {
  local post_file="$1"
  local model="${2:-$GEMINI_MODEL_FAST}"  # Default to fast model
  local post_name=$(basename "$post_file" .txt)
  local review_file="$REVIEW_DIR/${post_name}.review.$(basename $model).md"

  if [ ! -f "$post_file" ]; then
    echo "File not found: $post_file"
    return 1
  fi

  local content
  content=$(cat "$post_file")

  if [ -n "$GEMINI_API" ]; then
    echo "🧠 Reviewing with ${model}..."
    local raw_file="$TMPDIR/gemini-raw-${post_name}.json"
    mkdir -p "$TMPDIR"
    gemini_review "$model" "$content" "$raw_file"

    # Read the parsed result
    local review_json
    review_json=$(cat "$raw_file" 2>/dev/null || echo '{"error":"file not found"}')

    # Save review with model metadata
    local model_short=$(basename "$model")
    { echo "# Review: ${post_name}"; echo "Date: $(date)"; echo "Model: ${model_short}"; echo ""; } > "$review_file"
    echo '```json' >> "$review_file"
    echo "$review_json" >> "$review_file"
    echo '```' >> "$review_file"

    # Parse verdict
    local verdict
    verdict=$(echo "$review_json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('verdict','unknown'))" 2>/dev/null)

    echo "📝 Review saved to: $review_file"
    echo "🏁 Verdict: ${verdict}"

    # Compute score
    local total_score
    total_score=$(echo "$review_json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
s=d.get('scores',{})
print(sum(s.values()))
" 2>/dev/null)

    echo "📊 Total score: ${total_score:-?}/30"

    # Validate audio file exists and is actually audio (not JSON error)
    local post_basename
    post_basename=$(basename "${post_file%.txt}")
    local found_audio=""
    for ap in "$CONTENT_DIR/audio/${post_basename}.mp3" \
              "$CONTENT_DIR/audio/${post_basename}-inworld.mp3" \
              "$CONTENT_DIR/audio/${post_basename}"*.mp3; do
      if [ -f "$ap" ] && [ "$(file -b "$ap" | grep -cE 'Audio|RIFF|MPEG')" -gt 0 ] 2>/dev/null; then
        found_audio="$ap"
        break
      fi
    done
    if [ -z "$found_audio" ]; then
      echo "⚠️  No valid audio file found for this post"
      # Not a hard reject — just a warning
    else
      local audio_size=$(du -h "$found_audio" 2>/dev/null | cut -f1)
      echo "🎵 Audio: $audio_size ($(basename "$found_audio"))"
    fi

    # Auto-approve ONLY if verdict is explicitly "approve" AND score >= 20
    if [ "$verdict" = "approve" ]; then
      if [ "${total_score:-0}" -ge 20 ] 2>/dev/null; then
        echo "✅ POST APPROVED (score: ${total_score}/30)"
        touch "${post_file}.approved"
      else
        echo "❌ POST REJECTED — low score (${total_score}/30) despite approve verdict"
      fi
    elif [ "$verdict" = "revise" ]; then
      echo "🔄 REVISION REQUESTED — see feedback in review"
    elif [ "$verdict" = "reject" ]; then
      echo "❌ POST REJECTED — see feedback in review"
    else
      echo "❌ POST REJECTED — unknown verdict (${verdict:-none}) — review may need model update"
    fi

  else
    # No Gemini API — do a simple heuristic review
    echo "⚠️  No Gemini API key set. Doing basic heuristic review."

    local word_count
    word_count=$(wc -w < "$post_file")
    local has_hook
    has_hook=$(head -5 "$post_file" | grep -cE '^[0-9]+/' || echo 0)
    local has_thread_format
    has_thread_format=$(grep -cE '^[0-9]+/' "$post_file" || echo 0)

    cat > "$review_file" << EOF
# Review: ${post_name} (basic)
Date: $(date)
Model: heuristic

## Metrics
- Word count: ${word_count} (target: 200-500)
- Thread format: ${has_thread_format} numbered parts
- Hook present: $([ "$has_hook" -gt 0 ] && echo "yes" || echo "no")

## Heuristic Score: $(( word_count > 150 && word_count < 800 ? 1 : 0 ))/1
$([ "$word_count" -gt 100 ] && echo "✅ Length OK" || echo "❌ Too short")

## Verdict
$([ "$word_count" -gt 150 ] && echo "approve (auto)" || echo "revise (too short)")
EOF

    if [ "$word_count" -gt 150 ]; then
      touch "${post_file}.approved"
      echo "✅ Auto-approved (word count: ${word_count})"
    else
      echo "❌ Too short (${word_count} words)"
    fi
    echo "📝 Review saved to: $review_file"
  fi
}

# ─── Council review (2 models, compares results) ───
review_council() {
  local post_file="$1"
  local post_name=$(basename "$post_file" .txt)
  local council_file="$REVIEW_DIR/${post_name}.council.md"

  if [ ! -f "$post_file" ]; then
    echo "File not found: $post_file"
    return 1
  fi

  echo "=== Council Review: ${post_name} ==="
  echo ""

  # Review with fast model
  echo "📋 Phase 1: ${GEMINI_MODEL_FAST} (fast pass)"
  review_post "$post_file" "$GEMINI_MODEL_FAST"
  local fast_review_file="$REVIEW_DIR/${post_name}.review.$(basename $GEMINI_MODEL_FAST).md"

  # Extract fast scores
  local fast_scores fast_verdict fast_total
  fast_verdict=$(grep '"verdict"' "$fast_review_file" 2>/dev/null | cut -d'"' -f4)
  fast_total=$(python3 -c "
import json
d=json.load(open('$fast_review_file'))
s=d.get('scores',{})
print(sum(s.values()))
" 2>/dev/null || echo "?")

  echo ""
  echo "📋 Phase 2: ${GEMINI_MODEL_DEEP} (deep review)"
  review_post "$post_file" "$GEMINI_MODEL_DEEP"
  local deep_review_file="$REVIEW_DIR/${post_name}.review.$(basename $GEMINI_MODEL_DEEP).md"

  # Extract deep scores
  local deep_scores deep_verdict deep_total
  deep_scores=$(grep -A1 '"scores"' "$deep_review_file" 2>/dev/null | tail -1)
  deep_verdict=$(grep '"verdict"' "$deep_review_file" 2>/dev/null | cut -d'"' -f4)
  deep_total=$(python3 -c "
import json
d=json.load(open('$deep_review_file'))
s=d.get('scores',{})
print(sum(s.values()))
" 2>/dev/null || echo "?")

  # Compare
  echo ""
  echo "============ COUNCIL VERDICT ============"
  echo "  ${GEMINI_MODEL_FAST}: ${fast_total}/30 → ${fast_verdict}"
  echo "  ${GEMINI_MODEL_DEEP}: ${deep_total}/30 → ${deep_verdict}"
  echo ""

  local consensus=""
  if [ "$fast_verdict" = "$deep_verdict" ]; then
    consensus="CONSENSUS: ${fast_verdict}"
    echo "  ✅ ${consensus}"
    if [ "$fast_verdict" = "approve" ]; then
      touch "${post_file}.approved"
    fi
  else
    consensus="DISAGREEMENT — fast says ${fast_verdict}, deep says ${deep_verdict}"
    echo "  ⚠️  ${consensus}"
    echo "  → Using deep review as tiebreaker"
    if [ "$deep_verdict" = "approve" ]; then
      touch "${post_file}.approved"
    fi
  fi

  # Write council report
  cat > "$council_file" << EOF
# Council Review: ${post_name}
Date: $(date)
Models: ${GEMINI_MODEL_FAST} + ${GEMINI_MODEL_DEEP}

## Results
| Model | Score | Verdict |
|-------|-------|---------|
| ${GEMINI_MODEL_FAST} | ${fast_total}/30 | ${fast_verdict} |
| ${GEMINI_MODEL_DEEP} | ${deep_total}/30 | ${deep_verdict} |

## Verdict
${consensus}
EOF
  echo ""
  echo "📝 Council report: $council_file"
}

# ─── Status ───
show_status() {
  echo "=== Review Status ==="
  echo ""
  echo "Posts dir: $POSTS_DIR"
  echo "Reviews dir: $REVIEW_DIR"
  echo ""
  for f in "$POSTS_DIR"/*.txt; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .txt)
    approved_val=""
    [ -f "${f}.approved" ] && approved_val="✅ APPROVED" || approved_val="⏳ pending"
    reviewed="❌ unreviewed"
    # Check for any review file (new format: name.review.MODEL.md, old format: name.review.md, council: name.council.md)
    for r in "$REVIEW_DIR/${name}".review.*.md "$REVIEW_DIR/${name}".review.md "$REVIEW_DIR/${name}".council.md; do
      [ -f "$r" ] && { reviewed="📝 reviewed"; break; }
    done
    echo "  ${approved_val} ${reviewed} — ${name}.txt"
  done
}

# ─── Main ───
case "${1:-}" in
  --status)
    show_status
    ;;
  --approve)
    if [ -n "${2:-}" ]; then
      touch "${POSTS_DIR}/${2}.approved"
      echo "✅ Marked approved: $2"
    else
      echo "Usage: $0 --approve <filename>"
    fi
    ;;
  --all)
    for f in "$POSTS_DIR"/*.txt; do
      [ -f "$f" ] || continue
      [ -f "${f}.approved" ] && echo "Skipping (already approved): $(basename $f)" && continue
      echo ""
      echo "=== Reviewing: $(basename $f) with ${GEMINI_MODEL_FAST} ==="
      review_post "$f" "$GEMINI_MODEL_FAST"
    done
    ;;
  --council)
    target="${2:-}"
    if [ -n "$target" ] && [ -f "$target" ]; then
      review_council "$target"
    elif [ -n "$target" ] && [ -f "$POSTS_DIR/$target" ]; then
      review_council "$POSTS_DIR/$target"
    elif [ "$target" = "--all" ] || [ -z "$target" ]; then
      for f in "$POSTS_DIR"/*.txt; do
        [ -f "$f" ] || continue
        echo ""
        echo "=========================================="
        echo " Council Review: $(basename $f)"
        echo "=========================================="
        review_council "$f"
      done
    else
      echo "File not found: $target"
    fi
    ;;
  *)
    target="${1:-}"
    if [ -n "$target" ] && [ -f "$target" ]; then
      review_post "$target"
    elif [ -n "$target" ] && [ -f "$POSTS_DIR/$target" ]; then
      review_post "$POSTS_DIR/$target"
    else
      # Review latest unreviewed post
      latest=""
      for f in $(ls -t "$POSTS_DIR"/*.txt 2>/dev/null); do
        [ -f "${f}.approved" ] || { latest="$f"; break; }
      done
      if [ -n "$latest" ]; then
        echo "Reviewing latest unreviewed post: $(basename $latest)"
        review_post "$latest"
      else
        echo "No unreviewed posts found."
        show_status
      fi
    fi
    ;;
esac
