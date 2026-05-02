#!/usr/bin/env python3
"""
Fetch and cache volume data for all Hyperliquid assets in the past hour.
Optimized version with parallel processing for faster execution.
Outputs CSV with volume in USD, and if available, buyer/seller volume.

Rate Limiting:
- The Hyperliquid API has rate limits (429 errors)
- Script includes automatic retry with exponential backoff
- MAX_WORKERS is set to 5 to avoid hitting rate limits
- If you get rate limited, reduce MAX_WORKERS or increase RETRY_DELAY_BASE
"""

import os
import time
import csv
import random
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from joblib import Memory
from hyperliquid.utils import constants
from hyperliquid.info import Info
from hyperliquid.utils.error import ClientError

# Setup disk caching in the current directory
memory = Memory("./cachedir", verbose=0)

# Environment variables
HL_API_ADDRESS = os.getenv("HL_API_ADDRESS")
HL_API_KEY = os.getenv("HL_API_KEY")
HL_API_URL = os.getenv("HL_API_URL", constants.MAINNET_API_URL)

# Use default API URL for reliability
API_URL = constants.MAINNET_API_URL

# Rate limiting configuration
MAX_WORKERS = 5  # Reduced to avoid rate limits
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds
RATE_LIMIT_BACKOFF = 2.0  # Exponential backoff multiplier


@memory.cache
def fetch_all_assets_meta():
    """Fetch metadata for all perpetual and spot assets."""
    info = Info(API_URL, skip_ws=True)
    
    # Get perpetual assets
    perp_meta = info.meta()
    perp_assets = [asset["name"] for asset in perp_meta.get("universe", [])]
    
    # Get spot assets
    spot_meta = info.spot_meta()
    spot_assets = [asset["name"] for asset in spot_meta.get("universe", [])]
    
    return {
        "perp": perp_assets,
        "spot": spot_assets,
        "all": perp_assets + spot_assets
    }


@memory.cache
def fetch_asset_contexts():
    """Fetch current asset contexts including daily volume and prices."""
    info = Info(API_URL, skip_ws=True)
    
    # Get perpetual asset contexts
    _, perp_ctx = info.meta_and_asset_ctxs()
    
    # Get spot asset contexts
    _, spot_ctx = info.spot_meta_and_asset_ctxs()
    
    return {
        "perp": perp_ctx,
        "spot": spot_ctx
    }


