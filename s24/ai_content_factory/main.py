#!/usr/bin/env python3
"""
AI Content Factory - Main Orchestration
Ties all components together for automated content creation
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from topic_generator import SmartTopicGenerator as TopicGenerator
from screen_recorder import ScreenRecorder, DemoRecorder
from video_processor import VideoProcessor
from social_uploader import SocialMediaManager
from scheduler import ContentScheduler, PresetSchedules

# Try to import TTS (optional)
try:
    from tts_engine import FreeTTS as TTSEngine, VoiceRecorder
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    print("Note: TTS not available. Install espeak or run: pip install gtts")

class ContentFactory:
    """Main orchestrator for AI content creation"""
    
    def __init__(self, config_dir="~/.config/ai-content-factory"):
        self.config_dir = os.path.expanduser(config_dir)
        self.data_dir = os.path.join(self.config_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize components
        self.recorder = ScreenRecorder()
        self.processor = VideoProcessor()
        self.social = SocialMediaManager()
        self.scheduler = ContentScheduler()
        
        # TTS (optional)
        if HAS_TTS:
            self.tts = TTSEngine()
            self.voice_recorder = VoiceRecorder()
        
        # State file
        self.state_file = os.path.join(self.data_dir, "state.json")
        self.load_state()
    
    def load_state(self):
        """Load factory state"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "current_topic": None,
                "recordings": [],
                "processed": [],
                "uploaded": [],
                "content_plan": []
            }
    
    def save_state(self):
        """Save factory state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def generate_topics(self, niche="ai", count=7):
        """Generate content topics"""
        print(f"Generating {count} topics for {niche}...")
        
        generator = TopicGenerator(niche)
        topics = generator.generate_batch(count)
        
        # Save to content plan
        plan_file = os.path.join(self.data_dir, "content_plan.json")
        with open(plan_file, 'w') as f:
            json.dump(topics, f, indent=2)
        
        self.state["content_plan"] = topics
        self.save_state()
        
        print(f"Generated {len(topics)} topics")
        for i, topic in enumerate(topics, 1):
            print(f"  {i}. {topic['topic']}")
        
        return topics
    
    def get_next_topic(self):
        """Get the next topic to work on"""
        plan = self.state.get("content_plan", [])
        
        for topic in plan:
            if topic.get("status") != "completed":
                return topic
        
        return None
    
    def record_content(self, topic_id=None, duration=300):
        """Record screen content for a topic"""
        # Get topic
        if topic_id:
            topic = next((t for t in self.state["content_plan"] if t["id"] == topic_id), None)
        else:
            topic = self.get_next_topic()
        
        if not topic:
            print("No topic available. Generate topics first.")
            return None
        
        print(f"Recording: {topic['topic']}")
        
        # Start recording
        filename = f"raw_{topic['id']}"
        video_path = self.recorder.start_recording(
            filename=filename,
            duration=duration
        )
        
        # Update state
        self.state["current_topic"] = topic
        self.state["last_recording"] = video_path
        self.save_state()
        
        return video_path
    
    def process_content(self, video_path=None, title=None):
        """Process recorded content"""
        if not video_path:
            video_path = self.state.get("last_recording")
        
        if not video_path or not os.path.exists(video_path):
            print("No video to process")
            return None
        
        if not title:
            topic = self.state.get("current_topic", {})
            title = topic.get("topic", "AI Tutorial")
        
        print(f"Processing: {title}")
        
        result = self.processor.process_full_video(
            video_path,
            title,
            add_intro=True,
            add_outro=True
        )
        
        self.state["last_processed"] = result["video_path"]
        self.state["last_thumbnail"] = result["thumbnail_path"]
        self.save_state()
        
        print(f"Processed video: {result['video_path']}")
        print(f"Thumbnail: {result['thumbnail_path']}")
        print(f"Duration: {result['info'].get('duration', 'unknown')}s")
        
        return result
    
    def upload_content(self, platforms=["youtube"]):
        """Upload content to social platforms"""
        video_path = self.state.get("last_processed")
        
        if not video_path or not os.path.exists(video_path):
            print("No processed video to upload")
            return None
        
        topic = self.state.get("current_topic", {})
        
        metadata = {
            "title": topic.get("topic", "AI Tutorial"),
            "description": self._generate_description(topic),
            "tags": self._generate_tags(topic)
        }
        
        print(f"Uploading to {platforms}...")
        
        results = self.social.upload_all(video_path, metadata, platforms)
        
        for platform, result in results.items():
            status = "✓" if result.get("success") else "✗"
            print(f"  {status} {platform}: {result.get('error', 'Uploaded')}")
        
        return results
    
    def _generate_description(self, topic):
        """Generate video description"""
        outline = topic.get("outline", [])
        outline_text = "\n".join([f"- {item}" for item in outline])
        
        return f"""
{topic.get('topic', 'AI Tutorial')}

