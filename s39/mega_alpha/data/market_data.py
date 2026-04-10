"""Market data fetching and caching for Hyperliquid."""

import time
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants as hl_constants
except ImportError:
    logger.warning("hyperliquid-python-sdk not installed. Install with: pip install hyperliquid-python-sdk")
    Info = None
    hl_constants = None


class MarketDataFetcher:
    """Fetches and caches market data from Hyperliquid."""

    def __init__(self, api_url: str = "https://api.hyperliquid.xyz"):
        if Info is None:
            raise ImportError("hyperliquid-python-sdk is required")

        self.info = Info(api_url, skip_ws=True)
        self._cache: dict[str, pd.DataFrame] = {}
        self._cache_ttl = 60  # seconds
        self._last_fetch: dict[str, float] = {}

    def get_ohlcv(
        self,
        coin: str,
        interval: str = "1h",
        lookback_hours: int = 720,  # 30 days
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a coin.

        Args:
            coin: Trading pair (e.g., "ETH", "BTC").
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d).
            lookback_hours: How far back to fetch.

        Returns:
            DataFrame with columns: open, high, low, close, volume.
        """
        cache_key = f"{coin}_{interval}_{lookback_hours}"
        now = time.time()

        if cache_key in self._cache and now - self._last_fetch.get(cache_key, 0) < self._cache_ttl:
            return self._cache[cache_key]

        end = int(time.time() * 1000)
        start = end - lookback_hours * 60 * 60 * 1000

        try:
            candles = self.info.candles_snapshot(coin, interval, start, end)
        except Exception as e:
            logger.error(f"Failed to fetch candles for {coin}: {e}")
            if cache_key in self._cache:
                return self._cache[cache_key]
            return pd.DataFrame()

        if not candles:
            logger.warning(f"No candle data returned for {coin}")
            return pd.DataFrame()

        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["t"].astype(float), unit="ms")
        df = df.rename(columns={
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        })
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df.set_index("timestamp").sort_index()

        self._cache[cache_key] = df
        self._last_fetch[cache_key] = now
        return df

    def get_funding_rate(
        self,
        coin: str,
        lookback_hours: int = 720,
    ) -> pd.Series:
        """Fetch funding rate history for a coin."""
        end = int(time.time() * 1000)
        start = end - lookback_hours * 60 * 60 * 1000

        try:
            funding = self.info.funding_history(coin, start, end)
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {coin}: {e}")
            return pd.Series(dtype=float)

        if not funding:
            return pd.Series(dtype=float)

        df = pd.DataFrame(funding)
        if "fundingRate" in df.columns:
            time_col = "time" if "time" in df.columns else "t"
            df["timestamp"] = pd.to_datetime(df[time_col].astype(float), unit="ms")
            series = df.set_index("timestamp")["fundingRate"].astype(float)
            return series.sort_index()

        return pd.Series(dtype=float)

    def get_orderbook(self, coin: str) -> dict:
        """Fetch L2 order book snapshot."""
        try:
            book = self.info.l2_snapshot(coin)
            return book
        except Exception as e:
            logger.error(f"Failed to fetch orderbook for {coin}: {e}")
            return {"levels": [[], []]}

    def get_mid_price(self, coin: str) -> Optional[float]:
        """Get current mid price for a coin."""
        try:
            mids = self.info.all_mids()
            if coin in mids:
                return float(mids[coin])
        except Exception as e:
            logger.error(f"Failed to fetch mid price for {coin}: {e}")
        return None

    def get_all_mid_prices(self) -> dict[str, float]:
        """Get all mid prices."""
        try:
            mids = self.info.all_mids()
            return {k: float(v) for k, v in mids.items()}
        except Exception as e:
            logger.error(f"Failed to fetch mid prices: {e}")
            return {}

    def get_open_interest(self, coin: str) -> Optional[float]:
        """Get current open interest for a coin."""
        try:
            import requests
            data = requests.post(
                self.info.base_url + "/info",
                json={"type": "metaAndAssetCtxs"},
            ).json()
            meta, ctxs = data
            for i, asset in enumerate(meta["universe"]):
                if asset["name"] == coin:
                    return float(ctxs[i]["openInterest"])
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {coin}: {e}")
        return None

    def get_asset_context(self, coin: str) -> Optional[dict]:
        """Get full asset context (mark price, funding, OI, etc.)."""
        try:
            import requests
            data = requests.post(
                self.info.base_url + "/info",
                json={"type": "metaAndAssetCtxs"},
            ).json()
            meta, ctxs = data
            for i, asset in enumerate(meta["universe"]):
                if asset["name"] == coin:
                    return ctxs[i]
        except Exception as e:
            logger.error(f"Failed to fetch asset context for {coin}: {e}")
        return None

    def build_signal_data(
        self,
        coins: list[str],
        interval: str = "1h",
        lookback_hours: int = 720,
    ) -> dict[str, pd.DataFrame]:
        """Build complete data dict for signal computation.

        Returns dict mapping coin -> DataFrame with OHLCV + funding_rate + open_interest.
        """
        result = {}

        for coin in coins:
            df = self.get_ohlcv(coin, interval, lookback_hours)
            if df.empty:
                logger.warning(f"No OHLCV data for {coin}, skipping")
                continue

            # Add funding rate
            funding = self.get_funding_rate(coin, lookback_hours)
            if not funding.empty:
                df["funding_rate"] = funding.reindex(df.index, method="ffill").fillna(0)

            # Add open interest (current value, forward-filled)
            oi = self.get_open_interest(coin)
            if oi is not None:
                df["open_interest"] = oi

            # Add orderbook imbalance data
            book = self.get_orderbook(coin)
            if book and "levels" in book:
                bids, asks = book["levels"]
                if bids and asks:
                    bid_vol = sum(float(b.get("sz", 0)) for b in bids[:5])
                    ask_vol = sum(float(a.get("sz", 0)) for a in asks[:5])
                    df["bid_volume"] = bid_vol
                    df["ask_volume"] = ask_vol

            result[coin] = df

        return result
