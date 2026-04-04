"""
Configuration management for the Content Automation System
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Content Automation System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./content_automation.db",
        env="DATABASE_URL"
    )
    
    # Redis settings (for caching and task queue)
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # API Keys for various services
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Social Media API Keys
    TWITTER_API_KEY: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    TWITTER_API_SECRET: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN_SECRET")
    
    FACEBOOK_ACCESS_TOKEN: Optional[str] = Field(default=None, env="FACEBOOK_ACCESS_TOKEN")
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = Field(default=None, env="INSTAGRAM_ACCESS_TOKEN")
    LINKEDIN_ACCESS_TOKEN: Optional[str] = Field(default=None, env="LINKEDIN_ACCESS_TOKEN")
    
    # GitHub settings
    GITHUB_TOKEN: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    
    # Reddit settings
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, env="REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = Field(default="ContentAutomationBot/1.0", env="REDDIT_USER_AGENT")
    
    # Content generation settings
    MAX_CONTENT_LENGTH: int = Field(default=2000, env="MAX_CONTENT_LENGTH")
    CONTENT_TEMPERATURE: float = Field(default=0.7, env="CONTENT_TEMPERATURE")
    
    # Scheduling settings
    DEFAULT_POST_INTERVAL_HOURS: int = Field(default=6, env="DEFAULT_POST_INTERVAL_HOURS")
    MAX_POSTS_PER_DAY: int = Field(default=4, env="MAX_POSTS_PER_DAY")
    
    # Supported content topics
    SUPPORTED_TOPICS: List[str] = [
        "ai news",
        "github news", 
        "tech tutorials",
        "ai applied to politics",
        "ai applied to business",
        "real value ai"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()