# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Backtest runner for grid trading vs TP/SL trading strategies.
"""

import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import BTC, USDT
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider
from nautilus_trader.test_kit.providers import TestInstrumentProvider

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from strategies.grid_trading import GridTrading, GridTradingConfig
from strategies.tpsl_trading import TPSLTrading, TPSLTradingConfig


def generate_synthetic_bars(
    instrument_id,
    bar_spec,
    start_price: float = 10000.0,
    num_bars: int = 1000,
    volatility: float = 0.02,
    seed: int = 42,
    bates_params: dict = None,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV bar data using Bates stochastic volatility jump model.
    """
    np.random.seed(seed)
    
    # Bates model parameters (defaults derived from volatility)
    v0 = volatility ** 2  # initial variance
    r = 0.0  # risk-free rate (drift)
    if bates_params is None:
        bates_params = {}
    kappa = bates_params.get('kappa', 5.0)
    theta = bates_params.get('theta', v0)
    sigma = bates_params.get('sigma', 0.1)
    rho = bates_params.get('rho', -0.7)
    lambda_ = bates_params.get('lambda_', 0.05)
    mu_j = bates_params.get('mu_j', 0.0)
    sigma_j = bates_params.get('sigma_j', 0.05)
    
    # Convert bar_spec to bars per year
    parts = bar_spec.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid bar_spec: {bar_spec}")
    step = int(parts[0])
    agg = parts[1].upper()
    if agg == "MINUTE":
        bars_per_year = (24 * 60 * 252) / step
    elif agg == "HOUR":
        bars_per_year = (24 * 252) / step
    elif agg == "DAY":
        bars_per_year = 252 / step
    elif agg == "WEEK":
        bars_per_year = 52 / step
    elif agg == "MONTH":
        bars_per_year = 12 / step
    else:
        raise ValueError(f"Unsupported aggregation: {agg}")
    T = num_bars / bars_per_year  # total time in years
    N = num_bars  # number of time steps
    M = 1  # single path
    
    # Bates model simulation (Euler discretization)
    dt = T / N
    S = np.zeros((M, N+1))
    v = np.zeros((M, N+1))
    S[:, 0] = start_price
    v[:, 0] = v0
    
    for i in range(1, N+1):
        dW1 = np.random.normal(0, np.sqrt(dt), M)
        dW2 = rho * dW1 + np.sqrt(1 - rho**2) * np.random.normal(0, np.sqrt(dt), M)
        
        # Jump process
        dN = np.random.poisson(lambda_ * dt, M)
        J = np.random.normal(mu_j, sigma_j, M) * dN
        
        v[:, i] = v[:, i-1] + kappa * (theta - v[:, i-1]) * dt + sigma * np.sqrt(v[:, i-1]) * dW2
        v[:, i] = np.maximum(v[:, i], 0)  # Ensure non-negative volatility
        
        # Expected jump compensation
        k = np.exp(mu_j + 0.5 * sigma_j**2) - 1
        S[:, i] = S[:, i-1] * np.exp((r - lambda_ * k - 0.5 * v[:, i-1]) * dt + 
                                     np.sqrt(v[:, i-1]) * dW1 + J)
    
    price_path = S[0, 1:]  # exclude initial price, shape (num_bars,)
    
    # Create timestamps (starting from now, going backwards)
    end_time = pd.Timestamp.now(tz='UTC')
    # Parse bar_spec (e.g., "4-HOUR", "1-DAY")
    agg_map_pandas = {
        "MINUTE": "min",
        "HOUR": "h",
        "DAY": "D",
        "WEEK": "W",
        "MONTH": "M",
    }
    pandas_agg = agg_map_pandas.get(agg)
    if pandas_agg is None:
        raise ValueError(f"Unsupported aggregation: {agg}")
    freq = f"{step}{pandas_agg}"
    timestamps = pd.date_range(end=end_time, periods=num_bars, freq=freq, tz='UTC')
    # Generate OHLCV
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': price_path * (1 + np.random.uniform(-0.005, 0.005, num_bars)),
        'high': price_path * (1 + np.random.uniform(0, 0.01, num_bars)),
        'low': price_path * (1 + np.random.uniform(-0.01, 0, num_bars)),
        'close': price_path,
        'volume': np.random.uniform(100, 1000, num_bars),
    })
    # Ensure high >= max(open, close) and low <= min(open, close)
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    df = df.set_index('timestamp')
    return df


