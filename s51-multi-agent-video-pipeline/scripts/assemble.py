#!/usr/bin/env python3
"""Assemble scene clips into 4 final videos."""
import subprocess
import os

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = f"{BASE}/output/clips"
RENDERS_DIR = f"{BASE}/output/renders"

os.makedirs(RENDERS_DIR, exist_ok=True)

# Scene durations (for transition timing)
scene_durs = {1: 8, 2: 10, 3: 8, 4: 8, 5: 8, 6: 18}
total_dur = sum(scene_durs.values())  # 60s

variants = [
    ("b1", "video_b1.mp4", "Wan2.2 Realista"),
    ("b2", "video_b2.mp4", "HunyuanVideo Cinematic"),
    ("b3", "video_b3.mp4", "CogVideo Artistico"),
    ("b4", "video_b4.mp4", "Variacion Semillas"),
]


def assemble(prefix, output_name, label):
    clips = []
    for esc_id in range(1, 7):
        clip = f"{CLIPS_DIR}/escena{esc_id}_{prefix}.mp4"
        if os.path.exists(clip) and os.path.getsize(clip) > 1000:
            clips.append(clip)
        else:
            print(f"  ⚠️ Missing: {clip}")
            return None
    
    print(f"\n  {label}: {len(clips)} clips -> {output_name}")
    
    output_raw = f"{RENDERS_DIR}/{output_name.replace('.mp4', '_raw.mp4')}"
    output_final = f"{RENDERS_DIR}/{output_name}"
    
    # Use concat demuxer (fastest)
    concat_file = f"{CLIPS_DIR}/concat_{prefix}.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_raw
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    
    if r.returncode != 0:
        print(f"    concat failed, trying filter approach...")
        inputs = []
        fp = []
        for i, clip in enumerate(clips):
            inputs.extend(["-i", clip])
            fp.append(f"[{i}:v][{i}:a]")
        fs = "".join(fp) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", fs,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            output_raw
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
    
    if not os.path.exists(output_raw):
        print(f"    ❌ Assembly failed")
        return None
    
    # Add transitions
    cmd2 = [
        "ffmpeg", "-y",
        "-i", output_raw,
        "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={total_dur-2}:d=2",
        "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={total_dur-2}:d=2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_final
    ]
    subprocess.run(cmd2, capture_output=True, text=True)
    
    if os.path.exists(output_raw):
        os.remove(output_raw)
    
    if os.path.exists(output_final):
        mb = os.path.getsize(output_final) / (1024*1024)
        print(f"    ✅ {output_name} ({mb:.1f} MB)")
        return output_final
    
    return None


def main():
    print("=" * 60)
    print("🔗 Ensamblando 4 variaciones de video")
    print(f"   Duración total: {total_dur}s")
    print("=" * 60)
    
    results = {}
    for prefix, name, label in variants:
        res = assemble(prefix, name, label)
        if res:
            results[name] = res
    
    print(f"\n✅ Resultados:")
    for name, path in results.items():
        mb = os.path.getsize(path) / (1024*1024)
        print(f"   {name}: {mb:.1f} MB")
    
    print(f"\n📂 Directorio: {RENDERS_DIR}/")
    
    # Also save as progres report
    return results


if __name__ == "__main__":
    main()
