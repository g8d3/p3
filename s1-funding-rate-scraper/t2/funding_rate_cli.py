# funding_rate_cli.py
"""
Funding Rate CLI Tool for Top CLOB Perp DEXes
Fetches funding rates from multiple decentralized exchanges
"""

import sys
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
import csv

try:
    from tabulate import tabulate
except ImportError:
    print("Installing required package: tabulate")
    import subprocess
    subprocess.check_call(["uv", "pip", "install", "tabulate"])
    from tabulate import tabulate

from exchanges import (
    LighterClient, AsterClient, HyperliquidClient, EdgeXClient, ApexClient,
    GrvtClient, ExtendedClient, ParadexClient, PacificaClient, ReyaClient
)
from utils import format_timestamp


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

            # Get all funding rates from this exchange
            all_rates = client.get_funding_rates()

            # Filter by requested pairs
            for rate_data in all_rates:
                symbol = rate_data.get("symbol", "").replace("USDT", "").replace("-USD", "")
                if symbol in pairs:
                    results.append(rate_data)

        return results

    def display_results(self, results: List[Dict[str, Any]]):
        """Display results in a table"""
        if not results:
            print("\nNo funding rate data retrieved.")
            return

        table_data = []
        for result in results:
            funding_rate = result['funding_rate']
            table_data.append([
                result["exchange"],
                result["symbol"],
                f"{funding_rate * 100:.4f}%",  # Display as percentage per hour
                f"{funding_rate:.8f}",  # Raw funding rate
                result.get("funding_period", "8h"),  # Default to 8h if not specified
                format_timestamp(result.get("funding_time")),
                format_timestamp(result.get("next_funding_time")),
                result.get("mark_price", "N/A"),
                result.get("oracle_price", "N/A"),
                result.get("premium", "N/A")
            ])

        headers = ["Exchange", "Symbol", "Funding Rate (%/hr)", "Raw Rate", "Period", "Funding Time", "Next Funding Time", "Mark Price", "Oracle Price", "Premium"]
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
                fieldnames = ["exchange", "symbol", "funding_rate_percent", "funding_rate_raw", "funding_period",
                              "funding_time", "next_funding_time", "mark_price", "oracle_price", "premium",
                              "source_exchange", "market_id", "historical_count", "funding_interval", "timestamp"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for result in results:
                    row = {
                        "exchange": result.get("exchange"),
                        "symbol": result.get("symbol"),
                        "funding_rate_percent": f"{result.get('funding_rate', 0) * 100:.4f}%",
                        "funding_rate_raw": result.get("funding_rate"),
                        "funding_period": result.get("funding_period", "8h"),
                        "funding_time": format_timestamp(result.get("funding_time")),
                        "next_funding_time": format_timestamp(result.get("next_funding_time")),
                        "mark_price": result.get("mark_price"),
                        "oracle_price": result.get("oracle_price"),
                        "premium": result.get("premium"),
                        "source_exchange": result.get("source_exchange"),
                        "market_id": result.get("market_id"),
                        "historical_count": result.get("historical_count"),
                        "funding_interval": result.get("funding_interval"),
                        "timestamp": result.get("timestamp")
                    }
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

        export_choice = 'n'
        filename = ''
        if results:
            export_choice = input("\nExport data to CSV? (y/n): ").strip().lower()
            if export_choice in ['y', 'yes']:
                filename = input("Enter filename (press Enter for default): ").strip()
                self.export_data(results, filename if filename else None)

        # Print non-interactive equivalent
        equivalent = f"python {sys.argv[0]} --exchanges {' '.join(exchanges)} --pairs {' '.join(pairs)}"
        if export_choice in ['y', 'yes']:
            export_filename = filename if filename else f"funding_rates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            equivalent += f" --export {export_filename}"
        print(f"\nNon-interactive equivalent: {equivalent}")

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