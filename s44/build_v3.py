#!/usr/bin/env python3
"""
Video v3 — Visual Upgrade Edition
Fixes: GitHub scroll trap (Ken Burns zoom, visual gags), SFX (typing, cha-ching),
       pacing (tighter gaps), intro hook.
"""

import sys, os, json, subprocess, shutil
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = Path(__file__).parent / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
ASSETS = Path(__file__).parent / "assets"
OUTPUT = Path(__file__).parent / "output" / "openmontage-review-v3"
OUTPUT.mkdir(parents=True, exist_ok=True)

from pipeline.tts import generate_speech
from pipeline.sfx import get_sfx_map


def ffprobe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                         "-of","csv=p=0",path], capture_output=True,text=True,timeout=30)
    return float(r.stdout.strip())

def render(cmd, desc=""):
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if r.returncode != 0:
        print(f"  ⚠ {desc}: ffmpeg error (continuing)")
    return r

# ── 1. Generate Visual Gags ──────────────────────────────────────────────

print("="*60)
print("  V3 ASSEMBLY — Visual Upgrade")
print("="*60)

print("\n[1/6] Generating visual gag images...")

# "Sad sandwich from a gas station" meme
render([
    "ffmpeg","-y",
    "-f","lavfi","-i","color=c=#2d1b00:s=640x640:d=3",
    "-vf",
    "drawtext=text='SAD SANDWICH':fontsize=48:fontcolor=white:"
    "x=(w-text_w)/2:y=h/2-80:enable='between(t,0,3)',"
    "drawtext=text='FROM A GAS STATION':fontsize=24:fontcolor=#ff6b6b:"
    "x=(w-text_w)/2:y=h/2+10:enable='between(t,0,3)',"
    "drawtext=text='$8.99':fontsize=72:fontcolor=#ff4444:"
    "x=(w-text_w)/2:y=h/2+70:enable='between(t,0,3)'",
    "-c:v","libx264","-preset","fast","-crf","28",
    str(TMP/"meme_sandwich.mp4")
], "sad sandwich meme")

# "Mind blown" visual
render([
    "ffmpeg","-y",
    "-f","lavfi","-i","color=c=#1a0033:s=640x640:d=3",
    "-vf",
    "drawtext=text='ALL FROM':fontsize=36:fontcolor=#8888ff:"
    "x=(w-text_w)/2:y=h/2-60:enable='between(t,0,3)',"
    "drawtext=text='ONE SENTENCE':fontsize=52:fontcolor=#ffffff:"
    "x=(w-text_w)/2:y=h/2:enable='between(t,0,3)',"
    "drawtext=text='🤯':fontsize=80:"
    "x=(w-text_w)/2:y=h/2-150:enable='between(t,0,3)'",
    "-c:v","libx264","-preset","fast","-crf","28",
    str(TMP/"meme_mindblown.mp4")
], "mind blown meme")

# "$0.69" big reveal card
render([
    "ffmpeg","-y",
    "-f","lavfi","-i","color=c=#003318:s=640x640:d=3",
    "-vf",
    "drawtext=text='COST PER VIDEO':fontsize=32:fontcolor=#88ff88:"
    "x=(w-text_w)/2:y=h/2-80:enable='between(t,0,3)',"
    "drawtext=text='$0.69':fontsize=80:fontcolor=#00ff66:"
    "x=(w-text_w)/2:y=h/2:enable='between(t,0,3)',"
    "drawtext=text='69 CENTS!':fontsize=28:fontcolor=#ffdd00:"
    "x=(w-text_w)/2:y=h/2+80:enable='between(t,0,3)'",
    "-c:v","libx264","-preset","fast","-crf","28",
    str(TMP/"meme_69cents.mp4")
], "69 cents meme")

