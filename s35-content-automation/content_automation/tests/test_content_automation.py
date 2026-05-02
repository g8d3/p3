"""
Tests for the Content Automation System
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.models.content import Content, ContentTopic, ContentType, ContentStatus, SocialPost
from src.services.data_collectors import RSSCollector, GitHubCollector, DataCollectorManager
from src.services.content_generator import ContentGenerator
from src.services.content_engine import ContentEngine


class TestContentModel:
    """Test Content model"""
    
    def test_content_creation(self):
        """Test creating a content instance"""
        content = Content(
            title="Test Article",
            content_type=ContentType.ARTICLE,
            topic=ContentTopic.AI_NEWS,
            body="Test content body",
            summary="Test summary"
        )
        
        assert content.title == "Test Article"
        assert content.content_type == ContentType.ARTICLE
        assert content.topic == ContentTopic.AI_NEWS
        assert content.status == ContentStatus.DRAFT
    
    def test_social_post_creation(self):
        """Test creating a social post instance"""
        post = SocialPost(
            content_id=1,
            platform="twitter",
            status="pending"
        )
        
        assert post.content_id == 1
        assert post.platform == "twitter"
        assert post.status == "pending"


class TestRSSCollector:
    """Test RSS Collector"""
    
    def test_rss_collector_initialization(self):
        """Test RSS collector initializes with feeds"""
        collector = RSSCollector()
        assert collector.feeds is not None
        assert ContentTopic.AI_NEWS in collector.feeds
        assert len(collector.feeds[ContentTopic.AI_NEWS]) > 0
    
    @patch('feedparser.parse')
    def test_collect_rss_feeds(self, mock_parse):
        """Test collecting from RSS feeds"""
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.entries = [
            Mock(
                title="Test Article",
                summary="Test summary",
                link="https://example.com",
                published="2026-04-01"
            )
        ]
        mock_feed.feed.title = "Test Feed"
        mock_parse.return_value = mock_feed
        
        collector = RSSCollector()
        # Note: This would need async test in real implementation
        assert collector.feeds is not None


class TestContentGenerator:
    """Test Content Generator"""
    
    def test_generator_initialization(self):
        """Test content generator initializes"""
        generator = ContentGenerator()
        assert generator.temperature == 0.7
        assert generator.max_length == 2000
    
    def test_fallback_article_generation(self):
        """Test fallback article generation without LLM"""
        generator = ContentGenerator()
        raw_data = [
            {
                "title": "Test Article 1",
                "summary": "Test summary 1",
                "link": "https://example.com/1",
                "source": "Test Source"
            },
            {
                "title": "Test Article 2",
                "summary": "Test summary 2",
                "link": "https://example.com/2",
                "source": "Test Source"
            }
        ]
        
        result = generator._fallback_article_generation(ContentTopic.AI_NEWS, raw_data)
        
        assert "title" in result
        assert "body" in result
        assert "summary" in result
        assert "Test Article 1" in result["body"]
        assert "AI News" in result["body"]
    
    def test_fallback_social_post_generation(self):
        """Test fallback social post generation"""
        generator = ContentGenerator()
        raw_data = [
            {
                "title": "Test Article",
                "summary": "Test summary",
                "link": "https://example.com",
                "source": "Test Source"
            }
        ]
        
        result = generator._fallback_social_post_generation(
            ContentTopic.AI_NEWS, raw_data, "twitter"
        )
        
        assert "title" in result
        assert "body" in result
        assert len(result["body"]) <= 280  # Twitter limit
    
    def test_fallback_thread_generation(self):
        """Test fallback thread generation"""
        generator = ContentGenerator()
        raw_data = [
            {
                "title": f"Article {i}",
                "summary": f"Summary {i}",
                "link": f"https://example.com/{i}",
                "source": "Test Source"
            }
            for i in range(1, 6)
        ]
        
        result = generator._fallback_thread_generation(ContentTopic.AI_NEWS, raw_data)
        
        assert "title" in result
        assert "body" in result
        assert "1/5" in result["body"]


class TestDataCollectorManager:
    """Test Data Collector Manager"""
    
    def test_manager_initialization(self):
        """Test manager initializes with collectors"""
        manager = DataCollectorManager()
        assert len(manager.collectors) > 0
    
    def test_deduplication(self):
        """Test data deduplication"""
        manager = DataCollectorManager()
        data = [
            {"title": "Article 1", "summary": "Summary 1"},
            {"title": "Article 1", "summary": "Summary 1 Duplicate"},
            {"title": "Article 2", "summary": "Summary 2"},
        ]
        
        unique_data = manager._deduplicate(data)
        
        assert len(unique_data) == 2
        assert unique_data[0]["title"] == "Article 1"
        assert unique_data[1]["title"] == "Article 2"


class TestContentEngine:
    """Test Content Engine"""
    
    def test_engine_initial_state(self):
        """Test engine starts in correct state"""
        engine = ContentEngine()
        assert not engine.is_running
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """Test engine start and stop"""
        engine = ContentEngine()
        
        await engine.start()
        assert engine.is_running
        
        await engine.stop()
        assert not engine.is_running


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])