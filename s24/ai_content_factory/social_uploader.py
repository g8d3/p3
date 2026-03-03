#!/usr/bin/env python3
"""
AI Content Factory - Social Media Uploader
YouTube, Twitter/X, and more
"""

import os
import json
import subprocess
from datetime import datetime, timedelta

class YouTubeUploader:
    def __init__(self, config_path="~/.config/ai-content-factory/youtube.json"):
        self.config_path = os.path.expanduser(config_path)
        self.load_config()
    
    def load_config(self):
        """Load YouTube API credentials"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            print("No YouTube config found. Set up with:")
            print("  1. Go to Google Cloud Console")
            print("  2. Create OAuth2 credentials")
            print("  3. Save to ~/.config/ai-content-factory/youtube.json")
    
    def upload(self, video_path, title, description, tags=None, 
              category_id="28", privacy_status="private", scheduled_time=None):
        """Upload video to YouTube"""
        
        # Check for yt-dlp/ytupload first (easier than full API)
        if self._check_ytdlp():
            return self._upload_with_ytdlp(
                video_path, title, description, tags, 
                privacy_status, scheduled_time
            )
        
        # Fallback to curl with YouTube Data API
        return self._upload_with_api(
            video_path, title, description, tags,
            category_id, privacy_status, scheduled_time
        )
    
    def _check_ytdlp(self):
        """Check if yt-dlp or youtube-upload is available"""
        result = subprocess.run(
            ["which", "yt-dlp"],
            capture_output=True
        )
        return result.returncode == 0
    
    def _upload_with_ytdlp(self, video_path, title, description, tags,
                          privacy_status, scheduled_time):
        """Upload using yt-dlp (requires cookies or oauth)"""
        
        cmd = [
            "yt-dlp",
            "--upload-file", video_path,
            "--title", title,
            "--description", description,
        ]
        
        if tags:
            cmd.extend(["--add-tags", ",".join(tags)])
        
        if privacy_status:
            cmd.extend(["--privacy", privacy_status])
        
        if scheduled_time:
            cmd.extend(["--scheduled", scheduled_time])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr}
    
    def _upload_with_api(self, video_path, title, description, tags,
                        category_id, privacy_status, scheduled_time):
        """Upload using YouTube Data API v3"""
        
        if not self.config.get("client_secrets"):
            return {"success": False, "error": "No API credentials"}
        
        # This would use the Google APIs Python client
        # For now, return instructions
        return {
            "success": False, 
            "error": "Use yt-dlp or set up OAuth: pip install google-api-python-client"
        }


class TwitterUploader:
    def __init__(self, config_path="~/.config/ai-content-factory/twitter.json"):
        self.config_path = os.path.expanduser(config_path)
        self.load_config()
    
    def load_config(self):
        """Load Twitter API credentials"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def post_video(self, video_path, text, scheduled_time=None):
        """Post video to Twitter/X"""
        
        # Check for twitter-upload CLI
        if self._check_twitter_upload():
            return self._upload_cli(video_path, text, scheduled_time)
        
        # Use twarc or tweepy if available
        return {"success": False, "error": "No Twitter upload tool found"}
    
    def _check_twitter_upload(self):
        """Check for twitter-upload"""
        result = subprocess.run(
            ["which", "twitter-upload"],
            capture_output=True
        )
        return result.returncode == 0
    
    def _upload_cli(self, video_path, text, scheduled_time):
        """Upload using twitter-upload CLI"""
        cmd = ["twitter-upload", video_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            media_id = result.stdout.strip()
            
            # Post tweet with media
            cmd = ["tw", "post", "-m", media_id, text]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {"success": True, "media_id": media_id}
        
        return {"success": False, "error": result.stderr}
    
    def create_thread(self, video_path, thread_texts):
        """Create a Twitter thread with video"""
        # Split text into tweets
        # Upload video first
        # Post each tweet
        pass


class SocialMediaManager:
    """Manage multiple platform uploads"""
    
    def __init__(self):
        self.youtube = YouTubeUploader()
        self.twitter = TwitterUploader()
    
    def upload_all(self, video_path, metadata, platforms=["youtube"]):
        """Upload to multiple platforms"""
        results = {}
        
        title = metadata.get("title", "AI Tutorial")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])
        
        if "youtube" in platforms:
            result = self.youtube.upload(
                video_path, title, description, tags,
                privacy_status="private"  # Start private for review
            )
            results["youtube"] = result
        
        if "twitter" in platforms:
            result = self.twitter.post_video(video_path, description[:280])
            results["twitter"] = result
        
        return results
    
    def schedule_post(self, video_path, metadata, platforms, post_time):
        """Schedule a post for later"""
        # Save to schedule file
        schedule_file = os.path.expanduser("~/.config/ai-content-factory/schedule.json")
        
        schedule = []
        if os.path.exists(schedule_file):
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        
        schedule.append({
            "video_path": video_path,
            "metadata": metadata,
            "platforms": platforms,
            "post_time": post_time.isoformat(),
            "status": "pending"
        })
        
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        return {"success": True, "scheduled": len(schedule)}


def setup_credentials():
    """Create config file templates"""
    config_dir = os.path.expanduser("~/.config/ai-content-factory")
    os.makedirs(config_dir, exist_ok=True)
    
    # YouTube config template
    youtube_config = {
        "client_secrets": "path/to/client_secrets.json",
        "oauth": "path/to/credentials.json"
    }
    
    # Twitter config template  
    twitter_config = {
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "access_token_secret": "YOUR_ACCESS_SECRET"
    }
    
    with open(os.path.join(config_dir, "youtube.json"), 'w') as f:
        json.dump(youtube_config, f, indent=2)
    
    with open(os.path.join(config_dir, "twitter.json"), 'w') as f:
        json.dump(twitter_config, f, indent=2)
    
    print(f"Config templates created in {config_dir}")
    print("Please fill in your API credentials")


if __name__ == "__main__":
    setup_credentials()
