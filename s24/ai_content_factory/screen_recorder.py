#!/usr/bin/env python3
"""
AI Content Factory - Screen Recorder
Automated screen recording with ffmpeg
"""

import subprocess
import os
import signal
import time
import json
from datetime import datetime
from pathlib import Path

class ScreenRecorder:
    def __init__(self, output_dir="~/Videos/ai-content"):
        self.output_dir = os.path.expanduser(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.process = None
        self.recording = False
        self.display = os.environ.get("DISPLAY", ":0")
        
    def get_display_info(self):
        """Get display resolution and info"""
        try:
            result = subprocess.run(
                ["xrandr", "-d", self.display],
                capture_output=True,
                text=True,
                env={**os.environ, "DISPLAY": self.display}
            )
            # Parse resolution
            for line in result.stdout.split('\n'):
                if '*' in line:
                    res = line.split()[0]
                    width, height = res.split('x')
                    return {"width": int(width), "height": int(height)}
        except Exception as e:
            print(f"xrandr failed: {e}")
        # Default fallback
        return {"width": 1920, "height": 1080}
    
    def get_audio_devices(self):
        """Get available audio input devices"""
        try:
            result = subprocess.run(
                ["pactl", "list", "short", "sources"],
                capture_output=True,
                text=True
            )
            devices = []
            for line in result.stdout.split('\n'):
                if 'pulse' in line.lower():
                    continue
                parts = line.split()
                if parts:
                    devices.append(parts[0])
            return devices
        except:
            return []
    
    def start_recording(self, filename=None, duration=None, audio=False):
        """Start screen recording"""
        if self.recording:
            print("Already recording!")
            return None
        
        display = self.get_display_info()
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}"
        
        output_path = os.path.join(self.output_dir, f"{filename}.mp4")
        
        # Build ffmpeg command
        # Use X11 capture
        cmd = [
            "ffmpeg",
            "-f", "x11grab",
            "-framerate", "30",
            "-video_size", f"{display['width']}x{display['height']}",
            "-i", f"{self.display}.0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
        ]
        
        has_audio = False
        # Add audio if requested and available
        if audio:
            # Try pulseaudio first, then alsa
            try:
                result = subprocess.run(["pactl", "list", "short", "sources"], 
                                       capture_output=True, text=True)
                if result.returncode == 0 and "default" in result.stdout:
                    cmd.extend(["-f", "pulse", "-i", "default"])
                    has_audio = True
            except:
                pass
            
            if not has_audio:
                try:
                    result = subprocess.run(["arecord", "-l"], 
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        cmd.extend(["-f", "alsa", "-i", "plughw:0"])
                        has_audio = True
                except:
                    pass
        
        # Output settings
        if has_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        cmd.extend(["-y", output_path])
        
        print(f"Starting recording: {output_path}")
        print(f"Display: {self.display}")
        
        # Launch content to show on screen (terminal, browser, etc.)
        self._launch_content()
        
        print(f"Command: {' '.join(cmd)}")
        
        # Start recording
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.recording = True
        self.output_path = output_path
        
        # If duration specified, stop after that time
        if duration:
            print(f"Recording for {duration} seconds...")
            time.sleep(duration)
            self.stop_recording()
        
        return output_path
    
    def _launch_content(self):
        """Launch content on screen to make recording engaging"""
        # Try to open a terminal with some content
        try:
            # Open terminal with a coding command
            subprocess.Popen([
                "xterm",
                "-geometry", "100x30",
                "-bg", "black",
                "-fg", "green",
                "-e", "echo '🎬 Recording...'; echo 'Run: python3 --version'; python3 --version; echo ''; echo 'Ready!'; sleep 5"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Launched terminal for engagement")
        except:
            # Try gnome-terminal
            try:
                subprocess.Popen([
                    "gnome-terminal", "--", "bash", "-c",
                    "echo 'Recording...'; python3 --version; sleep 5"
                ])
            except:
                # Try xdg-open for something visual
                try:
                    subprocess.Popen(["xdg-open", "https://github.com"])
                except:
                    pass
    
    def stop_recording(self):
        """Stop the recording"""
        if not self.recording or not self.process:
            print("Not recording")
            return None
        
        # Send SIGTERM to gracefully stop
        self.process.terminate()
        
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        
        self.recording = False
        print(f"Recording saved to: {self.output_path}")
        
        return self.output_path
    
    def record_with_countdown(self, duration=300, countdown=5):
        """Record with countdown before starting"""
        print(f"Recording starting in {countdown} seconds...")
        for i in range(countdown, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        print("Recording!")
        return self.start_recording(duration=duration)

# Automated demo recording functions
class DemoRecorder:
    """Records specific demo scenarios"""
    
    def __init__(self, recorder):
        self.recorder = recorder
    
    def record_terminal_demo(self, commands, output_file="demo.mp4"):
        """
        Record a terminal demo by executing commands
        commands: list of (command, wait_time) tuples
        """
        # This would integrate with terminal automation
        # For now, just start recording
        print(f"Recording terminal demo: {output_file}")
        return self.recorder.start_recording(
            filename=output_file.replace(".mp4", ""),
            duration=60  # Default 1 min
        )
    
    def record_browser_demo(self, url, actions, output_file="browser.mp4"):
        """Record browser demo (requires browser automation)"""
        print(f"Recording browser demo at {url}")
        return self.recorder.start_recording(
            filename=output_file.replace(".mp4", ""),
            duration=120
        )
    
    def record_code_demo(self, file_path, output_file="code.mp4"):
        """Record code editing session"""
        print(f"Recording code demo: {file_path}")
        return self.recorder.start_recording(
            filename=output_file.replace(".mp4", ""),
            duration=180
        )


def test_recorder():
    """Test the recorder"""
    recorder = ScreenRecorder()
    
    print("Display info:", recorder.get_display_info())
    print("Audio devices:", recorder.get_audio_devices())
    
    # Start a 10-second test recording
    print("\nStarting 10-second test recording...")
    recorder.start_recording("test_recording", duration=10)
    
    print("Test complete!")

if __name__ == "__main__":
    test_recorder()
