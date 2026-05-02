"""
Data Collectors - Gather information from various sources
"""
import asyncio
import logging
import json
import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.core.config import settings
from src.models.content import ContentTopic

logger = logging.getLogger(__name__)

class BaseCollector:
    """Base class for all data collectors"""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    async def collect(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect data for a specific topic"""
        raise NotImplementedError
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return " ".join(text.split())

class RSSCollector(BaseCollector):
    """Collect data from RSS feeds"""
    
    def __init__(self):
        super().__init__()
        self.feeds = {
            ContentTopic.AI_NEWS: [
                "https://techcrunch.com/category/artificial-intelligence/feed/",
                "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
                "https://arstechnica.com/ai/feed/",
                "https://www.wired.com/feed/tag/ai/latest/rss",
            ],
            ContentTopic.GITHUB_NEWS: [
                "https://github.blog/feed/",
                "https://github.com/trending.atom",
            ],
            ContentTopic.TECH_TUTORIALS: [
                "https://dev.to/feed",
                "https://hackernoon.com/feed",
            ],
            ContentTopic.AI_POLITICS: [
                "https://www.politico.com/rss/technology.xml",
            ],
            ContentTopic.AI_BUSINESS: [
                "https://www.businessinsider.com/ai/rss",
                "https://www.forbes.com/ai/feed/",
            ],
            ContentTopic.REAL_VALUE_AI: [
                "https://www.technologyreview.com/feed/",
            ],
        }
    
    async def collect(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect from RSS feeds for a topic"""
        results = []
        feed_urls = self.feeds.get(topic, [])
        
        for url in feed_urls:
            try:
                loop = asyncio.get_event_loop()
                feed_data = await loop.run_in_executor(None, feedparser.parse, url)
                
                for entry in feed_data.entries[:10]:  # Limit to 10 per feed
                    results.append({
                        "title": entry.get("title", ""),
                        "summary": self._clean_text(entry.get("summary", "")),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": feed_data.feed.get("title", ""),
                        "type": "rss",
                    })
            except Exception as e:
                logger.error(f"Error fetching RSS feed {url}: {str(e)}")
        
        logger.info(f"RSSCollector collected {len(results)} items for {topic}")
        return results

class GitHubCollector(BaseCollector):
    """Collect trending repositories and GitHub news"""
    
    def __init__(self):
        super().__init__()
        self.github_token = settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ContentAutomationBot/1.0"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
    
    async def collect(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect GitHub trending repos and news"""
        results = []
        
        if topic == ContentTopic.GITHUB_NEWS:
            # Get trending repositories
            trending = await self._get_trending_repos()
            results.extend(trending)
            
            # Get GitHub blog posts
            blog_posts = await self._get_github_blog_posts()
            results.extend(blog_posts)
        
        logger.info(f"GitHubCollector collected {len(results)} items for {topic}")
        return results
    
    async def _get_trending_repos(self) -> List[Dict[str, Any]]:
        """Get trending repositories from GitHub API"""
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": "created:>2026-03-28",  # Last 4 days
                "sort": "stars",
                "order": "desc",
                "per_page": 20
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=self.headers, params=params, timeout=30)
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for repo in data.get("items", [])[:10]:
                results.append({
                    "title": f"{repo['full_name']} - {repo.get('description', 'No description')}",
                    "summary": repo.get("description", ""),
                    "link": repo["html_url"],
                    "published": repo.get("created_at", ""),
                    "source": "GitHub",
                    "type": "github_trending",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting trending repos: {str(e)}")
            return []
    
    async def _get_github_blog_posts(self) -> List[Dict[str, Any]]:
        """Get GitHub blog posts"""
        try:
            url = "https://github.blog/feed/"
            loop = asyncio.get_event_loop()
            feed_data = await loop.run_in_executor(None, feedparser.parse, url)
            
            results = []
            for entry in feed_data.entries[:5]:
                results.append({
                    "title": entry.get("title", ""),
                    "summary": self._clean_text(entry.get("summary", "")),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": "GitHub Blog",
                    "type": "github_blog",
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting GitHub blog posts: {str(e)}")
            return []

class NewsAPICollector(BaseCollector):
    """Collect news from various news APIs"""
    
    def __init__(self):
        super().__init__()
        self.news_api_key = settings.NEWS_API_KEY
    
    async def collect(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect news from NewsAPI"""
        results = []
        
        if not self.news_api_key:
            logger.warning("NEWS_API_KEY not set, skipping NewsAPI collection")
            return results
        
        topic_queries = {
            ContentTopic.AI_NEWS: "artificial intelligence OR AI OR machine learning",
            ContentTopic.GITHUB_NEWS: "GitHub OR open source OR developer tools",
            ContentTopic.TECH_TUTORIALS: "tutorial OR how-to OR guide programming",
            ContentTopic.AI_POLITICS: "AI policy OR AI regulation OR AI government",
            ContentTopic.AI_BUSINESS: "AI business OR AI enterprise OR AI ROI",
            ContentTopic.REAL_VALUE_AI: "AI practical applications OR AI use cases",
        }
        
        query = topic_queries.get(topic, "artificial intelligence")
        
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": self.news_api_key,
                "from": (datetime.utcnow() - timedelta(days=4)).strftime("%Y-%m-%d"),
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, params=params, timeout=30)
            )
            response.raise_for_status()
            data = response.json()
            
            for article in data.get("articles", [])[:15]:
                results.append({
                    "title": article.get("title", ""),
                    "summary": self._clean_text(article.get("description", "")),
                    "link": article.get("url", ""),
                    "published": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "type": "news_api",
                })
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {str(e)}")
        
        logger.info(f"NewsAPICollector collected {len(results)} items for {topic}")
        return results

