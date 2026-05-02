"""Continuous backtest runner: fetches data, runs optimizer, reports results.

This is the main entry point for the backtesting system. It:
1. Fetches historical data from Hyperliquid (or loads from cache)
2. Runs the continuous parameter optimizer
3. Reports the best configuration found
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from data.market_data import MarketDataFetcher
from backtest.engine import BacktestEngine
from backtest.optimizer import ParameterOptimizer


def generate_synthetic_data(
    coins: list[str] = None,
    n_bars: int = 2160,  # 90 days of hourly data
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Generate synthetic market data for backtesting when real data is unavailable.

    Creates realistic-looking OHLCV data with:
    - Geometric Brownian motion for prices
    - Mean-reverting funding rates
    - Trending open interest
    - Volume patterns
    """
    if coins is None:
        coins = ["ETH", "BTC", "SOL"]

    rng = np.random.RandomState(seed)
    data = {}

    base_prices = {"ETH": 3000, "BTC": 60000, "SOL": 150, "ARB": 1.5, "DOGE": 0.15}
    base_vols = {"ETH": 0.6, "BTC": 0.4, "SOL": 1.0, "ARB": 1.2, "DOGE": 1.5}

    for coin in coins:
        price = base_prices.get(coin, 100)
        annual_vol = base_vols.get(coin, 0.8)
        hourly_vol = annual_vol / np.sqrt(24 * 365)
        hourly_drift = 0.0  # Zero drift for testing

        # Generate returns with occasional regime changes
        returns = np.zeros(n_bars)
        regime = 0  # 0 = normal, 1 = trending up, -1 = trending down
        regime_length = 0

        for i in range(n_bars):
            # Regime switching
            if regime_length <= 0:
                regime = rng.choice([-1, 0, 0, 0, 1], p=[0.1, 0.25, 0.25, 0.25, 0.15])
                regime_length = rng.randint(20, 100)

            drift = regime * hourly_vol * 0.5
            returns[i] = drift + hourly_vol * rng.randn()
            regime_length -= 1

        # Build price series
        prices = price * np.exp(np.cumsum(returns))

        # OHLCV
        dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
        df = pd.DataFrame(index=dates)

        df["close"] = prices
        df["open"] = prices * (1 + rng.uniform(-0.002, 0.002, n_bars))
        df["high"] = np.maximum(df["open"], df["close"]) * (1 + rng.uniform(0, 0.005, n_bars))
        df["low"] = np.minimum(df["open"], df["close"]) * (1 - rng.uniform(0, 0.005, n_bars))
        df["volume"] = np.abs(rng.exponential(1000, n_bars)) * (1 + 0.5 * np.abs(returns))

        # Funding rate: mean-reverting around 0.01%
        funding = np.zeros(n_bars)
        funding[0] = 0.0001
        for i in range(1, n_bars):
            funding[i] = funding[i-1] * 0.95 + 0.0001 * 0.05 + rng.randn() * 0.00005
        df["funding_rate"] = funding

        # Open interest: trending with noise
        oi_base = rng.uniform(1e6, 1e8)
        oi_trend = rng.uniform(-0.001, 0.001)
        oi_noise = rng.randn(n_bars) * oi_base * 0.01
        df["open_interest"] = oi_base * np.exp(np.cumsum(np.full(n_bars, oi_trend))) + oi_noise
        df["open_interest"] = df["open_interest"].clip(lower=oi_base * 0.1)

        data[coin] = df

    return data


def fetch_real_data(coins: list[str], lookback_hours: int = 2160) -> dict[str, pd.DataFrame]:
    """Fetch real historical data from Hyperliquid."""
    settings = get_settings()
    fetcher = MarketDataFetcher(api_url=settings.hyperliquid.api_url)

    data = {}
    for coin in coins:
        try:
            df = fetcher.get_ohlcv(coin, interval="1h", lookback_hours=lookback_hours)
            if not df.empty:
                # Add funding rate
                funding = fetcher.get_funding_rate(coin, lookback_hours)
                if not funding.empty:
                    df["funding_rate"] = funding.reindex(df.index, method="ffill").fillna(0)

                # Add open interest
                oi = fetcher.get_open_interest(coin)
                if oi is not None:
                    df["open_interest"] = oi

                data[coin] = df
                logger.info(f"Fetched {len(df)} bars for {coin}")
        except Exception as e:
            logger.error(f"Failed to fetch data for {coin}: {e}")

    return data