@memory.cache
def fetch_candle_volume(asset_name: str, interval: str = "1h") -> Optional[dict]:
    """
    Fetch candle data for an asset to get volume with rate limit handling.
    
    Returns dict with:
    - volume: base volume
    - notional_volume: volume in USD (if price available)
    - start_time: candle start timestamp
    - end_time: candle end timestamp
    """
    # Calculate time range for past hour
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - 60 * 60 * 1000  # 1 hour ago
    
    for attempt in range(MAX_RETRIES):
        try:
            info = Info(API_URL, skip_ws=True)
            candles = info.candles_snapshot(asset_name, interval, start_ms, end_ms)
            
            if not candles:
                return None
            
            # Get the most recent complete candle
            candle = candles[-1]
            
            # Extract volume data
            volume = float(candle.get("v", 0))
            
            # Calculate notional volume using average price (typical approach)
            # Using (open + high + low + close) / 4 as average price
            o = float(candle.get("o", 0))
            h = float(candle.get("h", 0))
            l = float(candle.get("l", 0))
            c = float(candle.get("c", 0))
            
            avg_price = (o + h + l + c) / 4 if (o + h + l + c) > 0 else 0
            notional_volume = volume * avg_price
            
            return {
                "volume": volume,
                "notional_volume": notional_volume,
                "avg_price": avg_price,
                "start_time": candle.get("t"),
                "end_time": candle.get("T"),
                "num_trades": candle.get("n", 0)
            }
        except ClientError as e:
            # Check if it's a rate limit error (429)
            if e.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    delay = RETRY_DELAY_BASE * (RATE_LIMIT_BACKOFF ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited, retrying in {delay:.1f}s...", end=" ", flush=True)
                    time.sleep(delay)
                    continue
                else:
                    print(f"Rate limited after {MAX_RETRIES} attempts")
                    return None
            else:
                # Other client errors, return None
                return None
        except Exception as e:
            # Other exceptions, return None
            return None
    
    return None


def fetch_asset_volume(asset_name: str, asset_type: str, index: int, total: int) -> dict:
    """Fetch volume data for a single asset."""
    print(f"  [{index+1}/{total}] {asset_name}...", end=" ", flush=True)
    
    # Get hourly candle volume
    candle_data = fetch_candle_volume(asset_name, "1h")
    
    if candle_data:
        hourly_volume_usd = candle_data["notional_volume"]
        print(f"${hourly_volume_usd:,.2f}")
    else:
        hourly_volume_usd = 0
        print("no data")
    
    return {
        "asset": asset_name,
        "type": asset_type,
        "hourly_volume_usd": hourly_volume_usd,
        "hourly_base_volume": candle_data["volume"] if candle_data else 0,
        "avg_price": candle_data["avg_price"] if candle_data else 0,
        "num_trades": candle_data["num_trades"] if candle_data else 0
    }


def fetch_all_volumes_parallel() -> list[dict]:
    """
    Fetch volume data for all assets using parallel processing.
    
    Returns list of dicts with asset volume information.
    """
    print("Fetching asset metadata...")
    assets_meta = fetch_all_assets_meta()
    
    print("Fetching asset contexts...")
    contexts = fetch_asset_contexts()
    
    results = []
    
    # Prepare all assets for parallel processing
    all_assets = []
    
    # Add perpetual assets with context data
    for i, asset_name in enumerate(assets_meta["perp"]):
        daily_volume = 0
        mid_price = 0
        if i < len(contexts["perp"]):
            ctx = contexts["perp"][i]
            daily_volume = float(ctx.get("dayNtlVlm", 0) or 0)
            mid_price = float(ctx.get("midPx", 0) or 0)
        
        all_assets.append({
            "name": asset_name,
            "type": "perp",
            "daily_volume": daily_volume,
            "mid_price": mid_price,
            "index": i,
            "total": len(assets_meta["perp"])
        })
    
    # Add spot assets with context data
    for i, asset_name in enumerate(assets_meta["spot"]):
        daily_volume = 0
        mid_price = 0
        if i < len(contexts["spot"]):
            ctx = contexts["spot"][i]
            daily_volume = float(ctx.get("dayNtlVlm", 0) or 0)
            mid_price = float(ctx.get("midPx", 0) or 0)
        
        all_assets.append({
            "name": asset_name,
            "type": "spot",
            "daily_volume": daily_volume,
            "mid_price": mid_price,
            "index": i,
            "total": len(assets_meta["spot"])
        })
    
    total_assets = len(all_assets)
    print(f"\nProcessing {total_assets} assets with {MAX_WORKERS} parallel workers...")
    
    # Process assets in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_asset = {
            executor.submit(
                fetch_asset_volume, 
                asset["name"], 
                asset["type"], 
                asset["index"], 
                asset["total"]
            ): asset for asset in all_assets
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_asset):
            asset = future_to_asset[future]
            try:
                result = future.result()
                # Add daily volume and mid price from context
                result["daily_volume_usd"] = asset["daily_volume"]
                result["mid_price"] = asset["mid_price"]
                results.append(result)
            except Exception as e:
                print(f"Error processing {asset['name']}: {e}")
                # Add empty result for failed assets
                results.append({
                    "asset": asset["name"],
                    "type": asset["type"],
                    "hourly_volume_usd": 0,
                    "daily_volume_usd": asset["daily_volume"],
                    "mid_price": asset["mid_price"],
                    "hourly_base_volume": 0,
                    "avg_price": 0,
                    "num_trades": 0
                })
    
    # Sort results by asset name for consistent output
    results.sort(key=lambda x: (x["type"], x["asset"]))
    
    # Try to get buyer/seller volume if address is provided
    if HL_API_ADDRESS:
        print(f"\nFetching buyer/seller volume for address: {HL_API_ADDRESS[:8]}...")
        fills_data = fetch_buyer_seller_volume_from_fills(HL_API_ADDRESS, hours=1)
        
        # Add buyer/seller volume to all results (aggregate for the user)
        for result in results:
            result["user_buy_volume"] = fills_data["buy_volume"]
            result["user_sell_volume"] = fills_data["sell_volume"]
    
    return results