class RedditCollector(BaseCollector):
    """Collect trending discussions from Reddit"""
    
    def __init__(self):
        super().__init__()
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.user_agent = settings.REDDIT_USER_AGENT
    
    async def collect(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect from Reddit"""
        results = []
        
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit credentials not set, skipping Reddit collection")
            return results
        
        subreddits = {
            ContentTopic.AI_NEWS: ["artificial", "MachineLearning", "singularity"],
            ContentTopic.GITHUB_NEWS: ["github", "opensource", "programming"],
            ContentTopic.TECH_TUTORIALS: ["learnprogramming", "coding", "webdev"],
            ContentTopic.AI_POLITICS: ["technology", "privacy", "netsec"],
            ContentTopic.AI_BUSINESS: ["business", "startups", "entrepreneur"],
            ContentTopic.REAL_VALUE_AI: ["artificial", "MachineLearning"],
        }
        
        subs = subreddits.get(topic, ["artificial"])
        
        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            
            for subreddit_name in subs:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    for submission in subreddit.hot(limit=10):
                        results.append({
                            "title": submission.title,
                            "summary": self._clean_text(submission.selftext[:500]),
                            "link": f"https://reddit.com{submission.permalink}",
                            "published": datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                            "source": f"r/{subreddit_name}",
                            "type": "reddit",
                            "score": submission.score,
                        })
                except Exception as e:
                    logger.error(f"Error fetching from r/{subreddit_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing Reddit: {str(e)}")
        
        logger.info(f"RedditCollector collected {len(results)} items for {topic}")
        return results

class DataCollectorManager:
    """Manages all data collectors"""
    
    def __init__(self):
        self.collectors = [
            RSSCollector(),
            GitHubCollector(),
            NewsAPICollector(),
            RedditCollector(),
        ]
    
    async def initialize(self):
        """Initialize all collectors"""
        logger.info("Initializing data collectors...")
        # Any initialization needed
    
    async def close(self):
        """Close all collectors"""
        logger.info("Closing data collectors...")
        # Any cleanup needed
    
    async def collect_data(self, topic: ContentTopic) -> List[Dict[str, Any]]:
        """Collect data from all collectors for a topic"""
        logger.info(f"Collecting data for topic: {topic}")
        
        # Run all collectors in parallel
        tasks = [collector.collect(topic) for collector in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all results
        all_data = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Collector error: {str(result)}")
            elif isinstance(result, list):
                all_data.extend(result)
        
        # Remove duplicates based on title similarity
        unique_data = self._deduplicate(all_data)
        
        logger.info(f"Collected {len(unique_data)} unique items for {topic}")
        return unique_data
    
    def _deduplicate(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items based on title similarity"""
        seen_titles = set()
        unique_data = []
        
        for item in data:
            title_key = item.get("title", "").lower().strip()
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_data.append(item)
        
        return unique_data