"""CLI entry point for subnet trader."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from subnet_trader import (
    SubnetChainClient,
    TaostatsClient,
    AnalysisResult,
)
from subnet_trader.models import CompositeScore
from subnet_trader.signals import compute_all_signals
from subnet_trader.strategy import rank_subnets, generate_orders
from subnet_trader.output import analysis_to_csv, write_csv


async def fetch_data(chain_client: SubnetChainClient, tao_client: TaostatsClient):
    """Fetch and merge data from chain and taostats.io."""
    from subnet_trader.tao_api import fetch_all_subnet_data
    return await fetch_all_subnet_data(chain_client, tao_client)


def analyze(subnets, top_n=5, output_csv=False):
    """Run the analysis on subnets."""
    now = datetime.now()
    
    # Compute signals
    signals = compute_all_signals(subnets, now)
    
    # Rank subnets
    ranked = rank_subnets(subnets, signals)
    
    # Determine which signals are included
    all_signals = set()
    for sig in signals.values():
        if sig.yield_score is not None:
            all_signals.add("yield")
        if sig.volume_score is not None:
            all_signals.add("volume")
        if sig.momentum_1h_score is not None:
            all_signals.add("momentum_1h")
        if sig.momentum_1d_score is not None:
            all_signals.add("momentum_1d")
        if sig.momentum_7d_score is not None:
            all_signals.add("momentum_7d")
        if sig.age_score is not None:
            all_signals.add("age")
    
    # Generate orders
    orders = generate_orders(ranked, total_stake_tao=1000.0, top_n=top_n)
    
    result = AnalysisResult(
        timestamp=now.isoformat(),
        subnets=ranked,
        orders=orders,
        signals_included=sorted(list(all_signals)),
    )
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Bittensor Subnet Trading Strategy")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze subnets and generate rankings")
    analyze_parser.add_argument("--top", "-n", type=int, default=5, help="Number of top subnets to stake in")
    analyze_parser.add_argument("--csv", action="store_true", help="Output as CSV")
    analyze_parser.add_argument("--output", "-o", type=str, help="Output file")
    analyze_parser.add_argument("--mock", action="store_true", help="Use mock data")
    
    # signals command
    signals_parser = subparsers.add_parser("signals", help="Show signals for a subnet")
    signals_parser.add_argument("netuid", type=int, help="Subnet netuid")
    signals_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        # Initialize clients
        chain_client = SubnetChainClient(mock=args.mock)
        tao_client = TaostatsClient()
        
        try:
            if args.mock:
                subnets = chain_client.get_all_subnets()
                result = analyze(subnets, top_n=args.top)
            else:
                subnets = asyncio.run(fetch_data(chain_client, tao_client))
                result = analyze(subnets, top_n=args.top)
            
            if args.csv:
                csv_output = analysis_to_csv(result)
                if args.output:
                    Path(args.output).write_text(csv_output)
                else:
                    print(csv_output)
            else:
                print(result.to_json())
                
        finally:
            chain_client.close()
            
    elif args.command == "signals":
        print(f"Showing signals for netuid {args.netuid}")
        # TODO: implement
        print("Not yet implemented")
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
