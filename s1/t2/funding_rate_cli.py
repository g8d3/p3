#!/usr/bin/env python3
"""
Funding Rate CLI Tool for Top CLOB Perp DEXes
Fetches funding rates from multiple decentralized exchanges
"""

import requests
import json
import sys
import argparse
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import csv

try:
    from tabulate import tabulate
except ImportError:
    print("Installing required package: tabulate")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
    from tabulate import tabulate


class ExchangeAPIClient:
    """Base class for exchange API clients"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get funding rate for a specific symbol"""
        raise NotImplementedError


class LighterClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Lighter", "https://mainnet.zklighter.elliot.ai")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/funding", params={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("symbol", symbol),
                "funding_rate": float(data.get("funding_rate", 0)),
                "funding_time": data.get("funding_time"),
                "next_funding_time": data.get("next_funding_time")
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class AsterClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Aster", "https://fapi.asterdex.com")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/fapi/v1/fundingRate", params={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200:
                funding_data = data.get("data", {})
                return {
                    "exchange": self.name,
                    "symbol": funding_data.get("symbol", symbol),
                    "funding_rate": float(funding_data.get("fundingRate", 0)),
                    "funding_interval": funding_data.get("fundingInterval"),
                    "next_funding_rate": float(funding_data.get("nextFundingRate", 0))
                }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class HyperliquidClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Hyperliquid", "https://api.hyperliquid.xyz")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.post(f"{self.base_url}/info", json={"type": "funding"}, timeout=10)
            response.raise_for_status()
            data = response.json()
            funding_list = data.get("funding", [])
            
            for item in funding_list:
                if item.get("coin") == symbol:
                    return {
                        "exchange": self.name,
                        "symbol": symbol,
                        "funding_rate": float(item.get("fundingRate", 0)),
                        "funding_rate_px": float(item.get("fundingRatePx", 0)),
                        "next_funding_time": item.get("nextFundingTime")
                    }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class EdgeXClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("edgeX", "https://pro.edgex.exchange")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/api/v1/funding-rate", params={"market": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("market", symbol),
                "funding_rate": float(data.get("funding_rate", 0)),
                "funding_time": data.get("funding_time"),
                "mark_price": float(data.get("mark_price", 0))
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class ApexClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("ApeX Protocol", "https://api.pro.apex.exchange")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/v1/funding", params={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("symbol", symbol),
                "funding_rate": float(data.get("fundingRate", 0)),
                "funding_interval": data.get("fundingInterval"),
                "last_funding_time": data.get("lastFundingTime")
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class GrvtClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Grvt", "https://api-docs.grvt.io")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/funding-rate", params={"instrument": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("instrument", symbol),
                "funding_rate": float(data.get("funding_rate", 0)),
                "funding_time": data.get("funding_time"),
                "mark_price": float(data.get("mark_price", 0))
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class ExtendedClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Extended", "https://api.docs.extended.exchange")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/funding-rate", params={"market": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("market", symbol),
                "funding_rate": float(data.get("funding_rate", 0)),
                "timestamp": data.get("timestamp")
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class ParadexClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Paradex", "https://api.prod.paradex.trade")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/v1/funding-data", params={"market": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if results:
                latest = results[0]
                return {
                    "exchange": self.name,
                    "symbol": symbol,
                    "funding_rate": float(latest.get("funding_rate", 0)),
                    "funding_time": latest.get("funding_time"),
                    "oracle_price": float(latest.get("oracle_price", 0))
                }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class PacificaClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Pacifica", "https://api.pacifica.fi")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/api/v1/funding_rate/history", params={"symbol": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("data"):
                latest = data["data"][0]
                return {
                    "exchange": self.name,
                    "symbol": symbol,
                    "funding_rate": float(latest.get("funding_rate", 0)),
                    "created_at": latest.get("created_at"),
                    "oracle_price": float(latest.get("oracle_price", 0))
                }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class ReyaClient(ExchangeAPIClient):
    def __init__(self):
        super().__init__("Reya", "https://api.reya.xyz")
    
    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.session.get(f"{self.base_url}/v2/funding", params={"market": symbol}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "exchange": self.name,
                "symbol": data.get("market", symbol),
                "funding_rate": float(data.get("current_funding_rate", 0)),
                "next_funding_time": data.get("next_funding_time"),
                "mark_price": float(data.get("mark_price", 0))
            }
        except Exception as e:
            print(f"Error fetching {self.name} {symbol}: {e}")
            return None


