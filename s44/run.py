#!/usr/bin/env python3
"""
Content Agent — Autonomous Content Creator
Main entry point. Orchestrates the full pipeline:
  topic selection → script → TTS → recording → assembly → publish

Usage:
  python run.py                  # Full pipeline with random topic
  python run.py --topic "name"   # Review a specific topic
  python run.py --dry-run        # Generate plan without executing
  python run.py --schedule       # Set up daily cron schedule
  python run.py --refine         # Run personality refinement (no content)
  python run.py --list-topics    # Show available review topics
"""

import sys
import os
import json
import argparse
import subprocess
import tempfile as _tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TMP = Path(__file__).parent / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

from agent.script_gen import create_content_plan, pick_topic, SOFTWARE_TOPICS
from agent.personality import load_personality, iteration_report, record_engagement
from agent.social import save_post
from pipeline.tts import generate_speech, generate_voiceover
from pipeline.captions import generate_subtitles_from_script
from pipeline.assemble import VideoAssembler, generate_sfx_timing
from pipeline.sfx import generate_all_sfx, get_sfx_map


def parse_args():
    parser = argparse.ArgumentParser(description="Autonomous Content Creator")
    parser.add_argument("--topic", type=str, help="Specific topic to review")
    parser.add_argument("--dry-run", action="store_true", help="Generate plan only")
    parser.add_argument("--schedule", action="store_true", help="Set up daily cron")
    parser.add_argument("--refine", action="store_true", help="Run personality refinement")
    parser.add_argument("--list-topics", action="store_true", help="List available topics")
    parser.add_argument("--no-record", action="store_true", help="Skip screen recording")
    parser.add_argument("--output", type=str, help="Output directory", default=None)
    return parser.parse_args()


def list_topics():
    """Display all available review topics."""
    print("\n=== Available Review Topics ===\n")
    for category, topics in SOFTWARE_TOPICS.items():
        print(f"\n{category.upper()}:")
        for t in topics:
            print(f"  • {t['name']:25s} — {t['hook']}")
    print()


def dry_run(plan: dict):
    """Display the content plan without executing."""
    notes = plan["notes"]
    print(f"""
╔══════════════════════════════════════════════╗
║          CONTENT PLAN (DRY RUN)              ║
╠══════════════════════════════════════════════╣
║ ID:      {plan['content_id']}
║ Topic:   {plan['topic']['name']}
║ URL:     {plan['topic']['url']}
║ Type:    {plan['topic'].get('type', 'N/A')}
║ Duration: {notes['estimated_duration']:.1f}s
║ Words:   {notes['total_words']}
║ SFX:     {len(notes['sfx_cues'])} cues
║ Memes:   {len(notes['meme_cues'])} cues
║ TTS:     {plan['settings']['tts_voice']}
║ Tone:    {plan['personality']['tone']}
╠══════════════════════════════════════════════╣
║ RECORDING STEPS:                             ║""")
    for i, step in enumerate(plan["recording_steps"][:8], 1):
        print(f"║   {i}. {step['action']:12s} → {step.get('selector', step.get('url', ''))[:50]}")
    if len(plan["recording_steps"]) > 8:
        print(f"║   ... +{len(plan['recording_steps']) - 8} more steps")
    print("""╠══════════════════════════════════════════════╣
║ SCRIPT:                                       ║""")
    for line in plan["script"].split("\n"):
        print(f"║   {line[:72]}")
    print("""╚══════════════════════════════════════════════╝""")


