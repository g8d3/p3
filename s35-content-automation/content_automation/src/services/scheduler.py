"""
Content Scheduler - Manages scheduling of content creation and posting
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.core.config import settings
from src.services.content_engine import ContentEngine
from src.models.content import ContentTopic

logger = logging.getLogger(__name__)

class ContentScheduler:
    def __init__(self, content_engine: ContentEngine):
        self.content_engine = content_engine
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def start(self):
        """Start the scheduler"""
        logger.info("Starting Content Scheduler...")
        
        # Schedule content creation for each topic
        for topic in ContentTopic:
            # Create content every 6 hours (configurable)
            self.scheduler.add_job(
                self._create_content_for_topic,
                IntervalTrigger(hours=settings.DEFAULT_POST_INTERVAL_HOURS),
                args=[topic],
                id=f"create_content_{topic.value.replace(' ', '_')}",
                name=f"Create content for {topic.value}",
                replace_existing=True,
                max_instances=1
            )
        
        # Schedule posting of ready content every hour
        self.scheduler.add_job(
            self.content_engine.post_scheduled_content,
            IntervalTrigger(hours=1),
            id="post_scheduled_content",
            name="Post scheduled content",
            replace_existing=True,
            max_instances=1
        )
        
        # Start the scheduler
        self.scheduler.start()
        self.is_running = True
        
        logger.info("Content Scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping Content Scheduler...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Content Scheduler stopped")
    
    async def _create_content_for_topic(self, topic: ContentTopic):
        """Create content for a specific topic"""
        logger.info(f"Scheduled content creation for: {topic}")
        
        try:
            # Check if we've reached max posts per day
            # This would require checking the database for today's posts
            # For now, we'll just create the content
            
            content_items = await self.content_engine.gather_and_create_content(topic)
            
            if content_items:
                logger.info(f"Created {len(content_items)} content items for {topic}")
                
                # Auto-schedule the content for posting
                for content in content_items:
                    # Schedule for next available slot
                    schedule_time = datetime.utcnow() + timedelta(hours=1)
                    await self.content_engine.schedule_content_for_posting(
                        content_id=content.id,
                        platforms=["twitter", "linkedin", "facebook"],
                        schedule_time=schedule_time
                    )
            else:
                logger.info(f"No content created for {topic}")
                
        except Exception as e:
            logger.error(f"Error creating content for {topic}: {str(e)}")
    
    def add_custom_job(self, func, trigger, **kwargs):
        """Add a custom scheduled job"""
        self.scheduler.add_job(func, trigger, **kwargs)
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        self.scheduler.remove_job(job_id)
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()