def run_continuous_backtest(
    use_real_data: bool = False,
    coins: list[str] = None,
    initial_capital: float = 10000.0,
    max_iterations: int = 500,
    target_sharpe: float = 0.5,
    target_max_dd: float = 0.30,
    train_end_pct: float = 0.70,
) -> None:
    """Run the continuous backtest search.

    Args:
        use_real_data: If True, fetch from Hyperliquid. If False, use synthetic.
        coins: List of coins to trade.
        initial_capital: Starting capital.
        max_iterations: Max search iterations.
        target_sharpe: Target Sharpe ratio for "promising" configs.
        target_max_dd: Target max drawdown for "promising" configs.
        train_end_pct: Train/test split ratio for OOS validation.
    """
    if coins is None:
        coins = ["ETH", "BTC", "SOL"]

    # ─── Get data ───
    if use_real_data:
        logger.info("Fetching real market data from Hyperliquid...")
        data = fetch_real_data(coins)
        if not data:
            logger.warning("Failed to fetch real data. Falling back to synthetic.")
            data = generate_synthetic_data(coins)
    else:
        logger.info("Using synthetic market data for backtesting...")
        data = generate_synthetic_data(coins)

    logger.info(f"Data ready: {list(data.keys())} coins, {len(next(iter(data.values())))} bars each")

    # ─── Create backtest engine ───
    engine = BacktestEngine(
        data=data,
        initial_capital=initial_capital,
        commission_bps=5.0,
        slippage_bps=3.0,
    )

    # ─── Create optimizer ───
    optimizer = ParameterOptimizer(
        engine=engine,
        target_sharpe=target_sharpe,
        target_max_dd=target_max_dd,
        max_iterations=max_iterations,
        train_end_pct=train_end_pct,
    )

    # ─── Run search ───
    best = optimizer.search()

    # ─── Final report ───
    if best:
        logger.info("\n" + "=" * 60)
        logger.info("FINAL BEST CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Sharpe Ratio: {best.sharpe:.3f}")
        logger.info(f"Max Drawdown: {best.max_drawdown:.1%}")
        logger.info(f"Total Return: {best.total_return:.1%}")
        logger.info(f"Win Rate: {best.win_rate:.1%}")
        logger.info(f"Profit Factor: {best.profit_factor:.2f}")
        logger.info(f"Total Trades: {best.total_trades}")
        logger.info(f"Per-Signal IC: {best.per_signal_ic}")
        logger.info(f"Promising: {best.is_promising}")
        logger.info(f"\nBest Parameters:")
        for k, v in best.params.items():
            logger.info(f"  {k}: {v}")
        logger.info("=" * 60)
    else:
        logger.warning("No valid results found in the search.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mega Alpha Continuous Backtester")
    parser.add_argument("--real-data", action="store_true", help="Use real Hyperliquid data")
    parser.add_argument("--coins", nargs="+", default=["ETH", "BTC", "SOL"], help="Coins to trade")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--iterations", type=int, default=500, help="Max search iterations")
    parser.add_argument("--target-sharpe", type=float, default=0.5, help="Target Sharpe ratio")
    parser.add_argument("--target-dd", type=float, default=0.30, help="Target max drawdown")
    parser.add_argument("--train-pct", type=float, default=0.70, help="Train/test split ratio")
    args = parser.parse_args()

    run_continuous_backtest(
        use_real_data=args.real_data,
        coins=args.coins,
        initial_capital=args.capital,
        max_iterations=args.iterations,
        target_sharpe=args.target_sharpe,
        target_max_dd=args.target_dd,
        train_end_pct=args.train_pct,
    )
