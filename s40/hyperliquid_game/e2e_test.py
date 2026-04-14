#!/usr/bin/env python3
"""
End-to-end test: runs backtests and stores results for different "users".
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
from strategies.tpsl_trading import TPSLTrading, TPSLTradingConfig


def run_backtest_for_user(user_id: str, strategy_type: str, params: dict):
    """Run a backtest for a specific user and strategy."""
    instrument = TestInstrumentProvider.btcusdt_binance()
    instrument_id = instrument.id
    venue = instrument_id.venue
    
    bar_type = BarType.from_str(f"{instrument_id}-4-HOUR-LAST-EXTERNAL")
    
    # Generate synthetic data
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=params.get('start_price', 30000.0),
        num_bars=params.get('num_bars', 200),
        volatility=params.get('volatility', 0.02),
    )
    
    starting_balances = [
        Money(params.get('starting_usdt', 100000), USDT),
        Money(params.get('starting_btc', 1.0), BTC),
    ]
    
    if strategy_type == 'grid':
        config = GridTradingConfig(
            instrument_id=instrument_id,
            grid_step=Price.from_str(str(params.get('grid_step', 100.0))),
            num_levels=params.get('num_levels', 3),
            trade_size=Quantity(params.get('trade_size', 0.01), precision=6),
            max_position=Quantity(params.get('max_position', 0.1), precision=6),
            bar_type=str(bar_type),
        )
        strategy_class = GridTrading
    else:  # tpsl
        start_price = params.get('start_price', 30000.0)
        levels = [Price.from_str(str(start_price + i * params.get('level_spacing', 500))) 
                  for i in range(-params.get('num_levels', 3), params.get('num_levels', 3) + 1)]
        config = TPSLTradingConfig(
            instrument_id=instrument_id,
            bar_type=str(bar_type),
            horizontal_levels=levels,
            tp_pct=params.get('tp_pct', 0.01),
            sl_pct=params.get('sl_pct', 0.005),
            trade_size=Quantity(params.get('trade_size', 0.01), precision=6),
            max_position=Quantity(params.get('max_position', 0.1), precision=6),
        )
        strategy_class = TPSLTrading
    
    results = run_backtest(
        strategy_class=strategy_class,
        strategy_config=config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    # Extract summary metrics
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
        
        return {
            'user_id': user_id,
            'strategy': strategy_type,
            'timestamp': datetime.now().isoformat(),
            'initial_balance': initial,
            'final_balance': final,
            'total_return_pct': returns,
            'max_drawdown_pct': max_dd * 100,
            'params': params,
        }
    else:
        return {
            'user_id': user_id,
            'strategy': strategy_type,
            'timestamp': datetime.now().isoformat(),
            'error': 'Could not extract metrics',
        }


def main():
    """Run tests for multiple users and strategies."""
    results = []
    
    # Test 1: AI user with grid trading
    print("Running grid trading for AI user...")
    grid_params = {
        'start_price': 30000.0,
        'num_bars': 200,
        'volatility': 0.02,
        'grid_step': 100.0,
        'num_levels': 3,
        'trade_size': 0.01,
        'max_position': 0.1,
    }
    result = run_backtest_for_user('ai_user', 'grid', grid_params)
    results.append(result)
    print(f"  Grid result: {result.get('total_return_pct', 'error')}% return")
    
    # Test 2: AI user with TP/SL trading
    print("Running TP/SL trading for AI user...")
    tpsl_params = {
        'start_price': 30000.0,
        'num_bars': 200,
        'volatility': 0.02,
        'level_spacing': 500.0,
        'num_levels': 3,
        'tp_pct': 0.01,
        'sl_pct': 0.005,
        'trade_size': 0.01,
        'max_position': 0.1,
    }
    result = run_backtest_for_user('ai_user', 'tpsl', tpsl_params)
    results.append(result)
    print(f"  TP/SL result: {result.get('total_return_pct', 'error')}% return")
    
    # Save results to file
    output_file = Path('backtest_results.json')
    if output_file.exists():
        with open(output_file, 'r') as f:
            existing = json.load(f)
    else:
        existing = []
    
    existing.extend(results)
    
    with open(output_file, 'w') as f:
        json.dump(existing, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    print(f"Total results: {len(existing)}")
    
    # Print summary
    for r in results:
        if 'total_return_pct' in r:
            print(f"  {r['user_id']} - {r['strategy']}: {r['total_return_pct']:.2f}% return, {r['max_drawdown_pct']:.2f}% max DD")


if __name__ == "__main__":
    main()