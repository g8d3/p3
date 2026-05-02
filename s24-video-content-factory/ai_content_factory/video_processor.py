#!/usr/bin/env python3
"""
AI Content Factory - Video Processor
Video processing pipeline with ffmpeg
"""

import subprocess
import os
import json
from pathlib import Path
from datetime import datetime

class VideoProcessor:
    def __init__(self, assets_dir="~/Videos/ai-content/assets"):
        self.assets_dir = os.path.expanduser(assets_dir)
        os.makedirs(self.assets_dir, exist_ok=True)
    
    def generate_intro(self, title, duration=5, output_path=None):
        """Generate intro with title using ffmpeg"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.assets_dir, f"intro_{timestamp}.mp4")
        
        # Create a simple colored intro with text overlay
        # Using drawtext filter for title
        escaped_title = title.replace("'", "\\'").replace(":", "\\:")
        
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "color=c=0x1a1a2e:s=1280x720:d=5",  # Dark blue background
            "-vf", f"drawtext=text='{escaped_title}':fontcolor=white:fontsize=48:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:x=(w-text_w)/2:y=(h-text_h)/2,drawtext=text='AI Builder':fontcolor=0x4cc9f0:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+60",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"Error generating intro: {e}")
            # Fallback: just create solid color
            return self.generate_simple_intro(duration, output_path)
    
    def generate_simple_intro(self, duration, output_path):
        """Generate simple intro without text"""
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s=1280x720:d={duration}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return output_path
    
    def generate_outro(self, duration=5, output_path=None):
        """Generate outro with call-to-action"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.assets_dir, f"outro_{timestamp}.mp4")
        
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=0x16213e:s=1280x720:d={duration}",
            "-vf", "drawtext=text='Subscribe & Like!':fontcolor=white:fontsize=48:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except:
            return self.generate_simple_intro(duration, output_path)
        
        return output_path
    
    def concatenate_videos(self, video_paths, output_path):
        """Concatenate multiple videos"""
        # Create concat file
        concat_file = output_path + ".txt"
        with open(concat_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
        
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # Cleanup
        os.remove(concat_file)
        
        return output_path
    
    def add_audio(self, video_path, audio_path, output_path=None):
        """Add audio track to video"""
        if not output_path:
            output_path = video_path.replace(".mp4", "_with_audio.mp4")
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def add_background_music(self, video_path, music_path, volume=0.3, output_path=None):
        """Add background music"""
        if not output_path:
            output_path = video_path.replace(".mp4", "_with_music.mp4")
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def add_subtitles(self, video_path, srt_path, output_path=None):
        """Add subtitles to video"""
        if not output_path:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def create_thumbnail(self, video_path, timestamp="00:00:05", output_path=None):
        """Generate thumbnail from video"""
        if not output_path:
            output_path = video_path.replace(".mp4", "_thumb.jpg")
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", timestamp,
            "-vframes", "1",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def optimize_for_youtube(self, video_path, output_path=None):
        """Optimize video for YouTube upload"""
        if not output_path:
            output_path = video_path.replace(".mp4", "_yt.mp4")
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # Get video info
        info = self.get_video_info(output_path)
        
        return output_path, info
    
    def get_video_info(self, video_path):
        """Get video metadata"""
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-hide_banner"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr
        
        info = {}
        
        # Parse duration
        import re
        dur_match = re.search(r'Duration: (\d+):(\d+):(\d+)\.(\d+)', output)
        if dur_match:
            h, m, s, ms = dur_match.groups()
            info['duration'] = int(h) * 3600 + int(m) * 60 + int(s)
        
        # Parse resolution
        res_match = re.search(r'(\d+)x(\d+)', output)
        if res_match:
            info['width'] = int(res_match.group(1))
            info['height'] = int(res_match.group(2))
        
        return info
    
    def process_full_video(self, main_video, title, add_intro=True, add_outro=True):
        """Full processing pipeline"""
        print(f"Processing: {title}")
        
        videos = []
        
        # Add intro
        if add_intro:
            intro_path = self.generate_intro(title)
            videos.append(intro_path)
        
        # Add main video
        videos.append(main_video)
        
        # Add outro
        if add_outro:
            outro_path = self.generate_outro()
            videos.append(outro_path)
        
        # Concatenate
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            self.assets_dir, 
            f"final_{timestamp}.mp4"
        )
        
        self.concatenate_videos(videos, output_path)
        
        # Optimize
        final_path, info = self.optimize_for_youtube(output_path)
        
        # Thumbnail
        thumb_path = self.create_thumbnail(final_path)
        
        # Cleanup intermediate files
        for v in videos:
            if v != main_video:
                try:
                    os.remove(v)
                except:
                    pass
        
        return {
            "video_path": final_path,
            "thumbnail_path": thumb_path,
            "info": info
        }


def test_processor():
    """Test video processor"""
    processor = VideoProcessor()
    print("Video processor initialized")
    print(f"Assets dir: {processor.assets_dir}")

if __name__ == "__main__":
    test_processor()