class FundingRateCLI:
    def __init__(self):
        self.exchanges = {
            "lighter": LighterClient(),
            "aster": AsterClient(),
            "hyperliquid": HyperliquidClient(),
            "edgex": EdgeXClient(),
            "apex": ApexClient(),
            "grvt": GrvtClient(),
            "extended": ExtendedClient(),
            "paradex": ParadexClient(),
            "pacifica": PacificaClient(),
            "reya": ReyaClient()
        }
        
        self.common_pairs = ["BTC", "ETH", "SOL", "DOGE", "ADA", "MATIC", "DOT", "AVAX", "LINK", "UNI"]
    
    def display_exchanges(self):
        """Display available exchanges"""
        print("\nAvailable Exchanges:")
        for i, key in enumerate(self.exchanges.keys(), 1):
            print(f"{i:2d}. {key.capitalize()} - {self.exchanges[key].name}")
    
    def display_pairs(self):
        """Display common trading pairs"""
        print("\nCommon Trading Pairs:")
        for i, pair in enumerate(self.common_pairs, 1):
            print(f"{i:2d}. {pair}")
    
    def select_exchanges(self) -> List[str]:
        """Let user select exchanges"""
        self.display_exchanges()
        
        while True:
            try:
                selection = input("\nEnter exchange numbers separated by commas (e.g., 1,3,5) or 'all': ").strip().lower()
                
                if selection == 'all':
                    return list(self.exchanges.keys())
                
                indices = [int(x.strip()) for x in selection.split(',')]
                exchange_keys = list(self.exchanges.keys())
                selected = [exchange_keys[i-1] for i in indices if 1 <= i <= len(exchange_keys)]
                
                if selected:
                    return selected
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
    
    def select_pairs(self) -> List[str]:
        """Let user select trading pairs"""
        self.display_pairs()
        
        while True:
            try:
                selection = input("\nEnter pair numbers separated by commas (e.g., 1,3,5) or 'all': ").strip().lower()
                
                if selection == 'all':
                    return self.common_pairs
                
                indices = [int(x.strip()) for x in selection.split(',')]
                selected = [self.common_pairs[i-1] for i in indices if 1 <= i <= len(self.common_pairs)]
                
                if selected:
                    return selected
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
    
    def fetch_funding_rates(self, exchanges: List[str], pairs: List[str]) -> List[Dict[str, Any]]:
        """Fetch funding rates for selected exchanges and pairs"""
        results = []
        
        for exchange_key in exchanges:
            client = self.exchanges[exchange_key]
            print(f"\nFetching from {client.name}...")
            
            for pair in pairs:
                rate_data = client.get_funding_rate(pair)
                if rate_data:
                    results.append(rate_data)
        
        return results
    
    def display_results(self, results: List[Dict[str, Any]]):
        """Display results in a table"""
        if not results:
            print("\nNo funding rate data retrieved.")
            return
        
        table_data = []
        for result in results:
            table_data.append([
                result["exchange"],
                result["symbol"],
                f"{result['funding_rate']:.6f}",
                result.get("funding_time", "N/A"),
                result.get("next_funding_time", "N/A")
            ])
        
        headers = ["Exchange", "Symbol", "Funding Rate", "Funding Time", "Next Funding Time"]
        print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}")
    
    def export_data(self, results: List[Dict[str, Any]], filename: Optional[str] = None):
        """Export results to CSV"""
        if not results:
            print("No data to export.")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"funding_rates_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["exchange", "symbol", "funding_rate", "funding_time", "next_funding_time", 
                             "funding_interval", "mark_price", "oracle_price", "timestamp"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    row = {field: result.get(field, "N/A") for field in fieldnames}
                    writer.writerow(row)
            
            print(f"\nData exported to {filename}")
        except Exception as e:
            print(f"Error exporting data: {e}")
    
    def run_interactive(self):
        """Run interactive CLI"""
        print("=== Funding Rate CLI Tool ===")
        print("Fetch funding rates from top CLOB perpetual DEXes\n")
        
        exchanges = self.select_exchanges()
        pairs = self.select_pairs()
        
        print(f"\nFetching funding rates for {len(pairs)} pairs from {len(exchanges)} exchanges...")
        results = self.fetch_funding_rates(exchanges, pairs)
        
        self.display_results(results)
        
        if results:
            export_choice = input("\nExport data to CSV? (y/n): ").strip().lower()
            if export_choice in ['y', 'yes']:
                filename = input("Enter filename (press Enter for default): ").strip()
                self.export_data(results, filename if filename else None)
    
    def run_cli(self, args):
        """Run with command line arguments"""
        exchanges = args.exchanges if args.exchanges else list(self.exchanges.keys())
        pairs = args.pairs if args.pairs else self.common_pairs
        
        print(f"Fetching funding rates for {len(pairs)} pairs from {len(exchanges)} exchanges...")
        results = self.fetch_funding_rates(exchanges, pairs)
        
        self.display_results(results)
        
        if args.export:
            self.export_data(results, args.export)


def main():
    cli = FundingRateCLI()
    
    parser = argparse.ArgumentParser(description="Funding Rate CLI for CLOB Perp DEXes")
    parser.add_argument("--exchanges", nargs="+", help="Exchanges to query (e.g., lighter hyperliquid)")
    parser.add_argument("--pairs", nargs="+", help="Trading pairs to query (e.g., BTC ETH)")
    parser.add_argument("--export", help="Export results to CSV file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive or not args.exchanges and not args.pairs:
        cli.run_interactive()
    else:
        cli.run_cli(args)


if __name__ == "__main__":
    main()