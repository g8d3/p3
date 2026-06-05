#!/usr/bin/env python3
"""
Render A2A demo video using Pillow (images) + ffmpeg (video+audio).
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

TTS_DIR = "/tmp/a2a-demo-tts"
OUTPUT_DIR = "/tmp/a2a-demo-video"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 1280, 720
BG = (26, 26, 46)
FG = (255, 255, 255)
BLUE = (0, 212, 255)
GRAY = (136, 136, 136)
GREEN = (81, 207, 102)
RED = (255, 107, 107)
YELLOW = (255, 204, 0)

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
FONT_SUB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
FONT_MONO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 20)

STEPS = [
    ("A2A Protocol Test", "Agent-to-Agent Protocol v1.0 — Testing Limits", [
        ("Testing A2A on two agents: Alpha (generalist) and Beta (quality)", FG),
        ("Goal: find limits and propose a quality extension", FG),
        ("", None),
        ("stack: A2A + MCP + ACP are complementary protocols", GRAY),
    ]),
    ("Step 1: Agent Discovery", "Agent Cards at /.well-known/agent.json", [
        ("✅ Alpha-Generalist found — skills: research, analyze, delegate", GREEN),
        ("✅ Beta-Quality found — skills: code-review, validate, quality-check", GREEN),
        ("", None),
        ("Agent Cards describe capabilities but NO quality criteria", YELLOW),
    ]),
    ("Step 2: Task Execution", "Task lifecycle: submitted → working → completed", [
        ("Client sends task via POST /message:send", FG),
        ("Agent processes asynchronously, client polls via GET /tasks/{id}", FG),
        ("✅ Task lifecycle works correctly", GREEN),
        ("   Poll 1: working → Poll 2: working → Poll 3: completed", GRAY),
    ]),
    ("Step 3: Cancellation", "CancelTask via POST /tasks/{id}:cancel", [
        ("Client sends cancel request → state transitions to 'canceled'", FG),
        ("⚠️ Race condition found: processor thread overwrote state", YELLOW),
        ("✅ Bug fixed: complete_task() checks TERMINAL_STATES first", GREEN),
        ("Result: Cancellation works with proper locking", FG),
    ]),
    ("Step 4: Quality Gate Limitation", "THE KEY FINDING", [
        ("Good code input → state: completed", GREEN),
        ("Buggy code input → state: completed", GREEN),
        ("SAME STATE for both! No quality distinction!", RED),
        ("", None),
        ("A2A has NO concept of:", YELLOW),
        ("  • pending-review  (work done, needs validation)", RED),
        ("  • needs-revision  (checker rejected, go back)", RED),
        ("  • quality-passed  (passed all gates)", RED),
        ("❌ Quality is invisible to the protocol", RED),
    ]),
    ("The Solution: A2A-Q Extension", "A backward-compatible extension to A2A v1.0", [
        ("New states: pending-review, needs-revision, quality-passed, escalated", BLUE),
        ("New ops: requestReview, submitVerdict, requestRevision, getQualityReport", BLUE),
        ("Efficacy: quality_score, revision_count, criteria_results", FG),
        ("Efficiency: wall_time, tokens, utilization", FG),
        ("Hardware: CPU, RAM, context_window_pct", FG),
        ("Runtime: language, memory_footprint, startup_time", FG),
        ("~500 line RFC with full JSON schema", GRAY),
    ]),
    ("Next Steps & Call to Feedback", "Get involved — test it, break it, improve it", [
        ("RFC: s84/A2A-Q-RFC.md on GitHub (g8d3/p3)", BLUE),
        ("Code: s84/a2a_test/ — run it yourself!", GREEN),
        ("P1: Python implementation on a2a-sdk", FG),
        ("P2: Test with real A2A agents (ADK, LangGraph, CrewAI)", FG),
        ("P3: Submit as formal extension PR to A2A spec repo", FG),
        ("", None),
        ("github.com/g8d3/p3/tree/main/s84", GRAY),
    ]),
]


def get_audio_duration(mp3_path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3_path],
        capture_output=True, text=True, timeout=10
    )
    return float(r.stdout.strip() or 3.0)


def make_frame(text_lines, bar_text, step_label):
    """Create a Pillow image with text."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Top bar
    draw.rectangle([(0, 0), (W, 60)], fill=(20, 20, 40))
    # Bottom bar
    draw.rectangle([(0, H-35), (W, H)], fill=(15, 15, 30))

    # Title
    draw.text((30, 12), bar_text, font=FONT_SUB, fill=BLUE)
    draw.text((W-180, 12), step_label, font=FONT_SUB, fill=GRAY)

    # Body text
    y = 90
    for text, color in text_lines:
        if text == "":
            y += 15
            continue
        c = color or GRAY
        font = FONT_MONO if text.startswith("  •") else FONT
        draw.text((40, y), text, font=font, fill=c)
        y += 35

    return img


def main():
    print("Rendering A2A demo video with Pillow + ffmpeg...")

    for i, (title, subtitle, lines) in enumerate(STEPS):
        audio = os.path.join(TTS_DIR, f"step{i+1:02d}.mp3")
        if not os.path.exists(audio):
            print(f"  ⚠️  No audio for step {i+1}")
            continue

        dur = get_audio_duration(audio)
        fps = 2
        total_frames = max(int(dur * fps), 1)
        seg_dir = os.path.join(OUTPUT_DIR, f"seg{i:02d}")
        os.makedirs(seg_dir, exist_ok=True)

        bar_text = f"{title} — {subtitle}"
        step_label = f"Step {i+1}/{len(STEPS)}"

        # Generate frames
        for f_idx in range(total_frames):
            img = make_frame(lines, bar_text, step_label)
            img.save(os.path.join(seg_dir, f"frame{f_idx:04d}.png"))

        # Build video segment from frames + audio
        seg_out = os.path.join(OUTPUT_DIR, f"seg{i:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", f"{seg_dir}/frame%04d.png",
            "-i", audio,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-pix_fmt", "yuv420p",
            "-shortest", seg_out
        ], capture_output=True, timeout=120)
        print(f"  Step {i+1}: {dur:.1f}s -> {seg_out}")

    # Concatenate all segments
    segments = sorted([
        os.path.join(OUTPUT_DIR, f)
        for f in os.listdir(OUTPUT_DIR)
        if f.startswith("seg") and f.endswith(".mp4")
    ])
    if not segments:
        print("❌ No segments to concatenate")
        return

    list_file = os.path.join(OUTPUT_DIR, "concat.txt")
    with open(list_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    final = os.path.join(OUTPUT_DIR, "a2a-demo-final.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", final
    ], capture_output=True, timeout=60)

    size_mb = os.path.getsize(final) / 1e6
    duration = get_audio_duration(final) if os.path.exists(final) else 0
    print(f"\n✅ Video: {final}")
    print(f"   Size: {size_mb:.1f} MB")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Segments: {len(segments)}")


if __name__ == "__main__":
    main()
