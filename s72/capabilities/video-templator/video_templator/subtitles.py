"""Subtitle processing: word grouping, timing, and SRT/ASS generation."""

from __future__ import annotations

import math
from typing import List

from .models import SubtitleBlock, Word


def group_words_into_blocks(
    words: List[Word],
    max_words_per_block: int = 6,
    min_duration_ms: float = 1500.0,
    sentence_pause_ms: float = 200.0,
) -> List[SubtitleBlock]:
    """Group words into blocks using **only timing gaps**.

    edge-tts inserts ~875ms gaps at sentence boundaries and ~12ms
    gaps within sentences — so *only* sentence boundaries are
    meaningful break points.

    Strategy:
    1. Split at gaps ≥ ``sentence_pause_ms`` → these are full sentences.
    2. A sentence ≤ ``max_words_per_block`` → kept intact.
    3. A longer sentence → subdivided cleanly: we avoid ending a block
       on dangling prepositions/articles by scanning backward from the
       cut point to find a better last word.

    Parameters are purely about timing — no word lists, no punctuation.
    """
    if not words:
        return []

    # Words that shouldn't end a subtitle block (Spanish)
    _bad_endings = frozenset({
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "de", "del", "en", "por", "para", "con", "sin", "tras",
        "a", "ante", "bajo", "cabe", "contra", "desde",
        "durante", "entre", "hacia", "hasta", "mediante",
        "según", "sobre", "tras", "y", "e", "ni", "que",
        "su", "sus", "tu", "mis", "tus", "nuestros",
    })

    # ── Step 1: split into sentences by timing ──────────────
    sentences: List[List[Word]] = []
    cur: List[Word] = []
    for i, w in enumerate(words):
        cur.append(w)
        if i + 1 < len(words):
            gap = words[i + 1].start_ms - w.end_ms
            if gap >= sentence_pause_ms:
                sentences.append(cur)
                cur = []
    if cur:
        sentences.append(cur)

    # ── Step 2: build blocks ────────────────────────────────
    blocks: List[SubtitleBlock] = []

    for sent in sentences:
        if not sent:
            continue
        if len(sent) <= max_words_per_block:
            blocks.append(_make_block(sent, min_duration_ms))
            continue

        # Long sentence — find clean break points
        start = 0
        while start < len(sent):
            end = min(start + max_words_per_block, len(sent))

            # If this is the last chunk, take everything remaining
            if end >= len(sent):
                blocks.append(_make_block(sent[start:], min_duration_ms))
                break

            # Try to find a good cut within [start, end]
            # Scan backward from end to avoid bad-ending words
            cut = end
            for j in range(end - 1, start, -1):
                word_text = sent[j].text.lower().rstrip(",.;:!?")
                if word_text not in _bad_endings:
                    cut = j + 1  # cut AFTER this word
                    break

            blocks.append(_make_block(sent[start:cut], min_duration_ms))
            start = cut

    # ── Fix overlapping blocks from duration clamping ─────────
    for j in range(1, len(blocks)):
        gap = blocks[j].start_ms - blocks[j - 1].end_ms
        if gap < -10:
            blocks[j] = SubtitleBlock(
                words=blocks[j].words,
                start_ms=blocks[j - 1].end_ms,
                end_ms=blocks[j - 1].end_ms + blocks[j].duration_ms,
            )

    # ── Merge orphans ≤2 words into neighbours ────────────────
    merged: List[SubtitleBlock] = []
    for b in blocks:
        if merged and len(b.words) <= 2:
            merged[-1] = SubtitleBlock(
                words=merged[-1].words + b.words,
                start_ms=merged[-1].start_ms,
                end_ms=b.end_ms,
            )
        else:
            if merged and len(merged[-1].words) <= 2:
                prev = merged.pop()
                merged.append(SubtitleBlock(
                    words=prev.words + b.words,
                    start_ms=prev.start_ms,
                    end_ms=b.end_ms,
                ))
            else:
                merged.append(b)
    if len(merged) >= 2 and len(merged[-1].words) <= 2:
        prev = merged.pop()
        merged[-1] = SubtitleBlock(
            words=merged[-1].words + prev.words,
            start_ms=merged[-1].start_ms,
            end_ms=prev.end_ms,
        )

    return merged


def _make_block(words: List[Word], min_duration_ms: float) -> SubtitleBlock:
    """Create a SubtitleBlock, clamping duration to *min_duration_ms*."""
    start = words[0].start_ms
    end = words[-1].end_ms
    if end - start < min_duration_ms:
        end = start + min_duration_ms
    return SubtitleBlock(words=words, start_ms=start, end_ms=end)


