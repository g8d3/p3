"""
AutoContent - Automated Content Creation System
Configuration Module
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """LLM Configuration"""
    provider: str = "openai"  # openai, anthropic, ollama
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    base_url: Optional[str] = None  # For Ollama or custom endpoints
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4000


@dataclass
class CDPConfig:
    """Chrome DevTools Protocol Browser Configuration"""
    browser_type: str = "chrome"  # chrome, firefox, edge
    headless: bool = True
    user_data_dir: Optional[str] = None  # For persistent sessions
    proxy: Optional[str] = None
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 720})


@dataclass
class WalletConfig:
    """Wallet/Payment Configuration"""
    provider: str = "stripe"  # stripe, paypal, crypto
    api_key: str = os.getenv("WALLET_API_KEY", "")
    card_token: str = os.getenv("CARD_TOKEN", "")  # Tokenized card


@dataclass
class GitHubConfig:
    """GitHub Configuration"""
    token: str = os.getenv("GITHUB_TOKEN", "")
    default_repo: str = ""


@dataclass
class XConfig:
    """X.com Configuration"""
    username: str = os.getenv("X_USERNAME", "")
    password: str = os.getenv("X_PASSWORD", "")
    session_file: str = "x_session.json"


@dataclass
class SchedulerConfig:
    """Scheduler Configuration"""
    check_interval_minutes: int = 30
    content_generation_interval_hours: int = 4
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class Config:
    """Main Configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    cdp: CDPConfig = field(default_factory=CDPConfig)
    wallet: WalletConfig = field(default_factory=WalletConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    x: XConfig = field(default_factory=XConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    
    # Paths
    data_dir: str = "data"
    logs_dir: str = "logs"
    output_dir: str = "output"
    videos_dir: str = "output/videos"
    code_dir: str = "output/code"
    
    # Verification
    verify_inputs: bool = True
    verify_outputs: bool = True
    
    # Self-healing
    auto_retry: bool = True
    max_self_heal_attempts: int = 5


# Global config instance
config = Config()
