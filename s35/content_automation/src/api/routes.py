"""
API Routes for the Content Automation System
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.core.database import get_db
from src.models.content import Content, ContentTopic, ContentType, ContentStatus, SocialPost
from src.services.content_engine import ContentEngine

api_router = APIRouter()

# Dependency to get content engine from app state
def get_content_engine():
    # This will be set in main.py lifespan
    from src.main import app
    return app.state.content_engine

@api_router.get("/content", response_model=List[dict])
async def list_content(
    topic: Optional[ContentTopic] = None,
    status: Optional[ContentStatus] = None,
    content_type: Optional[ContentType] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """List all content with optional filtering"""
    query = db.query(Content)
    
    if topic:
        query = query.filter(Content.topic == topic)
    if status:
        query = query.filter(Content.status == status)
    if content_type:
        query = query.filter(Content.content_type == content_type)
    
    content_list = query.order_by(Content.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": c.id,
            "title": c.title,
            "content_type": c.content_type.value,
            "topic": c.topic.value,
            "summary": c.summary,
            "status": c.status.value,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "posted_at": c.posted_at.isoformat() if c.posted_at else None,
        }
        for c in content_list
    ]

@api_router.get("/content/{content_id}", response_model=dict)
async def get_content(content_id: int, db: Session = Depends(get_db)):
    """Get a specific content item"""
    content = db.query(Content).filter(Content.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {
        "id": content.id,
        "title": content.title,
        "content_type": content.content_type.value,
        "topic": content.topic.value,
        "body": content.body,
        "summary": content.summary,
        "status": content.status.value,
        "source_url": content.source_url,
        "source_name": content.source_name,
        "author": content.author,
        "tags": content.tags,
        "created_at": content.created_at.isoformat() if content.created_at else None,
        "updated_at": content.updated_at.isoformat() if content.updated_at else None,
        "scheduled_at": content.scheduled_at.isoformat() if content.scheduled_at else None,
        "posted_at": content.posted_at.isoformat() if content.posted_at else None,
    }

@api_router.post("/content/generate", response_model=dict)
async def generate_content(
    topic: ContentTopic,
    engine: ContentEngine = Depends(get_content_engine)
):
    """Manually trigger content generation for a topic"""
    content_items = await engine.gather_and_create_content(topic)
    
    return {
        "message": f"Generated {len(content_items)} content items for {topic.value}",
        "content_ids": [c.id for c in content_items]
    }

@api_router.post("/content/{content_id}/schedule", response_model=dict)
async def schedule_content(
    content_id: int,
    platforms: List[str],
    schedule_time: Optional[datetime] = None,
    engine: ContentEngine = Depends(get_content_engine)
):
    """Schedule content for posting"""
    success = await engine.schedule_content_for_posting(
        content_id=content_id,
        platforms=platforms,
        schedule_time=schedule_time
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to schedule content")
    
    return {"message": "Content scheduled successfully"}

@api_router.post("/content/post-now", response_model=dict)
async def post_now(engine: ContentEngine = Depends(get_content_engine)):
    """Immediately post all scheduled content that's ready"""
    results = await engine.post_scheduled_content()
    return results

@api_router.get("/posts", response_model=List[dict])
async def list_posts(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """List all social media posts"""
    query = db.query(SocialPost)
    
    if platform:
        query = query.filter(SocialPost.platform == platform)
    if status:
        query = query.filter(SocialPost.status == status)
    
    posts = query.order_by(SocialPost.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "content_id": p.content_id,
            "platform": p.platform,
            "platform_post_id": p.platform_post_id,
            "status": p.status,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            "error_message": p.error_message,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in posts
    ]

@api_router.get("/stats", response_model=dict)
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_content = db.query(Content).count()
    draft_content = db.query(Content).filter(Content.status == ContentStatus.DRAFT).count()
    scheduled_content = db.query(Content).filter(Content.status == ContentStatus.SCHEDULED).count()
    posted_content = db.query(Content).filter(Content.status == ContentStatus.POSTED).count()
    
    total_posts = db.query(SocialPost).count()
    posted_posts = db.query(SocialPost).filter(SocialPost.status == "posted").count()
    failed_posts = db.query(SocialPost).filter(SocialPost.status == "failed").count()
    
    return {
        "content": {
            "total": total_content,
            "draft": draft_content,
            "scheduled": scheduled_content,
            "posted": posted_content,
        },
        "posts": {
            "total": total_posts,
            "posted": posted_posts,
            "failed": failed_posts,
        }
    }

@api_router.get("/topics", response_model=List[str])
async def list_topics():
    """List all supported content topics"""
    return [topic.value for topic in ContentTopic]