def run_backtest(
    strategy_class,
    strategy_config,
    data: pd.DataFrame,
    bar_type: BarType,
    instrument,
    venue,
    starting_balances,
    account_type=AccountType.CASH,
    oms_type=OmsType.NETTING,
):
    """
    Run a backtest with the given strategy and data.
    Returns a dict of performance metrics.
    """
    config = BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        logging=LoggingConfig(log_level="ERROR", bypass_logging=True),  # Reduce noise and prevent Rust logging initialization panic
    )
    engine = BacktestEngine(config=config)
    
    # Add venue
    engine.add_venue(
        venue=venue,
        oms_type=oms_type,
        account_type=account_type,
        base_currency=None,  # Multi-currency account
        starting_balances=starting_balances,
    )
    
    # Add instrument
    engine.add_instrument(instrument)
    
    # Process data with BarDataWrangler
    wrangler = BarDataWrangler(bar_type, instrument)
    bars = wrangler.process(data)
    engine.add_data(bars)
    
    # Instantiate and add strategy
    strategy = strategy_class(config=strategy_config)
    engine.add_strategy(strategy)
    
    # Run engine
    engine.run()
    
    # Collect results
    account_report = engine.trader.generate_account_report(venue)
    fills_report = engine.trader.generate_order_fills_report()
    positions_report = engine.trader.generate_positions_report()
    
    # Compute summary metrics
    # For simplicity, we'll just return the account report as a dict
    # In a real implementation, we'd compute Sharpe, drawdown, etc.
    results = {
        'account_report': account_report.to_dict() if hasattr(account_report, 'to_dict') else str(account_report),
        'fills_report': fills_report.to_dict() if hasattr(fills_report, 'to_dict') else str(fills_report),
        'positions_report': positions_report.to_dict() if hasattr(positions_report, 'to_dict') else str(positions_report),
    }
    
    # Clean up
    engine.reset()
    engine.dispose()
    
    return results


def compare_strategies(
    grid_config: GridTradingConfig,
    tpsl_config: TPSLTradingConfig,
    data: pd.DataFrame,
    bar_type: BarType,
    instrument,
    venue,
    starting_balances,
):
    """
    Run backtests for both strategies and return comparison.
    """
    grid_results = run_backtest(
        strategy_class=GridTrading,
        strategy_config=grid_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    tpsl_results = run_backtest(
        strategy_class=TPSLTrading,
        strategy_config=tpsl_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    return {
        'grid_trading': grid_results,
        'tpsl_trading': tpsl_results,
    }


def generate_multiple_synthetic_bars(
    instrument_id,
    bar_spec,
    start_price: float = 10000.0,
    num_bars: int = 1000,
    volatility: float = 0.02,
    seed: int = 42,
    bates_params: dict = None,
    num_datasets: int = 5,
    variation: float = 0.2,
) -> list[pd.DataFrame]:
    """
    Generate multiple synthetic OHLCV bar datasets with varied Bates parameters.
    Returns list of DataFrames.
    """
    np.random.seed(seed)
    datasets = []
    for i in range(num_datasets):
        # Sample parameters with uniform variation
        if bates_params is None:
            bates_params = {}
        sampled_params = {}
        for key, value in bates_params.items():
            if value is None:
                sampled_params[key] = None
            else:
                # Apply variation within +/- variation fraction
                delta = np.random.uniform(-variation, variation)
                sampled_params[key] = value * (1 + delta)
        # Ensure bounds
        sampled_params['kappa'] = max(0.1, sampled_params.get('kappa', 5.0))
        sampled_params['theta'] = max(0.0001, sampled_params.get('theta', volatility**2))
        sampled_params['sigma'] = max(0.01, sampled_params.get('sigma', 0.1))
        sampled_params['rho'] = min(0.0, max(-1.0, sampled_params.get('rho', -0.7)))
        sampled_params['lambda_'] = max(0.0, sampled_params.get('lambda_', 0.05))
        sampled_params['mu_j'] = sampled_params.get('mu_j', 0.0)
        sampled_params['sigma_j'] = max(0.01, sampled_params.get('sigma_j', 0.05))
        
        # Generate dataset with sampled parameters
        df = generate_synthetic_bars(
            instrument_id=instrument_id,
            bar_spec=bar_spec,
            start_price=start_price,
            num_bars=num_bars,
            volatility=volatility,
            seed=seed + i,  # different seed each dataset
            bates_params=sampled_params,
        )
        datasets.append(df)
    return datasets


if __name__ == "__main__":
    # Example usage
    from nautilus_trader.model.identifiers import InstrumentId, Venue
    
    # Define instrument
    instrument = TestInstrumentProvider.btcusdt_binance()
    instrument_id = instrument.id
    venue = instrument_id.venue
    
    # Define bar type (4-hour bars)
    bar_type = BarType.from_str(f"{instrument_id}-4-HOUR-LAST-EXTERNAL")
    
    # Generate synthetic data
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=30000.0,
        num_bars=50,
        volatility=0.02,
    )
    
    # Define grid trading config
    grid_config = GridTradingConfig(
        instrument_id=instrument_id,
        grid_step=Price.from_str("100.0"),
        num_levels=5,
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
        bar_type=str(bar_type),
    )
    
    # Define TP/SL trading config
    # Horizontal levels every 500 USDT around starting price
    start_price = 30000.0
    levels = [Price.from_str(str(start_price + i*500)) for i in range(-5, 6)]
    tpsl_config = TPSLTradingConfig(
        instrument_id=instrument_id,
        bar_type=str(bar_type),
        horizontal_levels=levels,
        tp_pct=0.01,  # 1% take profit
        sl_pct=0.005,  # 0.5% stop loss
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
    )
    
    # Starting balances
    starting_balances = [Money(100000, USDT), Money(1, BTC)]
    
    # Run comparison
    results = compare_strategies(
        grid_config=grid_config,
        tpsl_config=tpsl_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    print("Backtest comparison completed.")
    print("Grid trading results keys:", results['grid_trading'].keys())
    print("TP/SL trading results keys:", results['tpsl_trading'].keys())
