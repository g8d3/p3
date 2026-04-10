"""Configuration management for the Mega Alpha trading system."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class HyperliquidConfig:
    api_url: str = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz")
    private_key: str = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")


@dataclass
class TradingConfig:
    coins: list[str] = field(
        default_factory=lambda: os.getenv("TRADING_COINS", "ETH,BTC,SOL").split(",")
    )
    max_position_size_usd: float = float(
        os.getenv("MAX_POSITION_SIZE_USD", "1000")
    )
    max_leverage: float = float(os.getenv("MAX_LEVERAGE", "3"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.02"))


@dataclass
class SignalConfig:
    lookback_days: int = int(os.getenv("SIGNAL_LOOKBACK_DAYS", "30"))
    combination_window_days: int = int(os.getenv("COMBINATION_WINDOW_DAYS", "60"))
    min_signal_history: int = int(os.getenv("MIN_SIGNAL_HISTORY", "20"))


@dataclass
class Settings:
    hyperliquid: HyperliquidConfig = field(default_factory=HyperliquidConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
