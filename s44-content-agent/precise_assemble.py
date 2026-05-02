#!/usr/bin/env python3
"""
Precise Video Assembly — measures actual TTS timing for perfect subtitle/SFX sync.
Fixes: subtitle drift, SFX misalignment, visual-audio mismatch.
"""

import sys
import os
import json
import subprocess
import tempfile as _tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = Path(__file__).parent / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

from pipeline.tts import generate_speech
from pipeline.sfx import get_sfx_map
from pipeline.assemble import VideoAssembler


def ffprobe_duration(path: str) -> float:
    """Get exact audio duration in seconds."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30
    )
    return float(r.stdout.strip())


def fmt_time(secs: float) -> str:
    """Format seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    cs = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{cs:03d}"


def run():
    print("=" * 60)
    print("  PRECISE ASSEMBLY — Exact Timing Mode")
    print("=" * 60)

    script_path = "tmp/openmontage_script.txt"
    paragraphs = [l.strip() for l in open(script_path).readlines() if l.strip()]
    print(f"\n  Script: {len(paragraphs)} paragraphs, {sum(len(p.split()) for p in paragraphs)} words")

    # ── Stage 1: Generate TTS per paragraph, measure exact durations ──────
    print("\n[1/4] Generating TTS with precise timing...")
    segments = []
    total_duration = 0.0
    gap = 0.3  # silence between paragraphs

    for i, para in enumerate(paragraphs):
        seg_path = str(TMP / f"para_{i:02d}.wav")
        generate_speech(para, backend="kokoro", voice="af_heart",
                        speed=1.0, output_path=seg_path)
        dur = ffprobe_duration(seg_path)

        start = total_duration + (gap if i > 0 else 0)
        end = start + dur
        total_duration = end

        segments.append({
            "index": i,
            "text": para,
            "path": seg_path,
            "start": start + (0 if i == 0 else gap),
            "end": end,
            "duration": dur,
        })
        words = len(para.split())
        print(f"    P{i+1}: {start:.1f}s→{end:.1f}s ({dur:.1f}s, {words}w, {words/dur:.1f} wps)")

    narration_duration = total_duration + 1.5  # +outro silence
    print(f"  Total narration: {narration_duration:.1f}s")

    # ── Stage 2: Concatenate all segments into one voiceover ──────────────
    print("\n[2/4] Concatenating voiceover...")
    concat_file = str(TMP / "voiceover_concat.txt")
    with open(concat_file, "w") as f:
        for s in segments:
            f.write(f"file '{s['path']}'\n")

    voiceover_path = str(TMP / "precise_voiceover.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy", voiceover_path,
    ], capture_output=True, timeout=60)

    # pad end with 1.5s silence
    padded_voiceover = str(TMP / "precise_voiceover_padded.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", voiceover_path,
        "-af", "apad=pad_dur=1.5",
        padded_voiceover,
    ], capture_output=True, timeout=60)

    # ── Stage 3: Generate EXACT subtitles from measured timing ────────────
    print("\n[3/4] Generating exact subtitles...")
    srt_lines = []
    for i, s in enumerate(segments, 1):
        srt_lines.append(str(i))
        srt_lines.append(f"{fmt_time(s['start'])} --> {fmt_time(s['end'])}")
        srt_lines.append(s['text'])
        srt_lines.append("")

    srt_path = str(TMP / "precise_subtitles.srt")
    with open(srt_path, "w") as f:
        f.write("\n".join(srt_lines))
    print(f"  ✓ {len(segments)} subtitle entries, exact timing")

    # ── Calculate exact SFX positions ─────────────────────────────────────
    sfx_map = get_sfx_map()
    # Map SFX to specific paragraphs:
    sfx_plan = [
        (0, "impact",    "Hook — first sentence lands"),          # 0.0s
        (1, "whoosh",    "Transition to explanation"),             # after para 1
        (2, "stinger",   "Mind blown moment"),                     # para 3 start
        (3, "swoosh",    "Transition to 'the bad'"),               # after para 3
        (4, "boing",     "Plot twist — sixty nine cents"),         # para 5 start
        (4, "laugh",     "Laugh at sad sandwich line"),            # mid para 5
        (5, "impact",    "Verdict"),                               # para 6 start
        (6, "swoosh",    "Transition to CTA"),                     # para 7 start
    ]

    sfx_timing = []
    for para_idx, sfx_name, desc in sfx_plan:
        if para_idx < len(segments):
            seg = segments[para_idx]
            sfx_path = sfx_map.get(sfx_name, "")
            if sfx_path and Path(sfx_path).exists():
                # Place SFX at 0.5s into the paragraph (or adjust based on type)
                offset = 0.3 if sfx_name in ("whoosh", "swoosh") else 0.5
                ts = seg["start"] + offset
                sfx_timing.append((ts, sfx_path))
                print(f"    ✓ {sfx_name} @ {ts:.1f}s ({desc})")

    # ── Stage 4: Assemble final video ────────────────────────────────────
    print("\n[4/4] Assembling final video...")
    assembler = VideoAssembler()

    # Pick music track (must be longer than narration)
    # 117s narration → use 120s track
    bg_music = "assets/music/bgm_energetic_120s.wav"

    # Find recording
    recordings = sorted(Path("tmp/recording").glob("*.mp4"))
    recording_path = str(recordings[-1]) if recordings else None
    print(f"  Recording: {recording_path}")

    final_path = assembler.assemble(
        recording_path=recording_path,
        narration_path=padded_voiceover,
        output_path=str(TMP / "openmontage_review_precise.mp4"),
        title="OpenMontage Review - Agent V",
        bg_music=bg_music,
        subtitles_path=srt_path,
        sfx_timing=sfx_timing,
        meme_overlays=None,
    )

    size = Path(final_path).stat().st_size
    print(f"\n{'='*60}")
    print(f"  ✅ FINAL VIDEO")
    print(f"  📹 {final_path}")
    print(f"  📏 {narration_duration:.0f}s | {size/1024/1024:.1f} MB")
    print(f"  🎯 Timing: EXACT (measured per-paragraph)")
    print(f"  🔊 SFX: {len(sfx_timing)} cues at precise positions")
    print(f"  📝 Subtitles: {len(segments)} entries, synced to audio")
    print(f"  🎵 Music: {bg_music}")
    print(f"{'='*60}")

    # Save to output
    output_dir = Path("output") / "openmontage-review-precise"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "openmontage_review_precise.mp4"
    import shutil
    shutil.copy(final_path, out_path)
    shutil.copy(srt_path, output_dir / "subtitles.srt")
    print(f"\n  📁 Output also saved to: {out_path}")

    # Print timing report for reference
    print(f"\n  ── Timing Report ──")
    for s in segments:
        print(f"    P{s['index']+1}: {s['start']:.1f}s - {s['end']:.1f}s  "
              f"({s['duration']:.1f}s, {len(s['text'].split())}w)")


if __name__ == "__main__":
    run()
