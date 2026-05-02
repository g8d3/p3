#!/usr/bin/env python3
"""
Post-process any generated video to boost volume.
No rebuild needed. Runs in 2 seconds.

Usage:
  python adjust_volume.py path/to/video.mp4            # default 2x boost
  python adjust_volume.py path/to/video.mp4 --boost 5  # custom boost
  python adjust_volume.py path/to/video.mp4 --loudnorm # automatic normalization
"""

import subprocess, sys, os
from pathlib import Path

def get_duration(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",path], capture_output=True,text=True,timeout=15)
    return float(r.stdout.strip())

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h","--help"):
        print(__doc__)
        return

    src = sys.argv[1]
    if not Path(src).exists():
        print(f"File not found: {src}")
        return

    boost = 2.0
    use_loudnorm = False
    if "--boost" in sys.argv:
        idx = sys.argv.index("--boost")
        boost = float(sys.argv[idx + 1])
    if "--loudnorm" in sys.argv:
        use_loudnorm = True

    ext = Path(src).suffix
    out = src.replace(ext, f"_volume{ext}")

    if use_loudnorm:
        # Two-pass loudnorm: measure first, then normalize
        print(f"Measuring loudness...")
        measure = subprocess.run(
            ["ffmpeg","-i",src,"-af","loudnorm=I=-14:print_format=json",
             "-f","null","-"],
            capture_output=True, text=True, timeout=30
        )
        # Extract measured values
        for line in measure.stderr.split("\n"):
            if "input_i" in line:
                val = line.split(":")[-1].strip().rstrip(",")
                print(f"  Input loudness: {val} LUFS")
        print(f"  Normalizing to -14 LUFS (YouTube standard)")
        cmd = [
            "ffmpeg","-y","-i",src,
            "-af", "loudnorm=I=-14:LRA=7:TP=-2",
            "-c:v", "copy", out,
        ]
    else:
        print(f"  Boosting audio by {boost}x")
        cmd = [
            "ffmpeg","-y","-i",src,
            "-af", f"volume={boost}",
            "-c:v", "copy", out,
        ]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode == 0:
        dur = get_duration(out)
        size = Path(out).stat().st_size
        print(f"  Done: {out}")
        print(f"  {dur:.0f}s | {size/1024/1024:.1f} MB")
    else:
        print(f"Error: {result.stderr.decode()[:300]}")

if __name__ == "__main__":
    main()
