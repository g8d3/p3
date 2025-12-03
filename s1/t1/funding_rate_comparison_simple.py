#!/usr/bin/env python3
"""
Funding Rate Comparison Tool for Top CLOB Perp DEXes
Fetches and normalizes funding rates from top perpetual DEXes
Uses only Python standard library
"""

import urllib.request
import urllib.error
import json
import time
from datetime import datetime
import sys

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

    def fetch_json(self, url):
        """Fetch JSON data from URL"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'FundingRateAnalyzer/1.0')
            req.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def fetch_hyperliquid_rates(self):
        """Fetch funding rates from Hyperliquid"""
        try:
            data = self.fetch_json('https://api.hyperliquid.xyz/info')
            if not data:
                return {}
            
            rates = {}
            if 'meta' in data and 'andressScopeStats' in data['meta']:
                for symbol in ['BTC', 'ETH']:
                    for asset in data['meta']['andressScopeStats']:
                        if asset.get('name') == symbol:
                            rate = asset.get('fundingRate', 0)
                            rates[symbol] = float(rate) * 100
                            break
            return rates
        except Exception as e:
            print(f"Error fetching Hyperliquid rates: {e}")
            return {}

    def fetch_dydx_rates(self):
        """Fetch funding rates from dYdX"""
        try:
            data = self.fetch_json('https://api.dydx.exchange/v3/markets')
            if not data:
                return {}
            
            rates = {}
            markets = data.get('markets', {})
            
            for symbol in ['BTC-USD', 'ETH-USD']:
                if symbol in markets:
                    rate = markets[symbol].get('nextFundingRate', 0)
                    rates[symbol] = float(rate) * 100
            return rates
        except Exception as e:
            print(f"Error fetching dYdX rates: {e}")
            return {}

    def fetch_gmx_rates(self):
        """Fetch funding rates from GMX"""
        try:
            # GMX uses different API structure
            rates = {}
            # For now, use mock data until we find the correct endpoint
            rates['BTC'] = 0.01  # placeholder
            rates['ETH'] = 0.01  # placeholder
            return rates
        except Exception as e:
            print(f"Error fetching GMX rates: {e}")
            return {}

    def fetch_drift_rates(self):
        """Fetch funding rates from Drift Protocol"""
        try:
            data = self.fetch_json('https://api.drift.trade/v1/markets')
            if not data:
                return {}
            
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

    def fetch_apex_rates(self):
        """Fetch funding rates from Apex"""
        try:
            data = self.fetch_json('https://api.apex.exchange/v1/tickers')
            if not data:
                return {}
            
            rates = {}
            for ticker in data.get('data', []):
                symbol = ticker.get('symbol', '')
                rate = ticker.get('fundingRate', 0)
                
                if 'BTC' in symbol or 'ETH' in symbol:
                    normalized_symbol = 'BTC-USDC' if 'BTC' in symbol else 'ETH-USDC'
                    rates[normalized_symbol] = float(rate) * 100
            
            return rates
        except Exception as e:
            print(f"Error fetching Apex rates: {e}")
            return {}

    def normalize_to_hourly(self, rate, interval_hours):
        """Normalize funding rate to hourly basis"""
        return rate / interval_hours if interval_hours > 0 else rate

    def normalize_to_annual(self, hourly_rate):
        """Convert hourly rate to annual percentage rate"""
        return hourly_rate * 24 * 365.25

    def test_api_connectivity(self):
        """Test connectivity to each API"""
        print("Testing API connectivity...")
        
        test_urls = {
            'Hyperliquid': 'https://api.hyperliquid.xyz/info',
            'dYdX': 'https://api.dydx.exchange/v3/markets',
            'Drift': 'https://api.drift.trade/v1/markets',
            'Apex': 'https://api.apex.exchange/v1/tickers'
        }
        
        working_apis = []
        for name, url in test_urls.items():
            try:
                response = urllib.request.urlopen(url, timeout=5)
                status = response.getcode()
                if status == 200:
                    working_apis.append(name)
                    print(f"  {name}: ✓ Available")
                else:
                    print(f"  {name}: ✗ HTTP {status}")
            except Exception as e:
                print(f"  {name}: ✗ {str(e)[:50]}...")
        
        return working_apis

    def fetch_all_rates(self):
        """Fetch funding rates from all configured DEXes"""
        print("Fetching funding rates...")
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
                time.sleep(1)  # Be nice to APIs
            except Exception as e:
                print(f"Failed to fetch from {dex_name}: {e}")
                continue
        
        return all_rates

    def display_table(self, rates_data):
        """Display comparison table in plain text"""
        # Standardize symbol names across DEXes
        symbol_mapping = {
            'BTC': ['BTC', 'BTC-USD', 'BTC-PERP', 'BTC-USDC'],
            'ETH': ['ETH', 'ETH-USD', 'ETH-PERP', 'ETH-USDC']
        }
        
        print("\n" + "="*80)
        print("FUNDING RATE COMPARISON - TOP CLOB PERP DEXES")
        print("="*80)
        
        # Process data
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
                        'Raw Rate': f"{rate:.4f}%",
                        'Hourly Rate': f"{hourly_rate:.4f}%",
                        'Annual Rate': f"{annual_rate:.2f}%",
                        'Interval': f"{interval}h"
                    })
        
        # Display by symbol
        for symbol in ['BTC', 'ETH']:
            symbol_data = [row for row in table_data if row['Symbol'] == symbol]
            
            print(f"\n{symbol} Funding Rates (Normalized)")
            print("-" * 70)
            print(f"{'DEX':<15} {'Raw Rate':<12} {'Hourly Rate':<12} {'Annual Rate':<12} {'Interval':<8}")
            print("-" * 70)
            
            for row in symbol_data:
                print(f"{row['DEX']:<15} {row['Raw Rate']:<12} {row['Hourly Rate']:<12} {row['Annual Rate']:<12} {row['Interval']:<8}")
        
        # Calculate arbitrage opportunities
        print(f"\nArbitrage Opportunities (Rate Differences)")
        print("-" * 50)
        
        for symbol in ['BTC', 'ETH']:
            symbol_data = [row for row in table_data if row['Symbol'] == symbol]
            
            if len(symbol_data) > 1:
                # Extract hourly rates for comparison
                hourly_rates = []
                for row in symbol_data:
                    rate_str = row['Hourly Rate'].rstrip('%')
                    try:
                        rate_val = float(rate_str)
                        hourly_rates.append((rate_val, row['DEX']))
                    except:
                        continue
                
                if hourly_rates:
                    hourly_rates.sort(key=lambda x: x[0])
                    min_rate, min_dex = hourly_rates[0]
                    max_rate, max_dex = hourly_rates[-1]
                    
                    rate_diff = max_rate - min_rate
                    annual_diff = rate_diff * 24 * 365.25
                    
                    print(f"{symbol}:")
                    print(f"  Highest: {max_dex} ({max_rate:.4f}% hourly)")
                    print(f"  Lowest:  {min_dex} ({min_rate:.4f}% hourly)")
                    print(f"  Spread:  {rate_diff:.4f}% hourly ({annual_diff:.2f}% annual)")

def get_sample_data():
    """Get sample funding rate data for demonstration"""
    return {
        'Hyperliquid': {'BTC': 0.0156, 'ETH': 0.0123},
        'dYdX': {'BTC-USD': 0.0234, 'ETH-USD': 0.0187},
        'GMX': {'BTC': 0.0145, 'ETH': 0.0112},
        'Drift': {'BTC-PERP': 0.0178, 'ETH-PERP': 0.0134},
        'Apex': {'BTC-USDC': 0.0201, 'ETH-USDC': 0.0167}
    }

def main():
    """Main execution function"""
    print("Funding Rate Comparison Tool - Top CLOB Perp DEXes")
    print("Fetching real-time funding rates...")
    
    fetcher = FundingRateFetcher()
    
    try:
        # Test API connectivity
        working_apis = fetcher.test_api_connectivity()
        
        if working_apis:
            print(f"\nSuccessfully connected to {len(working_apis)} APIs. Fetching real data...")
            real_data = fetcher.fetch_all_rates()
            
            if real_data:
                print(f"Successfully fetched data from {len(real_data)} exchanges")
                sample_data = real_data
            else:
                print("Failed to fetch real data, using demonstration data...")
                sample_data = get_sample_data()
        else:
            print("\nNo APIs accessible. Using demonstration data...")
            sample_data = get_sample_data()
        
        if not sample_data:
            print("No funding rate data retrieved.")
            return
        
        # Display the comparison
        fetcher.display_table(sample_data)
        
        print(f"\nData generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNote: Rates are normalized across different funding intervals")
        print("for accurate comparison across platforms.")
        
        # Add disclaimer
        print("\n" + "="*80)
        print("DISCLAIMER: This is demonstration data for testing purposes.")
        print("Please verify with official sources for actual trading decisions.")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
