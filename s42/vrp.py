import requests
import pandas as pd
import numpy as np
import time
import sys

# Config
ASSETS = ['BTC', 'ETH', 'SOL']
TIMEFRAME = '1h'
WINDOW_DAYS = 7
ANNUAL_FACTOR = np.sqrt(8760)

def get_iv(asset):
    """Updated for Deribit v2 API changes."""
    # Deribit DVOL index names are usually 'BTC-DVOL', 'ETH-DVOL'
    url = f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={asset}&resolution=1h"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'result' in data and 'data' in data['result']:
            # The last element in the data list is [timestamp, value]
            return float(data['result']['data'][-1][1])
        else:
            print(f"[Debug] {asset} IV Field Missing: {data.get('error', 'Unknown Error')}")
            return None
    except Exception as e:
        print(f"[Debug] {asset} IV Request Failed: {e}")
        return None

def get_rv(asset):
    """Updated for Hyperliquid info endpoint."""
    url = "https://api.hyperliquid.xyz/info"
    start_time = int((time.time() - (WINDOW_DAYS * 24 * 3600)) * 1000)
    # Hyperliquid requires "coin" and "startTime"
    payload = {
        "type": "candleSnapshot", 
        "req": {
            "coin": asset, 
            "interval": TIMEFRAME, 
            "startTime": start_time
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            # Hyperliquid candles return 'c' for close price as string
            prices = [float(candle['c']) for candle in data]
            returns = np.log(pd.Series(prices) / pd.Series(prices).shift(1)).dropna()
            return returns.std() * ANNUAL_FACTOR * 100
        else:
            print(f"[Debug] {asset} RV Data Empty or Malformed")
            return None
    except Exception as e:
        print(f"[Debug] {asset} RV Request Failed: {e}")
        return None

def monitor():
    while True:
        results = []
        for asset in ASSETS:
            iv = get_iv(asset)
            rv = get_rv(asset)
            
            if iv is not None and rv is not None:
                vrp = iv - rv
                status = "🔥 SELL" if vrp > 5 else "❄️ WAIT"
                results.append(f"{asset:<6} | {iv:>6.1f}% | {rv:>6.1f}% | {vrp:>6.1f}% | {status}")
            else:
                results.append(f"{asset:<6} | {'N/A':>6} | {'N/A':>6} | {'N/A':>6} | ⚠️ ERROR")
        
        # ANSI Clear Screen
        sys.stdout.write("\033[H\033[J")
        print(f"** VRP Multi-Monitor | Window: {WINDOW_DAYS}d | {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 65)
        print(f"{'Asset':<6} | {'IV':<8} | {'RV (7d)':<8} | {'VRP':<8} | {'Status'}")
        print("-" * 65)
        for r in results:
            print(r)
        
        time.sleep(60)

if __name__ == "__main__":
    monitor()
