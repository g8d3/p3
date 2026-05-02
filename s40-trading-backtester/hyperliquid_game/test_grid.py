#!/usr/bin/env python3
"""
Quick test of grid trading backtest.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.model.data import BarType
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.currencies import BTC, USDT

from backtest.runner import generate_synthetic_bars, run_backtest
from strategies.grid_trading import GridTrading, GridTradingConfig


def main():
    instrument = TestInstrumentProvider.btcusdt_binance()
    instrument_id = instrument.id
    venue = instrument_id.venue
    
    bar_type = BarType.from_str(f"{instrument_id}-4-HOUR-LAST-EXTERNAL")
    
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=30000.0,
        num_bars=50,
        volatility=0.02,
    )
    
    grid_config = GridTradingConfig(
        instrument_id=instrument_id,
        grid_step=Price.from_str("100.0"),
        num_levels=5,
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
        bar_type=str(bar_type),
    )
    
    starting_balances = [Money(100000, USDT), Money(1, BTC)]
    
    results = run_backtest(
        strategy_class=GridTrading,
        strategy_config=grid_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    print("Grid trading backtest completed.")
    print("Results keys:", results.keys())
    # Print account report summary
    account_report = results['account_report']
    if isinstance(account_report, dict):
        print("Account report:", account_report)
    else:
        print("Account report (string):", account_report[:200])


if __name__ == "__main__":
    main()