@memory.cache
def fetch_buyer_seller_volume_from_fills(address: str, hours: int = 1) -> dict:
    """
    Attempt to fetch buyer/seller volume from user fills with rate limit handling.
    Note: This only works for a specific user address, not aggregate market data.
    
    Returns dict with:
    - buy_volume: volume from buy orders
    - sell_volume: volume from sell orders
    """
    if not address:
        return {"buy_volume": 0, "sell_volume": 0}
    
    # Calculate time range
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (hours * 60 * 60 * 1000)
    
    for attempt in range(MAX_RETRIES):
        try:
            info = Info(API_URL, skip_ws=True)
            fills = info.user_fills_by_time(address, start_ms, end_ms)
            
            buy_volume = 0
            sell_volume = 0
            
            for fill in fills:
                side = fill.get("side", "")
                sz = float(fill.get("sz", 0))
                px = float(fill.get("px", 0))
                volume = sz * px
                
                if side == "B":  # Buy
                    buy_volume += volume
                elif side == "A":  # Sell/Ask
                    sell_volume += volume
            
            return {
                "buy_volume": buy_volume,
                "sell_volume": sell_volume
            }
        except ClientError as e:
            # Check if it's a rate limit error (429)
            if e.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    delay = RETRY_DELAY_BASE * (RATE_LIMIT_BACKOFF ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited, retrying in {delay:.1f}s...", end=" ", flush=True)
                    time.sleep(delay)
                    continue
                else:
                    print(f"Rate limited after {MAX_RETRIES} attempts")
                    return {"buy_volume": 0, "sell_volume": 0}
            else:
                print(f"Error fetching fills for {address}: {e}")
                return {"buy_volume": 0, "sell_volume": 0}
        except Exception as e:
            print(f"Error fetching fills for {address}: {e}")
            return {"buy_volume": 0, "sell_volume": 0}
    
    return {"buy_volume": 0, "sell_volume": 0}


def output_csv(results: list[dict], filename: str = "volume_data.csv"):
    """Output results to CSV file."""
    if not results:
        print("No data to output")
        return
    
    # Define CSV columns
    columns = [
        "asset",
        "type",
        "hourly_volume_usd",
        "daily_volume_usd",
        "mid_price",
        "hourly_base_volume",
        "avg_price",
        "num_trades"
    ]
    
    # Add buyer/seller columns if available
    if "user_buy_volume" in results[0]:
        columns.extend(["user_buy_volume", "user_sell_volume"])
    
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nOutput written to {filename}")
    print(f"Total assets: {len(results)}")
    
    # Summary statistics
    total_hourly_volume = sum(r["hourly_volume_usd"] for r in results)
    total_daily_volume = sum(r["daily_volume_usd"] for r in results)
    
    print(f"Total hourly volume: ${total_hourly_volume:,.2f}")
    print(f"Total daily volume: ${total_daily_volume:,.2f}")
    
    # Top 10 by hourly volume
    print("\nTop 10 assets by hourly volume:")
    sorted_results = sorted(results, key=lambda x: x["hourly_volume_usd"], reverse=True)
    for i, r in enumerate(sorted_results[:10]):
        print(f"  {i+1}. {r['asset']} ({r['type']}): ${r['hourly_volume_usd']:,.2f}")


if __name__ == "__main__":
    print("=" * 60)
    print("Hyperliquid Volume Fetcher (Parallel)")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    if HL_API_ADDRESS:
        print(f"Address: {HL_API_ADDRESS[:8]}...")
    print()
    
    start_time = time.time()
    
    # Fetch all volume data
    results = fetch_all_volumes_parallel()
    
    # Output to CSV
    output_csv(results)
    
    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.1f} seconds")
    print("Done!")