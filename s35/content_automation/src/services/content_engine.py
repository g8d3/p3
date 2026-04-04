"""
Content Engine - Core service for gathering information and generating content
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from src.core.config import settings
from src.core.database import get_db
from src.models.content import Content, ContentTopic, ContentType, ContentStatus
from src.services.data_collectors import DataCollectorManager
from src.services.content_generator import ContentGenerator
from src.services.social_media_poster import SocialMediaPoster

logger = logging.getLogger(__name__)

class ContentEngine:
    def __init__(self):
        self.data_collector = DataCollectorManager()
        self.content_generator = ContentGenerator()
        self.social_poster = SocialMediaPoster()
        self.is_running = False
    
    async def start(self):
        """Start the content engine"""
        logger.info("Starting Content Engine...")
        self.is_running = True
        # Initialize data collectors
        await self.data_collector.initialize()
        logger.info("Content Engine started")
    
    async def stop(self):
        """Stop the content engine"""
        logger.info("Stopping Content Engine...")
        self.is_running = False
        await self.data_collector.close()
        logger.info("Content Engine stopped")
    
    async def gather_and_create_content(self, topic: ContentTopic) -> List[Content]:
        """
        Main workflow: gather data -> generate content -> save to database
        """
        logger.info(f"Gathering and creating content for topic: {topic}")
        
        try:
            # Step 1: Collect data from various sources
            raw_data = await self.data_collector.collect_data(topic)
            logger.info(f"Collected {len(raw_data)} raw data items for {topic}")
            
            # Step 2: Generate content from the collected data
            generated_content = await self.content_generator.generate_content(
                topic=topic,
                raw_data=raw_data
            )
            logger.info(f"Generated {len(generated_content)} content pieces for {topic}")
            
            # Step 3: Save content to database
            saved_content = []
            for content_data in generated_content:
                content = await self._save_content(content_data)
                if content:
                    saved_content.append(content)
            
            logger.info(f"Saved {len(saved_content)} content pieces to database")
            return saved_content
            
        except Exception as e:
            logger.error(f"Error in gather_and_create_content for {topic}: {str(e)}")
            return []
    
    async def _save_content(self, content_data: Dict[str, Any]) -> Optional[Content]:
        """Save generated content to database"""
        try:
            # Get database session
            db = next(get_db())
            
            # Check if similar content already exists (avoid duplicates)
            existing = db.query(Content).filter(
                Content.title == content_data['title'],
                Content.topic == content_data['topic']
            ).first()
            
            if existing:
                logger.info(f"Content already exists: {content_data['title']}")
                return existing
            
            # Create new content
            content = Content(
                title=content_data['title'],
                content_type=content_data['content_type'],
                topic=content_data['topic'],
                body=content_data['body'],
                summary=content_data.get('summary'),
                source_url=content_data.get('source_url'),
                source_name=content_data.get('source_name'),
                author=content_data.get('author'),
                tags=content_data.get('tags'),
                status=ContentStatus.DRAFT
            )
            
            db.add(content)
            db.commit()
            db.refresh(content)
            
            logger.info(f"Saved content: {content.title} (ID: {content.id})")
            return content
            
        except Exception as e:
            logger.error(f"Error saving content: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def get_pending_content(self, limit: int = 10) -> List[Content]:
        """Get content that is ready to be posted"""
        try:
            db = next(get_db())
            content_list = db.query(Content).filter(
                Content.status == ContentStatus.DRAFT
            ).order_by(Content.created_at.desc()).limit(limit).all()
            return content_list
        except Exception as e:
            logger.error(f"Error getting pending content: {str(e)}")
            return []
        finally:
            db.close()
    
    async def schedule_content_for_posting(self, content_id: int, 
                                         platforms: List[str],
                                         schedule_time: Optional[datetime] = None) -> bool:
        """Schedule content for posting on specified platforms"""
        try:
            db = next(get_db())
            content = db.query(Content).filter(Content.id == content_id).first()
            
            if not content:
                logger.error(f"Content not found: {content_id}")
                return False
            
            # Update content status
            content.status = ContentStatus.SCHEDULED
            if schedule_time:
                content.scheduled_at = schedule_time
            
            db.commit()
            
            # Create social post entries for each platform
            for platform in platforms:
                social_post = SocialPost(
                    content_id=content.id,
                    platform=platform,
                    status="pending"
                )
                db.add(social_post)
            
            db.commit()
            logger.info(f"Scheduled content {content_id} for posting on {platforms}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling content: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def post_scheduled_content(self) -> Dict[str, Any]:
        """Post content that is scheduled and ready"""
        try:
            db = next(get_db())
            
            # Get scheduled content that's ready to post
            now = datetime.utcnow()
            scheduled_posts = db.query(SocialPost).join(Content).filter(
                SocialPost.status == "pending",
                Content.status == ContentStatus.SCHEDULED,
                (Content.scheduled_at.is_(None)) | (Content.scheduled_at <= now)
            ).all()
            
            results = {
                "total": len(scheduled_posts),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            for social_post in scheduled_posts:
                try:
                    # Post to the specific platform
                    success = await self.social_poster.post_to_platform(
                        platform=social_post.platform,
                        content=social_post.content
                    )
                    
                    if success:
                        social_post.status = "posted"
                        social_post.posted_at = now
                        results["successful"] += 1
                    else:
                        social_post.status = "failed"
                        results["failed"] += 1
                    
                    db.commit()
                    
                except Exception as e:
                    error_msg = f"Failed to post {social_post.platform} for content {social_post.content_id}: {str(e)}"
                    logger.error(error_msg)
                    social_post.status = "failed"
                    social_post.error_message = str(e)
                    results["failed"] += 1
                    results["errors"].append(error_msg)
                    db.commit()
            
            # Update content status if all posts are done
            for social_post in scheduled_posts:
                content = social_post.content
                all_posts = db.query(SocialPost).filter(SocialPost.content_id == content.id).all()
                if all(post.status in ["posted", "failed"] for post in all_posts):
                    if all(post.status == "posted" for post in all_posts):
                        content.status = ContentStatus.POSTED
                        content.posted_at = now
                    else:
                        content.status = ContentStatus.FAILED
                    db.commit()
            
            logger.info(f"Posted scheduled content: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error posting scheduled content: {str(e)}")
            return {"error": str(e)}
        finally:
            db.close()