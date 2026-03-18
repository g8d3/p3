"""CLI entry point for subnet trader.

Usage:
    python -m subnet_trader analyze [--json|--csv] [--top N]
    python -m subnet_trader signals [--netuid N] [--json|--csv]
    python -m subnet_trader history [--days N]
"""

import argparse
import csv
import io
import sys

from subnet_trader.config import load_config
from subnet_trader.strategy import SubnetAnalyzer
from subnet_trader.executor import Executor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subnet_trader",
        description="Bittensor subnet rotation strategy analyzer",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config YAML file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")
    analyze_parser.add_argument("--csv", action="store_true", help="Output as CSV")
    analyze_parser.add_argument("--top", type=int, default=None, help="Number of top subnets")
    analyze_parser.add_argument("--dry-run", action="store_true", default=None, help="Dry run mode")
    analyze_parser.add_argument("--tao", type=float, default=100.0, help="Total TAO to allocate")
    analyze_parser.add_argument("--execute", action="store_true", help="Execute orders after analysis")

    # signals command
    signals_parser = subparsers.add_parser("signals", help="Show signal breakdown")
    signals_parser.add_argument("--netuid", type=int, default=None, help="Specific subnet ID")
    signals_parser.add_argument("--json", action="store_true", help="Output as JSON")
    signals_parser.add_argument("--csv", action="store_true", help="Output as CSV")

    # history command
    history_parser = subparsers.add_parser("history", help="Show historical data")
    history_parser.add_argument("--days", type=int, default=7, help="Days of history")

    return parser


def format_csv(data: list[dict]) -> str:
    """Format list of dicts as CSV."""
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def cmd_analyze(args, config):
    """Run analysis command."""
    if args.top:
        config.top_n = args.top
    if args.dry_run is not None:
        config.dry_run = args.dry_run

    analyzer = SubnetAnalyzer(config)
    try:
        result = analyzer.analyze(total_tao=args.tao)

        if args.json:
            print(result.to_json())
            return

        if args.csv:
            # CSV output: subnets
            rows = []
            for s in result.subnets:
                rows.append({
                    "rank": s.rank,
                    "netuid": s.netuid,
                    "name": s.name,
                    "composite": round(s.composite, 4),
                    "alpha_price": round(s.raw_data.alpha_price, 6),
                    "emission_share": round(s.raw_data.emission_share, 6),
                    "yield_score": round(s.signals.yield_score, 3),
                    "momentum_score": round(s.signals.momentum_score, 3),
                    "price_trend_score": round(s.signals.price_trend_score, 3),
                    "volume_score": round(s.signals.volume_score, 3),
                    "age_score": round(s.signals.age_score, 3),
                })
            print(format_csv(rows))
            return

        # Human-readable
        print(f"\n{'='*60}")
        print(f"  Subnet Analysis — {result.timestamp}")
        print(f"{'='*60}\n")

        for s in result.subnets:
            print(f"  #{s.rank} Subnet {s.netuid} ({s.name})")
            print(f"     Composite: {s.composite:.4f}")
            print(f"     Yield: {s.signals.yield_score:.3f}  "
                  f"Momentum: {s.signals.momentum_score:.3f}  "
                  f"Price: {s.signals.price_trend_score:.3f}  "
                  f"Volume: {s.signals.volume_score:.3f}  "
                  f"Age: {s.signals.age_score:.3f}")
            print(f"     Price: {s.raw_data.alpha_price:.6f} TAO  "
                  f"Emission: {s.raw_data.emission_share:.4f}")
            print()

        if result.orders:
            print(f"  Orders:")
            executor = Executor(config)
            results = executor.execute(result.orders)
            print(executor.format_results(results))
        else:
            print("  No rebalance needed.")

        print()

    finally:
        analyzer.close()


def cmd_signals(args, config):
    """Show signal breakdown for subnets."""
    from subnet_trader.chain import SubnetChainClient

    client = SubnetChainClient(network=config.network)
    try:
        subnets = client.get_all_subnets()

        if args.netuid is not None:
            subnets = [s for s in subnets if s.netuid == args.netuid]
            if not subnets:
                print(f"Subnet {args.netuid} not found")
                return

        from subnet_trader.signals import compute_all_signals
        import time
        current_block = int(time.time() // 12)
        signals_map = compute_all_signals(subnets, {}, {}, current_block)

        if args.json:
            output = {
                s.netuid: {
                    "name": s.name,
                    "signals": signals_map[s.netuid].to_dict(),
                }
                for s in subnets
            }
            import json
            print(json.dumps(output, indent=2))
            return

        if args.csv:
            rows = []
            for s in subnets:
                sig = signals_map[s.netuid]
                rows.append({
                    "netuid": s.netuid,
                    "name": s.name,
                    "alpha_price": round(s.alpha_price, 6),
                    "yield_score": round(sig.yield_score, 3),
                    "momentum_score": round(sig.momentum_score, 3),
                    "price_trend_score": round(sig.price_trend_score, 3),
                    "volume_score": round(sig.volume_score, 3),
                    "age_score": round(sig.age_score, 3),
                })
            print(format_csv(rows))
            return

        for s in subnets:
            sig = signals_map[s.netuid]
            print(f"  Subnet {s.netuid} ({s.name}):")
            print(f"    Price: {s.alpha_price:.6f} TAO")
            print(f"    Yield:     {sig.yield_score:.3f}")
            print(f"    Momentum:  {sig.momentum_score:.3f}")
            print(f"    Price:     {sig.price_trend_score:.3f}")
            print(f"    Volume:    {sig.volume_score:.3f}")
            print(f"    Age:       {sig.age_score:.3f}")
            print()
    finally:
        client.close()


def cmd_history(args, config):
    """Show historical data."""
    from subnet_trader.db import HistoryDB

    db = HistoryDB()
    snapshots = db.get_latest_snapshot()

    if not snapshots:
        print("No historical data yet. Run 'analyze' first to collect data.")
        return

    print(f"\n  Latest snapshot ({len(snapshots)} subnets):\n")
    for s in snapshots:
        print(f"  Subnet {s['netuid']} ({s['name']}): "
              f"Price={s['alpha_price']:.6f} TAO, "
              f"Emission={s['emission_share']:.2%}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config(args.config)

    if args.command == "analyze":
        cmd_analyze(args, config)
    elif args.command == "signals":
        cmd_signals(args, config)
    elif args.command == "history":
        cmd_history(args, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
