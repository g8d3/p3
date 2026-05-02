#!/usr/bin/env python3
"""
AI Content Factory - Text to Speech
Uses free TTS APIs for narration
"""

import subprocess
import os
import json
import base64
import uuid
from datetime import datetime
from pathlib import Path

class FreeTTS:
    """Free TTS using various backends"""
    
    def __init__(self, output_dir="~/Videos/ai-content/assets"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.backend = self._detect_backend()
        print(f"TTS Backend: {self.backend}")
    
    def _detect_backend(self):
        """Detect available TTS backend"""
        # Check for espeak
        if self._command_exists("espeak"):
            return "espeak"
        if self._command_exists("espeak-ng"):
            return "espeak-ng"
        
        # Check for curl (for API-based TTS)
        if self._command_exists("curl"):
            return "curl"  # Can use free APIs
        
        return None
    
    def _command_exists(self, cmd):
        result = subprocess.run(["which", cmd], capture_output=True)
        return result.returncode == 0
    
    def speak(self, text, output_path=None, voice="af_sarah"):
        """Convert text to speech"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"tts_{timestamp}.mp3")
        
        if self.backend in ["espeak", "espeak-ng"]:
            return self._espeak_speak(text, output_path)
        elif self.backend == "curl":
            return self._puter_tts(text, output_path, voice)
        else:
            print("No TTS available!")
            return None
    
    def _espeak_speak(self, text, output_path):
        """Use espeak for TTS"""
        cmd = [
            "espeak" if self.backend == "espeak" else "espeak-ng",
            "-w", output_path,
            "-s", "140",  # Speed
            text
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Generated TTS: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Espeak failed: {e}")
            return None
    
    def _google_tts(self, text, output_path):
        """Use Google Translate TTS (free, no API key)"""
        # Escape text for URL
        import urllib.parse
        text_encoded = urllib.parse.quote(text)
        
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={text_encoded}&tl=en&client=tw-ob"
        
        try:
            cmd = [
                "curl", "-s",
                "-A", "Mozilla/5.0",
                url,
                "--output", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Check if we got audio
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                print(f"Generated TTS: {output_path}")
                return output_path
            
        except Exception as e:
            print(f"Google TTS error: {e}")
        
        return None
    
    def _puter_tts(self, text, output_path, voice="af_sarah"):
        """Try various free TTS APIs"""
        # Try Google Translate TTS first
        result = self._google_tts(text, output_path)
        if result:
            return result
        
        # Fallback to espeak
        return self._espeak_speak(text, output_path)
    
    def text_to_narration(self, topic, outline):
        """Convert topic outline to full narration script"""
        parts = []
        
        # Hook
        topic_clean = topic.replace("-", "").replace(":", "")
        parts.append(f"Welcome! In this video, we'll learn how to {topic_clean}. This is going to be amazing, so stick around!")
        
        # Outline sections
        for section in outline:
            section_clean = section.split(":")[-1].strip() if ":" in section else section
            
            if "intro" in section_clean.lower():
                parts.append(f"Let's start with {section_clean}. This is what we'll be building today.")
            elif "prerequisite" in section_clean.lower():
                parts.append(f"Before we begin, make sure you have everything needed for {section_clean}.")
            elif "step 1" in section_clean.lower():
                parts.append(f"Step one: {section_clean}. Let me show you how.")
            elif "step 2" in section_clean.lower():
                parts.append(f"Step two: {section_clean}. Follow along carefully.")
            elif "step 3" in section_clean.lower():
                parts.append(f"Now step three: {section_clean}. This is the key part.")
            elif "step" in section_clean.lower():
                parts.append(f"Next: {section_clean}. Keep going!")
            elif "outro" in section_clean.lower() or "summary" in section_clean.lower():
                parts.append(f"That's a wrap! To summarize: {section_clean}. Thanks for watching!")
            else:
                parts.append(f"Next up: {section_clean}.")
        
        # CTA
        parts.append("If you found this helpful, please like and subscribe! See you in the next video!")
        
        return " ".join(parts)


class VoiceRecorder:
    """Record voice narration from microphone"""
    
    def __init__(self, output_dir="~/Videos/ai-content/assets"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def record(self, duration=30, output_path=None):
        """Record voice for given duration"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"voice_{timestamp}.wav")
        
        # Check for audio input
        try:
            subprocess.run(["arecord", "-l"], capture_output=True, check=True)
            
            cmd = [
                "ffmpeg",
                "-f", "alsa",
                "-i", "plughw:0",
                "-t", str(duration),
                "-y",
                output_path
            ]
            
            print(f"Recording voice for {duration} seconds...")
            print("Press Ctrl+C to stop early")
            subprocess.run(cmd, check=True)
            print(f"Voice recorded: {output_path}")
            return output_path
        except:
            print("No microphone found!")
            return None


def test_tts():
    """Test TTS"""
    tts = FreeTTS()
    
    if tts.backend:
        print(f"\nTesting {tts.backend}...")
        
        # Test narration generation
        test_topic = "Build an AI App with Claude Code"
        test_outline = [
            "INTRO: What we'll build",
            "STEP 1: Setup",
            "STEP 2: Implementation",
            "OUTRO: Summary"
        ]
        
        narration = tts.text_to_narration(test_topic, test_outline)
        print(f"\nNarration: {narration[:200]}...")
        
        audio = tts.speak(narration)
        if audio:
            print(f"Generated: {audio}")
    else:
        print("\nNo TTS backend!")
        print("Install: sudo apt install espeak espeak-ng curl")


if __name__ == "__main__":
    test_tts()
