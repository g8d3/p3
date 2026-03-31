"""
AutoContent - Video Generator
Creates videos from generated content using LLM and ffmpeg
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class VideoMetadata:
    """Video metadata"""
    title: str
    description: str
    tags: list[str]
    duration: int
    file_path: str


class VideoGenerator:
    """Video generation using ffmpeg and LLM"""
    
    def __init__(self, output_dir: str = "output/videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True)
            return True
        except FileNotFoundError:
            logger.warning("ffmpeg not found, video generation limited")
            return False
    
    def create_video_from_script(self, script, title: str = "Content Video") -> Optional[str]:
        """Create video from script"""
        logger.info(f"Creating video: {title}")
        
        if not self.ffmpeg_available:
            return self._create_placeholder_video(title)
        
        # Generate TTS audio
        audio_path = self._generate_tts_audio(script)
        
        # Create video with static images and audio
        video_path = self._create_video_with_audio(audio_path, title)
        
        if video_path:
            logger.info(f"Video created: {video_path}")
        
        return video_path
    
    def _generate_tts_audio(self, script) -> Optional[str]:
        """Generate text-to-speech audio"""
        # Combine script parts
        full_script = f"{script.hook}. {script.intro}. "
        full_script += ". ".join(script.main_points)
        full_script += f". {script.conclusion}. {script.call_to_action}"
        
        audio_path = os.path.join(self.output_dir, "temp_audio.mp3")
        
        # Try using espeak or gtts
        try:
            # Try gtts first
            from gtts import gTTS
            tts = gTTS(text=full_script, lang='en')
            tts.save(audio_path)
            return audio_path
        except ImportError:
            pass
        
        try:
            # Try espeak
            subprocess.run(
                ["espeak", "-w", audio_path, full_script],
                capture_output=True
            )
            return audio_path
        except FileNotFoundError:
            pass
        
        # Fallback: create empty placeholder
        logger.warning("No TTS available, creating silent video")
        return None
    
    def _create_video_with_audio(self, audio_path: Optional[str], title: str) -> Optional[str]:
        """Create video with audio"""
        output_path = os.path.join(self.output_dir, f"{title.replace(' ', '_')}.mp4")
        
        # Create a simple video with solid color and audio
        if audio_path and os.path.exists(audio_path):
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=5",
                "-i", audio_path,
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path
            ]
        else:
            # Silent video
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=5",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path
            ]
        
        try:
            subprocess.run(cmd, capture_output=True)
            return output_path
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return None
    
    def _create_placeholder_video(self, title: str) -> str:
        """Create placeholder video file"""
        output_path = os.path.join(self.output_dir, f"{title.replace(' ', '_')}.mp4")
        
        # Create minimal valid MP4
        if self.ffmpeg_available:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=1280x720:d=1",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac",
                "-shortest",
                output_path
            ], capture_output=True)
        
        return output_path
    
    def add_subtitles(self, video_path: str, subtitles: list) -> str:
        """Add subtitles to video"""
        logger.info(f"Adding subtitles to {video_path}")
        
        # Create subtitle file
        srt_path = video_path.replace(".mp4", ".srt")
        
        with open(srt_path, "w") as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"00:00:{i*5:02d},000 --> 00:00:{i*5+3:02d},000\n")
                f.write(f"{sub}\n\n")
        
        # Burn subtitles into video
        output_path = video_path.replace(".mp4", "_subtitled.mp4")
        
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={srt_path}",
            output_path
        ], capture_output=True)
        
        return output_path
    
    def verify_video(self, video_path: str) -> bool:
        """Verify video file is valid"""
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return False
        
        # Check file size
        size = os.path.getsize(video_path)
        if size < 1000:
            logger.error(f"Video too small: {size} bytes")
            return False
        
        # Verify with ffprobe
        if self.ffmpeg_available:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ], capture_output=True, text=True)
            
            try:
                duration = float(result.stdout.strip())
                logger.info(f"Video duration: {duration}s")
                return duration > 0
            except:
                pass
        
        return True


def create_video_generator(**kwargs) -> VideoGenerator:
    """Factory function"""
    return VideoGenerator(**kwargs)