In this tutorial, we'll cover:
{outline_text}

#AI #Coding #Tutorial #Programming #TechBusiness
        """.strip()
    
    def _generate_tags(self, topic):
        """Generate hashtags/tags"""
        niche = topic.get("niche", "ai")
        return ["AI", "Tutorial", "Coding", niche.title(), "Tech"]
    
    def _generate_tts_narration(self, topic):
        """Generate TTS narration from topic outline"""
        if not HAS_TTS:
            print("TTS not available!")
            return None
        
        # Create narration text from outline
        outline = topic.get("outline", [])
        topic_title = topic.get("topic", "AI Tutorial")
        
        # Build narration
        narration_parts = [
            f"Welcome to this tutorial on {topic_title}.",
        ]
        
        for section in outline:
            narration_parts.append(f"Now let's discuss {section}.")
        
        narration_parts.append("Thanks for watching! Don't forget to like and subscribe.")
        
        full_narration = " ".join(narration_parts)
        
        # Generate TTS
        print(f"Narration: {full_narration[:100]}...")
        audio_path = self.tts.speak(full_narration)
        
        if audio_path:
            print(f"TTS audio: {audio_path}")
        
        return audio_path
    
    def _record_voice(self, topic):
        """Record voice narration"""
        if not HAS_TTS:
            print("Voice recording not available!")
            return None
        
        duration = 30  # 30 seconds voice recording
        print(f"Recording voice for {duration} seconds...")
        print("Press Ctrl+C when done (or it will auto-stop)")
        
        try:
            audio_path = self.voice_recorder.record(duration=duration)
            if audio_path:
                print(f"Voice recorded: {audio_path}")
            return audio_path
        except KeyboardInterrupt:
            print("Voice recording cancelled")
            return None
    
    def _combine_video_audio(self, video_path, audio_path):
        """Combine video with narration audio"""
        if not video_path or not audio_path:
            return video_path
        
        output_path = video_path.replace(".mp4", "_with_audio.mp4")
        
        # Use ffmpeg to combine - ignore timestamps
        import subprocess
        cmd = [
            "ffmpeg",
            "-re",
            "-i", video_path,
            "-stream_loop", "1",  # Loop video if needed
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-y",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"Combined video: {output_path}")
                return output_path
            else:
                print(f"Combine warning: {result.stderr[:200]}")
        except Exception as e:
            print(f"Failed to combine: {e}")
        
        return video_path
    
    def run_full_pipeline(self, niche="ai", upload=False, use_tts=False, voice=False):
        """Run the complete content pipeline
        
        Args:
            niche: Content niche (ai, crypto, robotics, business)
            upload: Whether to upload after processing (default: False - stop at processing)
            use_tts: Generate text-to-speech narration
            voice: Record voice narration instead of TTS
        """
        print("\n" + "="*50)
        print("AI CONTENT FACTORY - FULL PIPELINE")
        print("="*50 + "\n")
        
        # Step 1: Generate topics if needed
        if not self.state.get("content_plan"):
            self.generate_topics(niche)
        
        topic = self.get_next_topic()
        if not topic:
            print("No topic available!")
            return
        
        print(f"Working on: {topic['topic']}")
        
        # Step 1.5: Generate narration (TTS or voice)
        narration_path = None
        if use_tts and HAS_TTS:
            print("\n--- Generating Narration (TTS) ---")
            narration_path = self._generate_tts_narration(topic)
        elif voice and HAS_TTS:
            print("\n--- Voice Recording ---")
            narration_path = self._record_voice(topic)
        
        # Step 2: Record content (try with audio, fallback to video-only)
        print("\n--- Recording Screen ---")
        print("(Recording 10 seconds...)\n")
        
        # Try record_content first
        video_path = self.record_content(duration=10)
        
        # If that failed, try direct ffmpeg
        if not video_path or not os.path.exists(video_path):
            print("Trying direct ffmpeg...")
            import subprocess
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alt_path = os.path.join(self.recorder.output_dir, f"raw_{timestamp}.mp4")
            result = subprocess.run([
                "ffmpeg", "-f", "x11grab", "-framerate", "30",
                "-video_size", "1920x1080", "-i", ":0.0",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-t", "10", "-y", alt_path
            ], capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(alt_path):
                video_path = alt_path
                print(f"Direct recording saved: {video_path}")
        
        if not video_path or not os.path.exists(video_path):
            print("ERROR: Recording failed. Check X11 display is available.")
            return
        
        print(f"✓ Recording saved: {video_path}")
        self.state["last_recording"] = video_path
        
        # Step 2.5: Combine video with narration if available
        if narration_path and os.path.exists(narration_path):
            print("\n--- Combining Video + Audio ---")
            video_path = self._combine_video_audio(video_path, narration_path)
        
        # Step 3: Process content
        print("\n--- Processing ---")
        result = self.process_content(video_path)
        
        if not result:
            print("Processing failed!")
            return
        
        # Step 4: Upload (only if requested)
        if upload:
            print("\n--- Uploading ---")
            self.upload_content()
        else:
            print("\n--- Upload skipped (use --upload to enable) ---")
        
        # Mark topic complete
        topic = self.state.get("current_topic", {})
        
        # Mark topic complete
        topic = self.state.get("current_topic", {})
        for t in self.state["content_plan"]:
            if t["id"] == topic.get("id"):
                t["status"] = "completed"
                break
        
        self.save_state()
        
        print("\n" + "="*50)
        print("PIPELINE COMPLETE!")
        print("="*50 + "\n")
    
    def setup_automation(self):
        """Set up automated scheduling"""
        print("Setting up automation...")
        
        # Add tasks
        self.scheduler.add_task(
            "generate_topics",
            "0 10 * * 0",  # Sunday 10 AM
            {"niche": "ai", "count": 7}
        )
        
        self.scheduler.add_task(
            "full_pipeline",
            "0 10 * * 1-5",  # Weekdays 10 AM
            {}
        )
        
        self.scheduler.setup_cron()
        
        print("Automation set up!")
        print("  - Sunday 10AM: Generate topics")
        print("  - Weekdays 10AM: Full pipeline")
    
    def status(self):
        """Show factory status"""
        print("\n=== AI Content Factory Status ===\n")
        
        print(f"Content Plan: {len(self.state.get('content_plan', []))} topics")
        
        pending = sum(1 for t in self.state.get("content_plan", []) 
                     if t.get("status") != "completed")
        print(f"  - Pending: {pending}")
        
        completed = sum(1 for t in self.state.get("content_plan", []) 
                       if t.get("status") == "completed")
        print(f"  - Completed: {completed}")
        
        print(f"\nLast Recording: {self.state.get('last_recording', 'None')}")
        print(f"Last Processed: {self.state.get('last_processed', 'None')}")
        
        print("\nScheduled Tasks:")
        for task in self.scheduler.list_tasks():
            status = "✓" if task.get("enabled") else "✗"
            print(f"  {status} {task['type']} - {task['time']}")


def main():
    parser = argparse.ArgumentParser(description="AI Content Factory")
    
    parser.add_argument("--generate", "-g", action="store_true",
                       help="Generate topics")
    parser.add_argument("--niche", "-n", default="ai",
                       choices=["ai", "crypto", "robotics", "business"],
                       help="Content niche")
    parser.add_argument("--count", "-c", type=int, default=7,
                       help="Number of topics to generate")
    
    parser.add_argument("--record", "-r", action="store_true",
                       help="Record screen content")
    parser.add_argument("--duration", "-d", type=int, default=60,
                       help="Recording duration in seconds")
    parser.add_argument("--topic-id", type=str,
                       help="Specific topic ID to record")
    
    parser.add_argument("--process", "-p", action="store_true",
                       help="Process recorded content")
    
    parser.add_argument("--upload", "-u", nargs="+",
                       default=None,
                       help="Upload platforms (use with --full)")
    
    parser.add_argument("--full", "-f", action="store_true",
                       help="Run full pipeline")
    
    parser.add_argument("--tts", "-t", action="store_true",
                       help="Generate TTS narration for videos")
    
    parser.add_argument("--voice", "-v", action="store_true",
                       help="Record voice narration (requires microphone)")
    
    parser.add_argument("--setup", "-s", action="store_true",
                       help="Set up automation")
    
    parser.add_argument("--status", action="store_true",
                       help="Show status")
    
    args = parser.parse_args()
    
    # Create factory
    factory = ContentFactory()
    
    # Run commands
    if args.status:
        factory.status()
    
    elif args.setup:
        factory.setup_automation()
    
    elif args.generate:
        factory.generate_topics(args.niche, args.count)
    
    elif args.record:
        factory.record_content(args.topic_id, args.duration)
    
    elif args.process:
        factory.process_content()
    
    elif args.upload:
        factory.upload_content(args.upload)
    
    elif args.full:
        factory.run_full_pipeline(
            niche=args.niche,
            upload=False,  # Stop before upload by default
            use_tts=args.tts,
            voice=args.voice
        )
    
    else:
        parser.print_help()
        print("\nExample workflows:")
        print("  python3 main.py --generate --niche ai --count 7")
        print("  python3 main.py --record --duration 300")
        print("  python3 main.py --process")
        print("  python3 main.py --full --niche crypto")
        print("  python3 main.py --full --niche ai --tts")
        print("  python3 main.py --setup")


if __name__ == "__main__":
    main()
