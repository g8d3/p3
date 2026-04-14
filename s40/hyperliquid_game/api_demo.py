#!/usr/bin/env python3
"""
API demo: Run backtest comparison via Python and print results.
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
from strategies.tpsl_trading import TPSLTrading, TPSLTradingConfig


def main():
    print("=== Hyperliquid Trading Game - API Demo ===\n")
    sys.stdout.flush()
    
    # Use BTCUSDT with 4-hour bars
    instrument = TestInstrumentProvider.btcusdt_binance()
    instrument_id = instrument.id
    venue = instrument_id.venue
    
    bar_type = BarType.from_str(f"{instrument_id}-4-HOUR-LAST-EXTERNAL")
    
    # Generate synthetic data (200 bars)
    print("Generating synthetic price data...")
    sys.stdout.flush()
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=30000.0,
        num_bars=200,
        volatility=0.02,
    )
    print(f"Generated {len(data)} bars of 4-hour data.\n")
    sys.stdout.flush()
    
    # Grid trading configuration
    grid_config = GridTradingConfig(
        instrument_id=instrument_id,
        grid_step=Price.from_str("100.0"),
        num_levels=3,
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
        bar_type=str(bar_type),
    )
    
    # TP/SL trading configuration
    start_price = 30000.0
    levels = [Price.from_str(str(start_price + i * 500)) for i in range(-3, 4)]
    tpsl_config = TPSLTradingConfig(
        instrument_id=instrument_id,
        bar_type=str(bar_type),
        horizontal_levels=levels,
        tp_pct=0.01,  # 1% take profit
        sl_pct=0.005,  # 0.5% stop loss
        trade_size=Quantity(0.01, precision=6),
        max_position=Quantity(0.1, precision=6),
    )
    
    starting_balances = [Money(100000, USDT), Money(1, BTC)]
    
    print("Running Grid Trading backtest...")
    grid_results = run_backtest(
        strategy_class=GridTrading,
        strategy_config=grid_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    print("Running TP/SL Trading backtest...")
    tpsl_results = run_backtest(
        strategy_class=TPSLTrading,
        strategy_config=tpsl_config,
        data=data,
        bar_type=bar_type,
        instrument=instrument,
        venue=venue,
        starting_balances=starting_balances,
    )
    
    # Extract metrics
    def extract_metrics(results, name):
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
                if b > peak:
                    peak = b
                dd = (peak - b) / peak
                if dd > max_dd:
                    max_dd = dd
            print(f"\n{name} Results:")
            print(f"  Initial balance: {initial:.4f} BTC")
            print(f"  Final balance:   {final:.4f} BTC")
            print(f"  Total return:    {returns:.2f}%")
            print(f"  Max drawdown:    {max_dd*100:.2f}%")
            return returns
        else:
            print(f"\n{name}: Could not extract metrics")
            return 0
    
    grid_return = extract_metrics(grid_results, "Grid Trading")
    tpsl_return = extract_metrics(tpsl_results, "TP/SL Trading")
    
    print("\n" + "="*50)
    if grid_return > tpsl_return:
        print("🏆 Grid Trading wins!")
    else:
        print("🏆 TP/SL Trading wins!")
    print("="*50)
    
    print("\nYou can also view interactive results in the web UI at:")
    print("  http://localhost:8501")
    print("\nTry adjusting parameters in the sidebar and running new backtests!")


if __name__ == "__main__":
    main()