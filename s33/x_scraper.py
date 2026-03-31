"""
AutoContent - X.com Scraper
Scrapes likes and bookmarks from x.com using CDP browser
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from logger import logger
from error_handler import self_healer, ErrorContext


@dataclass
class XPost:
    """X.com post data"""
    post_id: str
    author: str
    author_handle: str
    content: str
    created_at: str
    likes: int = 0
    retweets: int = 0
    bookmarks: int = 0
    url: str = ""
    media: list[str] = field(default_factory=list)
    is_bookmark: bool = False
    is_like: bool = False


class XScraper:
    """X.com scraper using CDP browser"""
    
    def __init__(self, session_file: str = "x_session.json"):
        self.session_file = session_file
        self.posts: list[XPost] = []
        self.session_loaded = False
    
    def _run_browser(self, *args) -> subprocess.CompletedProcess:
        """Run agent-browser command"""
        cmd = ["agent-browser"] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def _save_session(self):
        """Save browser session"""
        self._run_browser("state", "save", self.session_file)
        logger.info("Browser session saved")
    
    def _load_session(self):
        """Load browser session"""
        result = self._run_browser("state", "load", self.session_file)
        if result.returncode == 0:
            self.session_loaded = True
            logger.info("Browser session loaded")
            return True
        return False
    
    def check_auth(self) -> bool:
        """Check if authenticated to x.com"""
        self._run_browser("open", "https://x.com/home")
        self._run_browser("wait", "--load", "networkidle")
        self._run_browser("snapshot", "-i")
        
        # Check for login or home elements
        result = self._run_browser("get", "url")
        if "login" in result.stdout.lower():
            return False
        return True
    
    def login(self, username: str, password: str) -> bool:
        """Login to x.com"""
        logger.info("Logging into x.com")
        
        self._run_browser("open", "https://x.com/login")
        self._run_browser("wait", "--load", "networkidle")
        self._run_browser("snapshot", "-i")
        
        # Fill username
        self._run_browser("fill", "@e1", username)
        self._run_browser("press", "Enter")
        self._run_browser("wait", "2000")
        self._run_browser("snapshot", "-i")
        
        # Fill password
        self._run_browser("fill", "@e1", password)
        self._run_browser("press", "Enter")
        self._run_browser("wait", "--load", "networkidle")
        
        # Save session
        self._save_session()
        
        return self.check_auth()
    
    def scrape_likes(self, limit: int = 50) -> list[XPost]:
        """Scrape liked posts"""
        logger.info(f"Scraping likes (limit: {limit})")
        
        self._run_browser("open", "https://x.com/i/activity/liked_by")
        self._run_browser("wait", "--load", "networkidle")
        
        posts = []
        scroll_count = 0
        
        while len(posts) < limit:
            self._run_browser("snapshot", "-i")
            self._run_browser("get", "text", "body", "--json")
            
            # Parse posts from page - simplified extraction
            # In production, would parse actual DOM structure
            scroll_count += 1
            self._run_browser("scroll", "down", "1000")
            self._run_browser("wait", "1000")
            
            if scroll_count > 10:  # Safety limit
                break
        
        logger.info(f"Scraped {len(posts)} liked posts")
        return posts
    
    def scrape_bookmarks(self, limit: int = 50) -> list[XPost]:
        """Scrape bookmarked posts"""
        logger.info(f"Scraping bookmarks (limit: {limit})")
        
        self._run_browser("open", "https://x.com/i/activity/saved_bookmarks")
        self._run_browser("wait", "--load", "networkidle")
        
        posts = []
        
        # Scroll to collect posts
        for _ in range(10):
            self._run_browser("snapshot", "-i")
            self._run_browser("scroll", "down", "1000")
            self._run_browser("wait", "1000")
        
        logger.info(f"Scraped {len(posts)} bookmarked posts")
        return posts
    
    def scrape_all(self, likes_limit: int = 50, bookmarks_limit: int = 50) -> list[XPost]:
        """Scrape both likes and bookmarks"""
        logger.info("Starting full x.com scrape")
        
        all_posts = []
        
        # Scrape likes
        likes = self.scrape_likes(likes_limit)
        for post in likes:
            post.is_like = True
        all_posts.extend(likes)
        
        # Scrape bookmarks
        bookmarks = self.scrape_bookmarks(bookmarks_limit)
        for post in bookmarks:
            post.is_bookmark = True
        all_posts.extend(bookmarks)
        
        # Save to file
        self._save_posts(all_posts)
        
        logger.info(f"Total posts scraped: {len(all_posts)}")
        return all_posts
    
    def _save_posts(self, posts: list[XPost]):
        """Save posts to JSON file"""
        with open("data/x_posts.json", "w") as f:
            json.dump([vars(p) for p in posts], f, indent=2)
        logger.info("Posts saved to data/x_posts.json")
    
    def verify_inputs(self) -> bool:
        """Verify scraped data is valid"""
        if not self.posts:
            logger.warning("No posts scraped")
            return False
        
        for post in self.posts:
            if not post.content:
                logger.warning(f"Post {post.post_id} has no content")
                return False
            if not post.author:
                logger.warning(f"Post {post.post_id} has no author")
                return False
        
        logger.info(f"Verified {len(self.posts)} posts")
        return True


def create_scraper() -> XScraper:
    """Factory function to create XScraper"""
    return XScraper()
