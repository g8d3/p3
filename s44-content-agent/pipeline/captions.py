"""
Subtitle / Caption Generator
Takes a script with timestamps and produces SRT subtitles.
"""

import re
import math
from pathlib import Path


def parse_script_with_timing(script_path: str,
                              words_per_second: float = 2.8) -> list:
    """
    Parse a script and estimate timing for each segment.
    Returns list of (start_time, end_time, text) tuples.
    
    words_per_second: approximate speech rate (2.8 = normal, 3.5 = fast)
    """
    with open(script_path) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    segments = []
    current_time = 0.0
    pause_between = 0.3  # seconds between paragraphs

    for line in lines:
        word_count = len(line.split())
        duration = word_count / words_per_second
        start = current_time
        end = start + duration
        segments.append((start, end, line))
        current_time = end + pause_between

    return segments


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    millis = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millis:03d}"


def generate_srt(segments: list, output_path: str = None) -> str:
    """
    Generate SRT subtitle content from (start, end, text) segments.
    Returns path to SRT file.
    """
    lines = []
    for i, (start, end, text) in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_srt_time(start)} --> {format_srt_time(end)}")
        lines.append(text)
        lines.append("")

    srt_content = "\n".join(lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(srt_content)
        return output_path

    return srt_content


def generate_subtitles_from_script(script_path: str, output_path: str,
                                    words_per_second: float = 2.8) -> str:
    """Full pipeline: parse script -> estimate timing -> generate SRT."""
    segments = parse_script_with_timing(script_path, words_per_second)
    return generate_srt(segments, output_path)


def calculate_word_timestamps(script_path: str,
                               words_per_second: float = 2.8) -> list:
    """
    Generate word-level timestamps for animated captions.
    Returns list of (word, start_time, end_time).
    """
    segments = parse_script_with_timing(script_path, words_per_second)
    word_timestamps = []

    for seg_start, seg_end, text in segments:
        words = text.split()
        seg_duration = seg_end - seg_start
        word_duration = seg_duration / len(words) if words else 0

        for i, word in enumerate(words):
            ws = seg_start + i * word_duration
            we = ws + word_duration
            word_timestamps.append((word, ws, we))

    return word_timestamps


if __name__ == "__main__":
    # Test with a sample script
    test_file = "/tmp/test_script.txt"
    with open(test_file, "w") as f:
        f.write("Welcome to this software review.\n")
        f.write("Today we're looking at an amazing tool.\n")
        f.write("Let's dive into the features.\n")

    srt_path = generate_subtitles_from_script(test_file, "/tmp/test_captions.srt")
    print(f"Subtitles generated: {srt_path}")
    with open(srt_path) as f:
        print(f.read())