def run_pipeline(plan: dict, skip_recording: bool = False,
                 output_dir: str = None):
    """
    Execute the full content creation pipeline.
    
    Stages:
    1. Write script to file
    2. Generate voiceover (TTS)
    3. Generate subtitles
    4. Record screen (optional)
    5. Assemble final video
    6. Save post package
    """
    personality = load_personality()
    content_id = plan["content_id"]
    topic = plan["topic"]
    topic_slug = topic["name"].lower().replace(" ", "_").replace("/", "_")

    print(f"\n{'='*60}")
    print(f"  Content Agent — Pipeline Run")
    print(f"  {content_id}")
    print(f"  Topic: {topic['name']}")
    print(f"{'='*60}\n")

    # --- Stage 1: Write script ---
    print("[1/5] Writing script...")
    script_path = f"{TMP}/{content_id}_script.txt"
    with open(script_path, "w") as f:
        for line in plan["script"].split("\n"):
            line = line.strip()
            if line:
                f.write(line + "\n")
    print(f"  ✓ Script saved ({len(plan['script'])} chars)")
    print(f"  ✓ SFX cues: {len(plan['notes']['sfx_cues'])}")

    # --- Stage 2: Generate voiceover ---
    print("\n[2/5] Generating voiceover...")
    tts_voice = plan["settings"].get("tts_voice", "af_heart")
    tts_speed = plan["settings"].get("tts_speed", 1.0)
    audio_path = f"{TMP}/{content_id}_narration.wav"

    try:
        generate_voiceover(script_path, audio_path,
                          backend="kokoro",
                          voice=tts_voice,
                          speed=tts_speed)
        audio_size = Path(audio_path).stat().st_size
        print(f"  ✓ Voiceover generated ({audio_size / 1024:.0f} KB)")
    except Exception as e:
        print(f"  ⚠ Voiceover failed: {e}")
        print(f"  ⚠ Trying edge-tts fallback...")
        try:
            from pipeline.tts import speak_edge
            import asyncio
            with open(script_path) as f:
                text = f.read()
            audio_path = audio_path.replace(".wav", ".mp3")
            asyncio.run(speak_edge(text, voice="en-US-JennyNeural",
                                    output_path=audio_path))
            print(f"  ✓ Voiceover generated with edge-tts")
        except Exception as e2:
            print(f"  ✗ Voiceover failed completely: {e2}")
            return None

    # --- Stage 3: Generate subtitles ---
    print("\n[3/5] Generating subtitles...")
    srt_path = f"{TMP}/{content_id}_subtitles.srt"
    wps = plan["settings"].get("words_per_second", 2.8)
    generate_subtitles_from_script(script_path, srt_path,
                                    words_per_second=wps)
    print(f"  ✓ Subtitles saved")

    # --- Stage 4: Record screen (optional) ---
    recording_path = None
    if not skip_recording:
        print("\n[4/5] Recording screen...")
        recording_path = f"{TMP}/{content_id}_recording.mp4"

        try:
            from pipeline.record import create_testreel_config, record_with_playwright
            config = create_testreel_config(
                url=topic["url"],
                steps=plan["recording_steps"],
                output_format="mp4",
            )
            config_path = f"{TMP}/{content_id}_config.json"
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            # Try Testreel first
            try:
                recording_path = record_with_playwright(config_path)
                print(f"  ✓ Recording complete: {recording_path}")
            except Exception as e:
                print(f"  ⚠ Testreel recording failed: {e}")
                print(f"  ⚠ Falling back to simple Playwright script...")
                recording_path = None

        except Exception as e:
            print(f"  ⚠ Recording unavailable: {e}")
            recording_path = None
    else:
        print("\n[4/5] Screen recording skipped (--no-record)")

    if recording_path is None:
        # Create a placeholder/slideshow video from screenshots
        print("  ⚠ No recording available — generating image-based video")
        recording_path = _generate_placeholder_video(topic["name"],
                                                      duration=plan["notes"]["estimated_duration"] + 4)

    # --- Stage 5: Assemble final video ---
    print("\n[5/5] Assembling final video...")
    assembler = VideoAssembler(output_dir=output_dir or f"{TMP}/{content_id}_output")

    # Prepare SFX timing
    sfx_map = {name: str(path) for name, path in get_sfx_map().items()}
    sfx_timing = []
    for time_sec, sfx_type in plan["notes"]["sfx_cues"]:
        if sfx_type in sfx_map and Path(sfx_map[sfx_type]).exists():
            sfx_timing.append((time_sec, sfx_map[sfx_type]))

    # Find background music
    bg_music = None
    music_dir = Path(__file__).parent / "assets" / "music"
    music_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    if music_files:
        import random
        bg_music = str(random.choice(music_files))

    try:
        final_path = assembler.assemble(
            recording_path=recording_path,
            narration_path=audio_path,
            output_path=f"{TMP}/{content_id}_final.mp4",
            title=f"Review: {topic['name']}",
            bg_music=bg_music,
            subtitles_path=srt_path,
            sfx_timing=sfx_timing,
            meme_overlays=None,
        )
        video_size = Path(final_path).stat().st_size
        print(f"  ✓ Final video: {final_path}")
        print(f"  ✓ Size: {video_size / 1024 / 1024:.1f} MB")
    except Exception as e:
        print(f"  ✗ Assembly failed: {e}")
        return None

    # --- Save post package ---
    print("\nSaving post package...")
    post = save_post(plan, video_path=final_path)

    # Record iteration
    record_engagement(
        iteration=personality["learning"]["iterations"] + 1,
        content_id=content_id,
    )
    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline complete!")
    print(f"  📹 Video: {final_path}")
    print(f"  📝 Posts: {Path(post['content_id']).resolve()}")
    print(f"{'='*60}\n")

    return final_path


def _generate_placeholder_video(title: str, duration: float = 30.0) -> str:
    """Generate a simple background video as fallback when recording fails."""
    output = f"{TMP}/{title.replace(' ', '_').replace(':', '')}_placeholder.mp4"
    # Use a simple gradient-ish color background — no drawtext to avoid font issues
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=#1e1b4b:s=1280x720:d={duration}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        output,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 or not Path(output).exists():
        # Ultra-fallback: tiny valid MP4
        cmd2 = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=640x360:d=10",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
            output,
        ]
        subprocess.run(cmd2, capture_output=True, timeout=30)
    return output


def main():
    args = parse_args()

    if args.list_topics:
        list_topics()
        return

    if args.schedule:
        from agent.scheduler import set_multiple_daily, show_schedule
        print("=== Setting up daily schedule ===")
        set_multiple_daily([(9, 0), (15, 0), (21, 0)])
        show_schedule()
        return

    if args.refine:
        print("=== Personality Refinement ===")
        print(iteration_report())
        print()
        personality = load_personality()
        print(f"Current tone: {personality['voice']['tone']}")
        print(f"Current energy: {personality['voice']['energy']}")
        print(f"Total iterations: {personality['learning']['iterations']}")
        return

    # Generate content plan
    print("=== Generating Content Plan ===")
    if args.topic:
        plan = create_content_plan(preference=args.topic)
    else:
        plan = create_content_plan()

    if args.dry_run:
        dry_run(plan)
        return

    print(f"  Content: {plan['content_id']}")
    print(f"  Topic: {plan['topic']['name']}")

    # Run full pipeline
    result = run_pipeline(plan, skip_recording=args.no_record,
                          output_dir=args.output)

    if result:
        print(f"\n✨ Done! Video at: {result}")
    else:
        print(f"\n❌ Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
