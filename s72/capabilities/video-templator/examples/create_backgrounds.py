"""Create test background videos for the demo renders.

Generates 15-second 1920x1080 background clips that simulate gameplay
footage using ffmpeg (color bars + moving text + geometric shapes).
"""

import subprocess
import sys
import shutil

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def create_bg_video(
    output: str,
    duration: int = 15,
    color: str = "0x2D3748",
    accent: str = "0x4A5568",
    text: str = "GAMEPLAY FOOTAGE",
):
    """Create a test background video with smooth motion."""
    filter_graph = (
        f"color=c={color}:s=1920x1080:d={duration}:r=30[bg];"
        f"color=c={accent}:s=400x300:d={duration}:r=30[box];"
        f"[bg][box]overlay=x='mod(100+50*t,W-400)':y='mod(100+30*t,H-300)'[v1];"
        f"[v1]drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,{duration})':box=1:boxcolor=black@0.3[out]"
    )

    cmd = [
        FFMPEG, "-y",
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-b:v", "2M",
        output,
    ]
    print(f"  Creating {output}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}", file=sys.stderr)
        return False
    return True


def create_bg_music(output: str = "/tmp/bg_music.mp3", duration: int = 15):
    """Create a simple ambient background music track."""
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=220:duration={duration}",
        "-f", "lavfi",
        "-i", f"sine=frequency=330:duration={duration}",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-filter_complex",
        f"[0:a]volume=0.03[a1];[1:a]volume=0.02[a2];[2:a]volume=0.015[a3];"
        f"[a1][a2][a3]amix=inputs=3:duration=first",
        "-ac", "2",
        "-b:a", "64k",
        output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False
    return True


if __name__ == "__main__":
    print("Creating test backgrounds...\n")

    create_bg_video(
        "/tmp/bg_primary.mp4",
        duration=15,
        color="0x1a202c",
        accent="0x2d3748",
        text="GAMEPLAY - NIVEL 1",
    )
    create_bg_video(
        "/tmp/bg_secondary.mp4",
        duration=15,
        color="0x22543d",
        accent="0x276749",
        text="GAMEPLAY - NIVEL 2",
    )
    create_bg_music("/tmp/bg_music.mp3", duration=15)

    print("\nDone: /tmp/bg_primary.mp4, /tmp/bg_secondary.mp4, /tmp/bg_music.mp3")
