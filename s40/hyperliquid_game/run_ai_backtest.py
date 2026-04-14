#!/usr/bin/env python3
"""
Run a single backtest for AI user and save results.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from nautilus_trader.model.identifiers import InstrumentId
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
    
    # Generate synthetic data
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=30000.0,
        num_bars=200,
        volatility=0.02,
    )
    
    config = GridTradingConfig(
        instrument_id=instrument_id,
        grid_step=Price.from_str("100.0"),
        num_levels=3,
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
        bar_type=str(bar_type),
    )
    
    starting_balances = [Money(100000, USDT), Money(1, BTC)]
    
    results = run_backtest(
        strategy_class=GridTrading,
        strategy_config=config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    # Extract metrics
    account_report = results['account_report']
    if isinstance(account_report, dict) and 'total' in account_report:
        total_series = account_report['total']
        balances = list(total_series.values())
        initial = float(balances[0])
        final = float(balances[-1])
        returns = (final - initial) / initial * 100
        
        # Compute max drawdown
        peak = initial
        max_dd = 0
        for b in balances:
            b_float = float(b)
            if b_float > peak:
                peak = b_float
            dd = (peak - b_float) / peak
            if dd > max_dd:
                max_dd = dd
        
        result = {
            'user_id': 'ai_user',
            'strategy': 'grid',
            'timestamp': datetime.now().isoformat(),
            'initial_balance': initial,
            'final_balance': final,
            'total_return_pct': returns,
            'max_drawdown_pct': max_dd * 100,
        }
        
        # Save to file
        results_file = Path('backtest_results.json')
        existing = []
        if results_file.exists():
            with open(results_file, 'r') as f:
                existing = json.load(f)
        existing.append(result)
        with open(results_file, 'w') as f:
            json.dump(existing, f, indent=2)
        
        print(f"Result saved: {result}")
    else:
        print("Could not extract metrics")


if __name__ == "__main__":
    main()