# ---------------------------------------------------------------------------
# SRT generation
# ---------------------------------------------------------------------------

def _ms_to_srt_time(ms: float) -> str:
    """Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
    if ms < 0:
        ms = 0.0
    total_sec = ms / 1000.0
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    mill = int(ms % 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{mill:03d}"


def blocks_to_srt(blocks: List[SubtitleBlock]) -> str:
    """Generate SRT subtitle content from blocks.

    Each block becomes one SRT entry. Empty blocks are skipped.
    """
    lines: List[str] = []
    for i, block in enumerate(blocks, 1):
        if block.duration_ms < 100:
            continue  # skip near-zero duration
        lines.append(str(i))
        lines.append(
            f"{_ms_to_srt_time(block.start_ms)} --> {_ms_to_srt_time(block.end_ms)}"
        )
        lines.append(block.text)
        lines.append("")
    return "\n".join(lines)


def save_srt(blocks: List[SubtitleBlock], path: str) -> str:
    """Generate SRT and write to file. Returns the path."""
    content = blocks_to_srt(blocks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# ASS (Advanced SubStation Alpha) — for word-level highlighting
# ---------------------------------------------------------------------------

def blocks_to_ass(
    blocks: List[SubtitleBlock],
    video_width: int = 1920,
    video_height: int = 1080,
    font_name: str = "sans-serif",
    font_size: int = 46,
    primary_color: str = "&H00FFFFFF",
    secondary_color: str = "&H0000FFFF",
    stroke_color: str = "&H00000000",
    stroke_width: float = 1.5,
    margin_bottom: int = 60,
) -> str:
    """Generate ASS subtitle content with karaoke word highlighting.

    Each word in a block is highlighted (secondary_color) during its
    spoken duration and shown in primary_color otherwise. This gives
    a "current word highlight" effect similar to ReVid / gaming videos.

    Args:
        blocks: Subtitle blocks with word-level timing.
        video_width, video_height: Video resolution.
        font_name: Font family name.
        font_size: Font size in pixels.
        primary_color: ASS colour for non-active words.
        secondary_color: ASS colour for the currently spoken word.
        stroke_color: Outline colour.
        stroke_width: Outline width.
        margin_bottom: Bottom margin in pixels.

    Returns:
        ASS file content as string.
    """
    from textwrap import dedent

    def ass_time(ms: float) -> str:
        total_sec = max(0.0, ms / 1000.0)
        h = int(total_sec // 3600)
        m = int((total_sec % 3600) // 60)
        s = int(total_sec % 60)
        cs = int((total_sec % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def escape_ass(text: str) -> str:
        return text.replace("{", "\\{").replace("}", "\\}")

    # ── Header ────────────────────────────────────────────────
    header = dedent(f"""\
        [Script Info]
        ScriptType: v4.00+
        PlayResX: {video_width}
        PlayResY: {video_height}
        WrapStyle: 0

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{stroke_color},&H00000000,0,0,0,0,100,100,0,0,1,{stroke_width:.1f},0,2,10,10,{margin_bottom},1

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """)

    # ── Events ────────────────────────────────────────────────
    events: List[str] = []

    for block in blocks:
        if not block.words:
            continue

        start_t = ass_time(block.start_ms)
        end_t = ass_time(block.end_ms)

        # Build karaoke line: each word has \K duration (centiseconds)
        # Words before the current stay in primary, current word uses \K which
        # highlights in secondary colour, words after also in primary.
        ass_text_parts: List[str] = []
        for w in block.words:
            word_duration_cs = max(1, int(round((w.end_ms - w.start_ms) / 10)))
            escaped = escape_ass(w.text)
            # Using \K (karaoke) — during the word's duration it shows in secondary colour.
            # Before and after it shows in primary.
            ass_text_parts.append(f"{{\\K{word_duration_cs}}}{escaped} ")

        ass_line = "".join(ass_text_parts).strip()
        events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{ass_line}")

    return header + "\n".join(events)


def save_ass(
    blocks: List[SubtitleBlock],
    path: str,
    video_width: int = 1920,
    video_height: int = 1080,
    font_name: str = "sans-serif",
    font_size: int = 46,
    primary_color: str = "&H00FFFFFF",
    secondary_color: str = "&H0000FFFF",
    stroke_color: str = "&H00000000",
    stroke_width: float = 1.5,
    margin_bottom: int = 60,
) -> str:
    """Generate ASS with karaoke and write to file. Returns the path."""
    content = blocks_to_ass(
        blocks,
        video_width=video_width,
        video_height=video_height,
        font_name=font_name,
        font_size=font_size,
        primary_color=primary_color,
        secondary_color=secondary_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        margin_bottom=margin_bottom,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
