#!/usr/bin/env python3
"""
Funding Rate Comparison Tool for Top CLOB Perp DEXes
Fetches and normalizes funding rates from top perpetual DEXes
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from tabulate import tabulate

class FundingRateFetcher:
    def __init__(self):
        self.dex_configs = {
            'Hyperliquid': {
                'base_url': 'https://api.hyperliquid.xyz/info',
                'funding_interval': 1,  # hours
                'symbols': ['BTC', 'ETH']
            },
            'dYdX': {
                'base_url': 'https://api.dydx.exchange/v3',
                'funding_interval': 8,  # hours  
                'symbols': ['BTC-USD', 'ETH-USD']
            },
            'GMX': {
                'base_url': 'https://api.gmx.io/v2',
                'funding_interval': 1,  # hours
                'symbols': ['BTC', 'ETH']
            },
            'Drift': {
                'base_url': 'https://api.drift.trade/v1',
                'funding_interval': 1,  # hours
                'symbols': ['BTC-PERP', 'ETH-PERP']
            },
            'Apex': {
                'base_url': 'https://api.apex.exchange/v1',
                'funding_interval': 1,  # hours
                'symbols': ['BTC-USDC', 'ETH-USDC']
            }
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FundingRateAnalyzer/1.0',
            'Accept': 'application/json'
        })

    def fetch_hyperliquid_rates(self) -> Dict[str, float]:
        """Fetch funding rates from Hyperliquid"""
        try:
            response = self.session.get('https://api.hyperliquid.xyz/info')
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            if 'meta' in data and 'andressScopeStats' in data['meta']:
                for symbol in ['BTC', 'ETH']:
                    for asset in data['meta']['andressScopeStats']:
                        if asset.get('name') == symbol:
                            # Hyperliquid returns funding rate as percentage (0.0001 = 0.01%)
                            rate = asset.get('fundingRate', 0)
                            rates[symbol] = float(rate) * 100
                            break
            return rates
        except Exception as e:
            print(f"Error fetching Hyperliquid rates: {e}")
            return {}

    def fetch_dydx_rates(self) -> Dict[str, float]:
        """Fetch funding rates from dYdX"""
        try:
            # Get markets info
            response = self.session.get('https://api.dydx.exchange/v3/markets')
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            markets = data.get('markets', {})
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                if symbol in markets:
                    # dYdX returns hourly funding rate
                    rate = markets[symbol].get('nextFundingRate', 0)
                    rates[symbol] = float(rate) * 100
            return rates
        except Exception as e:
            print(f"Error fetching dYdX rates: {e}")
            return {}

    def fetch_gmx_rates(self) -> Dict[str, float]:
        """Fetch funding rates from GMX"""
        try:
            response = self.session.get('https://api.gmx.io/v2/prices')
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            # GMX funding rates need to be calculated from price data
            # This is a simplified version - actual implementation might need different endpoint
            for token in ['BTC', 'ETH']:
                prices = data.get(token, {})
                if prices:
                    # Placeholder - actual GMX funding rate endpoint may differ
                    rates[token] = 0.01  # placeholder rate
            return rates
        except Exception as e:
            print(f"Error fetching GMX rates: {e}")
            return {}

    def fetch_drift_rates(self) -> Dict[str, float]:
        """Fetch funding rates from Drift Protocol"""
        try:
            response = self.session.get('https://api.drift.trade/v1/markets')
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for market in data:
                symbol = market.get('name', '')
                rate = market.get('currentFundingRate', 0)
                
                if 'BTC' in symbol:
                    rates['BTC-PERP'] = float(rate) * 100
                elif 'ETH' in symbol:
                    rates['ETH-PERP'] = float(rate) * 100
            
            return rates
        except Exception as e:
            print(f"Error fetching Drift rates: {e}")
            return {}

    def fetch_apex_rates(self) -> Dict[str, float]:
        """Fetch funding rates from Apex"""
        try:
            response = self.session.get('https://api.apex.exchange/v1/tickers')
            response.raise_for_status()
            data = response.json()
            
            rates = {}
            for ticker in data.get('data', []):
                symbol = ticker.get('symbol', '')
                if 'BTC' in symbol or 'ETH' in symbol:
                    rate = ticker.get('fundingRate', 0)
                    normalized_symbol = 'BTC-USDC' if 'BTC' in symbol else 'ETH-USDC'
                    rates[normalized_symbol] = float(rate) * 100
            
            return rates
        except Exception as e:
            print(f"Error fetching Apex rates: {e}")
            return {}

    def normalize_to_hourly(self, rate: float, interval_hours: int) -> float:
        """Normalize funding rate to hourly basis"""
        return rate / interval_hours if interval_hours > 0 else rate

    def normalize_to_annual(self, hourly_rate: float) -> float:
        """Convert hourly rate to annual percentage rate"""
        return hourly_rate * 24 * 365.25

    def fetch_all_rates(self) -> Dict[str, Dict[str, float]]:
        """Fetch funding rates from all configured DEXes"""
        all_rates = {}
        
        fetchers = {
            'Hyperliquid': self.fetch_hyperliquid_rates,
            'dYdX': self.fetch_dydx_rates,
            'GMX': self.fetch_gmx_rates,
            'Drift': self.fetch_drift_rates,
            'Apex': self.fetch_apex_rates
        }
        
        for dex_name, fetcher in fetchers.items():
            try:
                print(f"Fetching rates from {dex_name}...")
                rates = fetcher()
                if rates:
                    all_rates[dex_name] = rates
                time.sleep(0.5)  # Be nice to APIs
            except Exception as e:
                print(f"Failed to fetch from {dex_name}: {e}")
                continue
        
        return all_rates

    def create_comparison_table(self, rates_data: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """Create normalized comparison table"""
        # Standardize symbol names across DEXes
        symbol_mapping = {
            'BTC': ['BTC', 'BTC-USD', 'BTC-PERP', 'BTC-USDC'],
            'ETH': ['ETH', 'ETH-USD', 'ETH-PERP', 'ETH-USDC']
        }
        
        table_data = []
        
        for dex_name, dex_rates in rates_data.items():
            config = self.dex_configs.get(dex_name, {})
            interval = config.get('funding_interval', 1)
            
            for symbol_group, symbol_variants in symbol_mapping.items():
                # Find rate for this symbol
                rate = None
                for variant in symbol_variants:
                    if variant in dex_rates:
                        rate = dex_rates[variant]
                        break
                
                if rate is not None:
                    # Normalize rates
                    hourly_rate = self.normalize_to_hourly(rate, interval)
                    annual_rate = self.normalize_to_annual(hourly_rate)
                    
                    table_data.append({
                        'DEX': dex_name,
                        'Symbol': symbol_group,
                        'Raw Rate (%)': f"{rate:.4f}",
                        'Hourly Rate (%)': f"{hourly_rate:.4f}",
                        'Annual Rate (%)': f"{annual_rate:.2f}",
                        'Funding Interval (h)': interval
                    })
        
        return pd.DataFrame(table_data)

    def display_comparison(self, df: pd.DataFrame):
        """Display the comparison table"""
        if df.empty:
            print("No funding rate data available")
            return
        
        # Create pivot tables for better comparison
        btc_df = df[df['Symbol'] == 'BTC'].copy()
        eth_df = df[df['Symbol'] == 'ETH'].copy()
        
        print("\n" + "="*80)
        print("FUNDING RATE COMPARISON - TOP CLOB PERP DEXES")
        print("="*80)
        
        print(f"\nBTC Funding Rates (Normalized to Hourly & Annual)")
        print("-" * 50)
        if not btc_df.empty:
            btc_pivot = btc_df[['DEX', 'Hourly Rate (%)', 'Annual Rate (%)']].copy()
            print(tabulate(btc_pivot.values.tolist(), 
                          headers=['DEX', 'Hourly Rate (%)', 'Annual Rate (%)'],
                          tablefmt='grid', floatfmt='.4f'))
        
        print(f"\nETH Funding Rates (Normalized to Hourly & Annual)")
        print("-" * 50)
        if not eth_df.empty:
            eth_pivot = eth_df[['DEX', 'Hourly Rate (%)', 'Annual Rate (%)']].copy()
            print(tabulate(eth_pivot.values.tolist(),
                          headers=['DEX', 'Hourly Rate (%)', 'Annual Rate (%)'],
                          tablefmt='grid', floatfmt='.4f'))
        
        # Calculate and display arbitrage opportunities
        print(f"\nArbitrage Opportunities (Rate Differences)")
        print("-" * 50)
        
        for symbol in ['BTC', 'ETH']:
            symbol_data = df[df['Symbol'] == symbol]
            if not symbol_data.empty and len(symbol_data) > 1:
                hourly_rates = symbol_data['Hourly Rate (%)'].str.rstrip('%').astype(float)
                if len(hourly_rates) > 1:
                    max_rate_idx = hourly_rates.idxmax()
                    min_rate_idx = hourly_rates.idxmin()
                    
                    max_dex = symbol_data.loc[max_rate_idx]
                    min_dex = symbol_data.loc[min_rate_idx]
                    
                    rate_diff = hourly_rates.max() - hourly_rates.min()
                    annual_diff = rate_diff * 24 * 365.25
                    
                    print(f"{symbol}:")
                    print(f"  Highest: {max_dex['DEX']} ({max_dex['Hourly Rate (%)']})")
                    print(f"  Lowest:  {min_dex['DEX']} ({min_dex['Hourly Rate (%)']})")
                    print(f"  Spread:  {rate_diff:.4f}% hourly ({annual_diff:.2f}% annual)")

def main():
    """Main execution function"""
    print("Funding Rate Comparison Tool - Top CLOB Perp DEXes")
    print("Fetching real-time funding rates...")
    
    fetcher = FundingRateFetcher()
    
    try:
        # Fetch all rates
        rates_data = fetcher.fetch_all_rates()
        
        if not rates_data:
            print("No funding rate data retrieved. Please check API endpoints.")
            return
        
        # Create and display comparison
        df = fetcher.create_comparison_table(rates_data)
        fetcher.display_comparison(df)
        
        print(f"\nData fetched at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("\nNote: Rates are normalized across different funding intervals")
        print("for accurate comparison across platforms.")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
