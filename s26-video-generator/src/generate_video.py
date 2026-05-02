#!/usr/bin/env python3
"""
Autonomous Video Generator
===========================
Generates videos from text with configurable audio and video settings.
Uses config.yaml for all parameters - minimal LLM interaction needed.
"""

import os
import sys
import json
import yaml
import subprocess
import requests
import base64
import argparse
from pathlib import Path

# Default config
DEFAULT_CONFIG = {
    "video": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "target_duration": 60
    },
    "audio": {
        "provider": "inworld",
        "voice": "Timothy",
        "model": "inworld-tts-1.5-max",
        "speed": 1.0,
        "fade_out": 8,
        "chunk_size": 1800
    },
    "text": {
        "sections": []
    },
    "youtube": {
        "client_secret": "",
        "title_template": "{title}",
        "description": "",
        "tags": [],
        "privacy": "public"
    }
}

def load_config(config_path="config.yaml"):
    """Load configuration from YAML file"""
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = DEFAULT_CONFIG.copy()
    
    # Merge with defaults
    for key in DEFAULT_CONFIG:
        if key not in config:
            config[key] = DEFAULT_CONFIG[key]
    
    return config

def generate_audio_inworld(text, config, output_path):
    """Generate audio using Inworld TTS API"""
    api_key = os.environ.get("INWORLD_API_KEY")
    if not api_key:
        print("❌ INWORLD_API_KEY not set")
        return False
    
    # Split text into chunks
    chunks = []
    current = ""
    max_chars = config["audio"].get("chunk_size", 1800)
    
    for sentence in text.replace(".", ".|").replace("?", "?|").replace("!", "!|").split("|"):
        if len(current) + len(sentence) < max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence
    if current:
        chunks.append(current.strip())
    
    print(f"📝 Generating audio ({len(chunks)} chunks)...")
    
    all_audio = []
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    for i, chunk in enumerate(chunks):
        data = {
            "modelId": config["audio"].get("model", "inworld-tts-1.5-max"),
            "text": chunk,
            "voiceId": config["audio"].get("voice", "Timothy")
        }
        
        response = requests.post(
            "https://api.inworld.ai/tts/v1/voice",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            audio = base64.b64decode(response.json()["audioContent"])
            all_audio.append(audio)
            print(f"  Chunk {i+1}: OK")
        else:
            print(f"  Chunk {i+1}: Error {response.status_code}")
            return False
    
    # Combine audio chunks
    with open(output_path.replace(".mp3", ".raw"), "wb") as f:
        for a in all_audio:
            f.write(a)
    
    # Convert to WAV then MP3
    raw_path = output_path.replace(".mp3", ".raw")
    wav_path = output_path.replace(".mp3", ".wav")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
        "-i", raw_path, wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Get duration and adjust speed if needed
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    target = config["video"].get("target_duration", 60)
    
    # Apply speed adjustment if needed
    if duration > 0 and target > 0:
        speed = duration / target
        if speed > 1.1 or speed < 0.9:
            print(f"  Adjusting speed: {speed:.2f}x")
            subprocess.run([
                "ffmpeg", "-y", "-i", wav_path,
                "-filter:a", f"atempo={speed}",
                wav_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Add fade out
    fade = config["audio"].get("fade_out", 8)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-af", f"afade=t=out:st={target-fade}:d={fade}",
        "-codec:a", "libmp3lame", "-b:a", "128k", output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup
    for f in [raw_path, wav_path]:
        if os.path.exists(f):
            os.remove(f)
    
    print(f"✅ Audio saved: {output_path}")
    return True

def generate_slides(text, config, output_dir):
    """Generate video slides from text"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean old slides first
    for f in Path(output_dir).glob("slide_*.mp4"):
        os.remove(f)
    
    sections = config.get("text", {}).get("sections", [])
    if not sections:
        # Auto-generate sections from text
        sections = [{"title": "VIDEO", "duration": 5}]
    
    print(f"🎬 Generating slides ({len(sections)} sections)...")
    
    for i, section in enumerate(sections):
        title = section.get("title", f"Section {i+1}")
        duration = section.get("duration", 5)
        
        # Create slide with text
        slide_path = f"{output_dir}/slide_{i:02d}.mp4"
        
        # Escape text for ffmpeg
        title_escaped = title.replace("'", "\\'").replace(":", "\\:")
        
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={config['video']['width']}x{config['video']['height']}:d={duration}",
            "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{title_escaped}':fontsize=72:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2:borderw=3:bordercolor=black",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            slide_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"  Slide {i+1}: {title} ({duration}s)")
    
    return True

def combine_video_audio(slides_dir, audio_path, output_path):
    """Combine slides and audio into final video"""
    print("🎥 Combining video and audio...")
    
    # Get all slides
    slides = sorted(Path(slides_dir).glob("slide_*.mp4"))
    if not slides:
        print("❌ No slides found")
        return False
    
    print(f"  Using {len(slides)} slides")
    print(f"  Audio: {audio_path}")
    
    # Build ffmpeg command with filter_complex
    inputs = []
    for slide in slides:
        inputs.extend(["-i", str(slide.absolute())])
    inputs.extend(["-i", audio_path])
    
    # Build filter_complex for video concatenation
    filter_parts = []
    for i in range(len(slides)):
        filter_parts.append(f"[{i}:v]")
    filter_str = f"concat=n={len(slides)}:v=1:a=0[outv]"
    
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", f"{''.join(filter_parts)}{filter_str}",
        "-map", "[outv]", "-map", f"{len(slides)}:a",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
        "-shortest", output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
    
    if not os.path.exists(output_path):
        print(f"❌ Failed to create video")
        return False
    
    # Get final duration
    try:
        dur_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output_path],
            capture_output=True, text=True, timeout=10
        )
        duration = float(dur_result.stdout.strip()) if dur_result.stdout.strip() else 0
        print(f"✅ Video saved: {output_path} ({duration:.1f}s)")
    except:
        print(f"✅ Video saved: {output_path}")
    
    return True

def generate_video(config_path="config.yaml"):
    """Main video generation pipeline"""
    config = load_config(config_path)
    
    # Get text content
    text = config.get("text", {}).get("content", "")
    if not text:
        print("❌ No text content in config")
        return False
    
    # Paths
    audio_path = config.get("output", {}).get("audio", "assets/audio/voiceover.mp3")
    slides_dir = config.get("output", {}).get("slides", "assets/slides")
    video_path = config.get("output", {}).get("video", "videos/output.mp3")
    
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    os.makedirs(slides_dir, exist_ok=True)
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    # Step 1: Generate audio
    if not generate_audio_inworld(text, config, audio_path):
        return False
    
    # Step 2: Generate slides
    if not generate_slides(text, config, slides_dir):
        return False
    
    # Step 3: Combine
    if not combine_video_audio(slides_dir, audio_path, video_path):
        return False
    
    print(f"\n🎉 Done! Output: {video_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Video Generator")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()
    
    generate_video(args.config)