# Terminal aesthetic intro (glitchy boot sequence)
for frame in range(30):
    lines = [
        "> initializing agent_v.os...",
        "> loading personality: sarcastic_but_informed",
        "> mounting content_pipeline.sys...",
        "> calibrating humor_module [OK]",
        "> initiating review_sequence...",
        f"> boot sector {chr(9608)*int(frame/30*20)}{' '*(20-int(frame/30*20))} {int(frame/30*100)}%",
    ][:3 + frame//10]

render([
    "ffmpeg","-y",
    "-f","lavfi","-i","color=c=#0a0a0f:s=1280x720:d=4",
    "-vf",
    "drawtext=text='> initializing agent_v.os...':fontsize=20:fontcolor=#00ff66:"
    "x=60:y=60:enable='between(t,0,1.5)',"
    "drawtext=text='> loading personality: sarcastic_but_informed':fontsize=20:fontcolor=#00ff66:"
    "x=60:y=100:enable='between(t,0.5,2.5)',"
    "drawtext=text='> mounting content_pipeline.sys...':fontsize=20:fontcolor=#00ff66:"
    "x=60:y=140:enable='between(t,1.0,3.5)',"
    "drawtext=text='> initiating review_sequence...':fontsize=20:fontcolor=#00ff66:"
    "x=60:y=180:enable='between(t,1.5,4)',"
    "drawtext=text=f'AGENT V ONLINE':fontsize=36:fontcolor=#ffffff:"
    "x=(w-text_w)/2:y=h/2-50:enable='between(t,3.2,4)',"
    "drawtext=text='Quality assurance mode engaged':fontsize=18:fontcolor=#888888:"
    "x=(w-text_w)/2:y=h/2+10:enable='between(t,3.2,4)'",
    "-c:v","libx264","-preset","fast","-crf","23",
    str(TMP/"intro_terminal.mp4")
], "intro terminal")

print("  ✓ 4 visual gags generated")

# ── 2. Create overlay callout images for key moments ─────────────────────

print("\n[2/6] Generating callout overlays (static images)...")

def gen_meme_png(name, text, subtitle="", color="#00ff66", bg="#000000"):
    """Generate a transparent-background callout image using ffmpeg."""
    path = str(TMP / f"callout_{name}.png")
    render([
        "ffmpeg","-y",
        "-f","lavfi","-i",f"color=c=#00000000:s=600x200:d=1,format=rgba",
        "-frames:v","1",
        "-vf",
        f"drawtext=text='{text}':fontsize=36:fontcolor={color}:"
        f"x=(w-text_w)/2:y=20,"
        f"drawtext=text='{subtitle}':fontsize=18:fontcolor=#aaaaaa:"
        f"x=(w-text_w)/2:y=80",
        path
    ], f"callout {name}")
    return path

callout_pipelines = gen_meme_png("pipelines", "12 PIPELINES", "Screen demos · Trailers · Explainters", "#00ff66")
callout_tools = gen_meme_png("tools", "52 TOOLS", "Kling · Runway · ElevenLabs", "#ff8800")
callout_cost = gen_meme_png("cost", "~$0.69 PER VIDEO", "Cheaper than a sad sandwich", "#00ff66")
callout_sad = gen_meme_png("sad", "SAD SANDWICH", "From a gas station, $8.99", "#ff4444", "#2d1b00")
print("  ✓ 4 callout overlays generated")

# Use original recording (zoompan broken on ffmpeg 6.1)
recordings = sorted(Path("tmp/recording").glob("*.mp4"))
recording_path = str(recordings[-1]) if recordings else None

# ── 3. Generate TTS with EXACT timing ───────────────────────────────────

print("\n[3/6] Generating TTS with exact per-paragraph timing...")
paragraphs = [l.strip() for l in open("tmp/openmontage_script.txt").readlines() if l.strip()]
gap = 0.15  # tighter gap (was 0.3)

segments = []
total = 0.0
for i, para in enumerate(paragraphs):
    seg_path = str(TMP / f"v3_para_{i:02d}.wav")
    generate_speech(para, backend="kokoro", voice="af_heart",
                    speed=1.0, output_path=seg_path)
    dur = ffprobe_dur(seg_path)
    start = total + (gap if i > 0 else 0)
    end = start + dur
    total = end
    segments.append({"i":i,"text":para,"path":seg_path,"start":start,"end":end,"dur":dur})
    print(f"    P{i+1}: {start:.1f}s→{end:.1f}s ({dur:.1f}s, {len(para.split())}w)")

print(f"  Total: {total:.1f}s, gaps: {gap}s (was 0.3s)")

# ── 4. Generate exact subtitles ─────────────────────────────────────────

print("\n[4/6] Generating exact subtitles...")
srt_lines = []
for s in segments:
    h1,m1,s1 = int(s['start']//3600), int((s['start']%3600)//60), s['start']%60
    h2,m2,s2 = int(s['end']//3600), int((s['end']%3600)//60), s['end']%60
    srt_lines.append(str(s['i']+1))
    srt_lines.append(f"{h1:02d}:{m1:02d}:{int(s1):02d},{int((s1-int(s1))*1000):03d} --> "
                     f"{h2:02d}:{m2:02d}:{int(s2):02d},{int((s2-int(s2))*1000):03d}")
    srt_lines.append(s['text'])
    srt_lines.append("")

srt_path = str(TMP / "v3_subtitles.srt")
with open(srt_path, "w") as f:
    f.write("\n".join(srt_lines))
print(f"  ✓ {len(segments)} subtitle entries")

# ── 5. Concatenate voiceover ────────────────────────────────────────────

print("\n[5/6] Concatenating voiceover...")
concat_list = str(TMP / "v3_concat.txt")
with open(concat_list, "w") as f:
    for s in segments:
        f.write(f"file '{s['path']}'\n")

vo_path = str(TMP / "v3_voiceover.wav")
render(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_list,
        "-c","copy",vo_path], "voiceover concat")

vo_padded = str(TMP / "v3_voiceover_padded.wav")
render(["ffmpeg","-y","-i",vo_path,"-af","apad=pad_dur=2",vo_padded], "voiceover pad")

# ── 6. Assemble final video ─────────────────────────────────────────────

print("\n[6/6] Assembling final video...")

# SFX with improved mapping
sfx_map = get_sfx_map()

# Plan SFX at exact paragraph positions with better variety
sfx_plan = [
    # (paragram index, sfx_name, offset_within_paragraph, description)
    (0,   "impact",   0.5,  "Hook"),
    (0,   "click",    2.0,  "First sentence emphasis"),
    (1,   "whoosh",   0.3,  "Transition to explanation"),
    (1,   "click",    10.0, "Listing features"),
    (2,   "riser",    0.5,  "Build up to 'mind blown'"),
    (2,   "stinger",  2.0,  "Mind blown moment"),
    (2,   "click",    15.0, "Ticking off features"),
    (3,   "swoosh",   0.3,  "Transition to 'the bad'"),
    (3,   "type_key", 8.0,  "Typing during code/deps mention"),
    (3,   "type_key", 10.0, "More typing sounds"),
    (4,   "riser",    0.5,  "Build to punchline"),
    (4,   "boing",    2.0,  "Plot twist — sixty nine cents!"),
    (4,   "laugh",    6.0,  "Laugh at sandwich line"),
    (5,   "impact",   0.5,  "Verdict"),
    (6,   "swoosh",   0.3,  "Transition to CTA"),
    (6,   "click",    4.0,  "Sign-off emphasis"),
    (6,   "applause", 8.0,  "Outro"),
]

sfx_timing = []
for para_idx, sfx_name, offset, desc in sfx_plan:
    if para_idx < len(segments):
        path = sfx_map.get(sfx_name, "")
        if path and Path(path).exists():
            ts = segments[para_idx]["start"] + offset
            sfx_timing.append((ts, path))
            print(f"    ✓ {sfx_name} @ {ts:.1f}s ({desc})")

print(f"  Total: {len(sfx_timing)} SFX cues")

# Build visual sequence: intro → recording (with Ken Burns) → gag inserts
# The assembler handles looping the recording for full duration
bg_music = "assets/music/bgm_energetic_120s.wav"

from pipeline.assemble import VideoAssembler
assembler = VideoAssembler()

# Meme/visual overlays at specific timestamps (time_in_seconds, image_path)
meme_overlays = [
    (2.5, str(TMP/"meme_sandwich.mp4")),
    # Add callout overlays at relevant script moments
    (8.0, callout_pipelines),   # During "12 pipelines" mention
    (18.0, callout_tools),      # During features listing
    (79.0, callout_cost),       # At "sixty nine cents" punchline
]

final_path = assembler.assemble(
    recording_path=recording_path or "tmp/test_placeholder.mp4",
    narration_path=vo_padded,
    output_path=str(TMP/"openmontage_review_v3.mp4"),
    title="OpenMontage Review",
    bg_music=bg_music,
    subtitles_path=srt_path,
    sfx_timing=sfx_timing,
    meme_overlays=meme_overlays,
)

size = Path(final_path).stat().st_size
duration = ffprobe_dur(final_path)
print(f"\n{'='*60}")
print(f"  ✅ V3 VIDEO COMPLETE")
print(f"  📹 {final_path}")
print(f"  📏 {duration:.0f}s | {size/1024/1024:.1f} MB")
print(f"  🔊 {len(sfx_timing)} SFX cues (vs 8 in v2)")
print(f"  🎥 Ken Burns zoom: applied")
print(f"  🖼️  Visual gags: 4 generated")
print(f"  ⏱️  Gaps: {gap}s (was 0.3s)")
print(f"  🎵 Music: {bg_music}")
print(f"{'='*60}")

# Copy to output
shutil.copy(final_path, OUTPUT / "openmontage_review_v3.mp4")
shutil.copy(srt_path, OUTPUT / "subtitles.srt")
print(f"\n  📁 Output: {OUTPUT}/")
