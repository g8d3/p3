"""
AutoContent - Main Orchestrator
Automated content creation from X.com likes and bookmarks
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional

# Import modules
from config import config, Config
from logger import logger
from error_handler import self_healer
from x_scraper import XScraper, create_scraper
from llm_processor import LLMProcessor, create_processor
from video_generator import VideoGenerator, create_video_generator
from github_manager import GitHubManager, create_github_manager
from provisioner import Provisioner, create_provisioner
from scheduler import TaskScheduler, create_scheduler


class AutoContentOrchestrator:
    """Main orchestrator for automated content creation"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.scraper: Optional[XScraper] = None
        self.llm: Optional[LLMProcessor] = None
        self.video_gen: Optional[VideoGenerator] = None
        self.github: Optional[GitHubManager] = None
        self.provisioner: Optional[Provisioner] = None
        self.scheduler: Optional[TaskScheduler] = None
        
        self.initialized = False
        self.last_content: Optional[dict] = None
    
    def initialize(self) -> bool:
        """Initialize all components"""
        logger.info("Initializing AutoContent Orchestrator")
        
        # Create directories
        for dir_path in [self.config.data_dir, self.config.logs_dir, 
                        self.config.output_dir, self.config.videos_dir, 
                        self.config.code_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Initialize provisioner
        self.provisioner = create_provisioner()
        required = ["github", "x", "llm", "video"]
        if not self.provisioner.provision_all(required):
            logger.warning("Some services not provisioned")
        
        if not self.provisioner.verify_provisioning():
            logger.error("Provisioning verification failed")
            return False
        
        # Initialize components
        self.scraper = create_scraper(self.config.x.session_file)
        self.llm = create_processor(
            self.config.llm.api_key,
            provider=self.config.llm.provider,
            model=self.config.llm.model,
            base_url=self.config.llm.base_url
        )
        self.video_gen = create_video_generator(self.config.videos_dir)
        self.github = create_github_manager(self.config.github.token)
        
        # Initialize scheduler
        self.scheduler = create_scheduler(
            self.config.scheduler.check_interval_minutes
        )
        
        self.initialized = True
        logger.info("AutoContent initialized successfully")
        return True
    
    def verify_inputs(self) -> bool:
        """Verify all inputs are valid"""
        logger.info("Verifying inputs")
        
        # Check LLM API key
        if not self.config.llm.api_key:
            logger.error("LLM API key not configured")
            return False
        
        # Check GitHub token if needed
        if self.config.github.token:
            logger.info("GitHub token configured")
        
        # Check X credentials
        if not self.config.x.username or not self.config.x.password:
            logger.warning("X credentials not fully configured")
        
        logger.info("Input verification complete")
        return True
    
    def scrape_x(self) -> list:
        """Scrape X.com likes and bookmarks"""
        logger.info("Scraping X.com")
        
        # Check auth
        if not self.scraper.check_auth():
            logger.info("Need to login to X.com")
            if self.config.x.username and self.config.x.password:
                self.scraper.login(
                    self.config.x.username,
                    self.config.x.password
                )
            else:
                logger.error("X.com login credentials required")
                return []
        
        # Scrape
        posts = self.scraper.scrape_all(
            likes_limit=50,
            bookmarks_limit=50
        )
        
        # Verify output
        if self.config.verify_outputs:
            if not self._verify_posts(posts):
                logger.error("Post verification failed")
                return []
        
        logger.info(f"Scraped {len(posts)} posts")
        return posts
    
    def _verify_posts(self, posts: list) -> bool:
        """Verify scraped posts"""
        if not posts:
            return False
        
        for post in posts:
            if not hasattr(post, 'content') or not post.content:
                logger.warning("Post missing content")
                return False
        
        return True
    
    def generate_content(self, posts: list) -> dict:
        """Generate content from posts"""
        logger.info("Generating content")
        
        if not posts:
            logger.warning("No posts to generate content from")
            return {}
        
        # Generate main content
        content = self.llm.generate_content(posts)
        
        # Generate video script
        video_script = self.llm.generate_video_script(content)
        
        # Generate code if applicable
        code = self.llm.generate_code(content)
        
        result = {
            "content": content,
            "video_script": video_script,
            "code": code,
            "generated_at": datetime.now().isoformat()
        }
        
        self.last_content = result
        return result
    
    def create_video(self, video_script) -> str:
        """Create video from script"""
        logger.info("Creating video")
        
        video_path = self.video_gen.create_video_from_script(
            video_script,
            title=video_script.hook[:30]
        )
        
        if video_path and self.config.verify_outputs:
            if not self.video_gen.verify_video(video_path):
                logger.error("Video verification failed")
                return ""
        
        return video_path or ""
    
    def create_pr(self, code: str, repo: str = "") -> str:
        """Create GitHub PR with code"""
        logger.info("Creating GitHub PR")
        
        if not code:
            logger.warning("No code to create PR with")
            return ""
        
        if not self.config.github.default_repo:
            logger.warning("No default repo configured")
            return ""
        
        pr_url = self.github.create_code_pr(
            code,
            repo or self.config.github.default_repo,
            title="Auto-generated code from X.com content"
        )
        
        return pr_url or ""
    
    def run_full_cycle(self) -> bool:
        """Run a full content creation cycle"""
        logger.info("Starting full content creation cycle")
        
        try:
            # 1. Scrape X.com
            posts = self.scrape_x()
            if not posts:
                logger.error("No posts scraped, aborting cycle")
                return False
            
            # 2. Generate content
            result = self.generate_content(posts)
            if not result:
                logger.error("Content generation failed")
                return False
            
            # 3. Create video
            if result.get("video_script"):
                video_path = self.create_video(result["video_script"])
                result["video_path"] = video_path
            
            # 4. Create PR if code generated
            if result.get("code"):
                pr_url = self.create_pr(result["code"])
                result["pr_url"] = pr_url
            
            # 5. Save results
            self._save_results(result)
            
            logger.info("Full cycle completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Full cycle failed: {e}")
            return False
    
    def _save_results(self, result: dict):
        """Save results to file"""
        output_file = os.path.join(
            self.config.output_dir,
            f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Convert dataclasses to dicts
        save_data = {}
        if result.get("content"):
            save_data["content"] = {
                "title": result["content"].title,
                "body": result["content"].body,
                "summary": result["content"].summary,
                "tags": result["content"].tags
            }
        
        if result.get("video_script"):
            save_data["video_script"] = {
                "hook": result["video_script"].hook,
                "intro": result["video_script"].intro,
                "main_points": result["video_script"].main_points,
                "conclusion": result["video_script"].conclusion,
                "call_to_action": result["video_script"].call_to_action
            }
        
        save_data["video_path"] = result.get("video_path", "")
        save_data["pr_url"] = result.get("pr_url", "")
        save_data["generated_at"] = result.get("generated_at", "")
        
        with open(output_file, "w") as f:
            json.dump(save_data, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
    
    def start_scheduled(self):
        """Start scheduled content creation"""
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return
        
        # Add main task
        self.scheduler.add_task(
            "content_creation",
            self.run_full_cycle,
            self.config.scheduler.content_generation_interval_hours
        )
        
        self.scheduler.start()
        logger.info("Scheduled content creation started")
    
    def stop_scheduled(self):
        """Stop scheduled content creation"""
        if self.scheduler:
            self.scheduler.stop()
    
    def get_status(self) -> dict:
        """Get system status"""
        status = {
            "initialized": self.initialized,
            "last_run": datetime.now().isoformat()
        }
        
        if self.provisioner:
            status["provisioning"] = self.provisioner.get_status()
        
        if self.scheduler:
            status["scheduler"] = self.scheduler.get_status()
        
        return status


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║          AutoContent - Automated Content Creation         ║
║                                                           ║
║  Inputs: X.com likes and bookmarks                        ║
║  Outputs: Content, videos, code, GitHub PRs               ║
║                                                           ║
║  Requirements: LLM API key, CDP browser, wallet/card      ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Create orchestrator
    orchestrator = AutoContentOrchestrator()
    
    # Initialize
    if not orchestrator.initialize():
        logger.error("Failed to initialize")
        sys.exit(1)
    
    # Verify inputs
    if not orchestrator.verify_inputs():
        logger.error("Input verification failed")
        sys.exit(1)
    
    # Check for scheduled mode
    if "--schedule" in sys.argv:
        orchestrator.start_scheduled()
        logger.info("Running in scheduled mode. Press Ctrl+C to stop.")
        try:
            while True:
                import time
                time.sleep(60)
        except KeyboardInterrupt:
            orchestrator.stop_scheduled()
            logger.info("Stopped")
    else:
        # Run single cycle
        success = orchestrator.run_full_cycle()
        if success:
            print("\n✓ Content creation cycle completed!")
        else:
            print("\n✗ Content creation cycle failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
