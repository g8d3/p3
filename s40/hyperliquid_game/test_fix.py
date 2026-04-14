#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from nautilus_trader.model.data import BarType
from nautilus_trader.test_kit.providers import TestInstrumentProvider

instrument = TestInstrumentProvider.btcusdt_binance()
instrument_id = instrument.id

timeframe_map = {
    "4h": "4-HOUR",
    "8h": "8-HOUR",
    "12h": "12-HOUR",
    "1d": "1-DAY",
}
for tf, spec in timeframe_map.items():
    bar_type_str = f"{instrument_id}-{spec}-LAST-EXTERNAL"
    print(f"Testing {tf} -> {spec}: {bar_type_str}")
    try:
        bar_type = BarType.from_str(bar_type_str)
        print(f"  Success: {bar_type}")
    except Exception as e:
        print(f"  Error: {e}")

# Test generate_synthetic_bars parsing
from backtest.runner import generate_synthetic_bars
print("\nTesting generate_synthetic_bars with bar_spec='4-HOUR'")
try:
    data = generate_synthetic_bars(
        instrument_id=instrument_id,
        bar_spec="4-HOUR",
        start_price=30000.0,
        num_bars=5,
        volatility=0.02,
    )
    print(f"Generated {len(data)} rows")
    print(data.head())
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()