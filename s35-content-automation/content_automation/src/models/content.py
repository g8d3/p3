"""
Content data models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.core.database import Base
import enum

class ContentType(str, enum.Enum):
    ARTICLE = "article"
    SOCIAL_POST = "social_post"
    THREAD = "thread"
    VIDEO_SCRIPT = "video_script"
    NEWSLETTER = "newsletter"

class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    ARCHIVED = "archived"

class ContentTopic(str, enum.Enum):
    AI_NEWS = "ai news"
    GITHUB_NEWS = "github news"
    TECH_TUTORIALS = "tech tutorials"
    AI_POLITICS = "ai applied to politics"
    AI_BUSINESS = "ai applied to business"
    REAL_VALUE_AI = "real value ai"

class Content(Base):
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content_type = Column(Enum(ContentType), nullable=False)
    topic = Column(Enum(ContentTopic), nullable=False)
    body = Column(Text, nullable=False)
    summary = Column(Text)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    
    # Metadata
    source_url = Column(String(500))
    source_name = Column(String(100))
    author = Column(String(100))
    tags = Column(String(500))  # Comma-separated tags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    scheduled_at = Column(DateTime(timezone=True))
    posted_at = Column(DateTime(timezone=True))
    
    # Relationships
    posts = relationship("SocialPost", back_populates="content")
    
    def __repr__(self):
        return f"<Content(id={self.id}, title='{self.title}', topic='{self.topic}')>"

class SocialPost(Base):
    __tablename__ = "social_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    platform = Column(String(50), nullable=False)  # twitter, facebook, linkedin, etc.
    platform_post_id = Column(String(100))  # ID from the platform
    status = Column(String(20), default="pending")  # pending, posted, failed
    posted_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    content = relationship("Content", back_populates="posts")
    
    def __repr__(self):
        return f"<SocialPost(id={self.id}, platform='{self.platform}', status='{self.status}')>"

class ContentSource(Base):
    __tablename__ = "content_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)  # rss, github, reddit, news_api, etc.
    is_active = Column(Boolean, default=True)
    last_fetched = Column(DateTime(timezone=True))
    fetch_interval_minutes = Column(Integer, default=60)
    
    # Configuration (JSON stored as text)
    config = Column(Text)  # JSON configuration for the source
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ContentSource(id={self.id}, name='{self.name}', type='{self.source_type}')>"