#!/usr/bin/env python3
"""
Funding Rate CLI Tool
Reads exchange info from top_clob_perp_dexes.txt and allows users to fetch funding rates
"""

import json
import re
import sys
import argparse
from typing import Dict, List, Tuple, Optional
import requests
from datetime import datetime
import csv

def parse_exchange_data(file_path: str) -> Dict[str, Dict]:
    """Parse the exchange data from the text file"""
    exchanges = {}
    current_exchange = None
    current_api_info = {}
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Match exchange lines (e.g., "1. Lighter - $10.891B (24h volume)")
        exchange_match = re.match(r'^(\d+)\.\s+(.+?)\s+-\s+\$[\d.]+[BM]?\s+\(24h volume\)', line)
        if exchange_match:
            if current_exchange and current_api_info:
                exchanges[current_exchange] = current_api_info
            current_exchange = exchange_match.group(2).strip()
            current_api_info = {}
            i += 1
            continue
        
        # Match API docs line
        if line.startswith('   API Docs:'):
            if current_exchange:
                current_api_info['api_docs'] = line.split('API Docs:')[1].strip()
            i += 1
            continue
        
        # Match funding rate extraction section
        if line.startswith('   Funding Rate Extraction:'):
            i += 1
            funding_info = []
            current_line = lines[i] if i < len(lines) else ''
            
            # Parse funding rate info until next exchange or end
            while i < len(lines) and not (lines[i].strip().startswith(str(len(exchanges) + 1) + '.') if len(exchanges) > 0 else False):
                current_line = lines[i].strip()
                if current_line.startswith('   - Endpoint:'):
                    endpoint = current_line.split('Endpoint:')[1].strip()
                    funding_info.append(('endpoint', endpoint))
                elif current_line.startswith('   - Parameters:'):
                    params = current_line.split('Parameters:')[1].strip()
                    funding_info.append(('parameters', params))
                elif current_line.startswith('   - Method:'):
                    method = current_line.split('Method:')[1].strip()
                    funding_info.append(('method', method))
                elif current_line.startswith('   - Output Sample:'):
                    # Skip the next few lines until we find the closing ```
                    i += 1
                    sample_lines = []
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        if lines[i].strip() and not lines[i].strip().startswith('      ```'):
                            sample_lines.append(lines[i].strip()[6:])  # Remove '      ' prefix
                        i += 1
                    funding_info.append(('sample', '\n'.join(sample_lines)))
                i += 1
            
            if current_exchange:
                current_api_info['funding'] = dict(funding_info)
            continue
        
        i += 1
    
    # Add the last exchange
    if current_exchange and current_api_info:
        exchanges[current_exchange] = current_api_info
    
    return exchanges

def display_exchanges(exchanges: Dict[str, Dict]):
    """Display available exchanges"""
    print("\n=== Available Exchanges ===")
    for i, (name, info) in enumerate(exchanges.items(), 1):
        print(f"{i}. {name}")
    print()

def select_exchanges(exchanges: Dict[str, Dict]) -> Optional[List[str]]:
    """Let user select exchanges"""
    display_exchanges(exchanges)
    
    while True:
        try:
            selection = input("Enter exchange numbers separated by commas (e.g., 1,3,5): ").strip()
            if not selection:
                return []
            
            selected_indices = [int(x.strip()) for x in selection.split(',')]
            exchange_names = list(exchanges.keys())
            
            selected_exchanges = []
            for idx in selected_indices:
                if 1 <= idx <= len(exchange_names):
                    selected_exchanges.append(exchange_names[idx - 1])
                else:
                    print(f"Invalid selection: {idx}")
                    return None
            
            return selected_exchanges
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            continue

def get_pairs() -> List[str]:
    """Get trading pairs from user"""
    default_pairs = ["BTC", "ETH", "SOL"]
    pairs_input = input(f"Enter trading pairs separated by commas (default: {', '.join(default_pairs)}): ").strip()
    
    if not pairs_input:
        return default_pairs
    
    pairs = [pair.strip().upper() for pair in pairs_input.split(',')]
    return pairs

def fetch_funding_rate(exchange_name: str, pair: str, funding_info: Dict) -> Dict[str, any]:
    """Fetch funding rate for a specific exchange and pair"""
    try:
        if 'hyperliquid' in exchange_name.lower():
            # Hyperliquid uses POST
            response = requests.post('https://api.hyperliquid.xyz/info', 
                                json={'type': 'funding'}, 
                                timeout=10)
        elif 'aster' in exchange_name.lower():
            # Aster
            url = f"https://fapi.asterdex.com/fapi/v1/fundingRate?symbol={pair}USDT"
            response = requests.get(url, timeout=10)
        elif 'lighter' in exchange_name.lower():
            # Lighter
            url = f"https://mainnet.zklighter.elliot.ai/funding?symbol={pair}"
            response = requests.get(url, timeout=10)
        elif 'edgex' in exchange_name.lower():
            # edgeX
            url = f"https://pro.edgex.exchange/api/v1/funding-rate?market={pair}"
            response = requests.get(url, timeout=10)
        elif 'apex' in exchange_name.lower():
            # ApeX
            url = f"https://api.pro.apex.exchange/v1/funding?symbol={pair}USDT"
            response = requests.get(url, timeout=10)
        elif 'grvt' in exchange_name.lower():
            # Grvt
            url = f"https://api-docs.grvt.io/funding-rate?instrument={pair}_USDT_Perp"
            response = requests.get(url, timeout=10)
        elif 'extended' in exchange_name.lower():
            # Extended
            url = f"https://api.docs.extended.exchange/funding-rate?market={pair}"
            response = requests.get(url, timeout=10)
        elif 'paradex' in exchange_name.lower():
            # Paradex
            url = f"https://api.prod.paradex.trade/v1/funding-data?market={pair}-USD-PERP"
            response = requests.get(url, timeout=10)
        elif 'pacifica' in exchange_name.lower():
            # Pacifica
            url = f"https://api.pacifica.fi/api/v1/funding_rate/history?symbol={pair}"
            response = requests.get(url, timeout=10)
        elif 'reya' in exchange_name.lower():
            # Reya
            url = f"https://api.reya.xyz/v2/funding?market={pair}"
            response = requests.get(url, timeout=10)
        else:
            return {
                'exchange': exchange_name,
                'pair': pair,
                'error': 'Exchange not supported for API calls',
                'timestamp': datetime.now().isoformat()
            }
        
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    'exchange': exchange_name,
                    'pair': pair,
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                }
            except json.JSONDecodeError:
                return {
                    'exchange': exchange_name,
                    'pair': pair,
                    'error': 'Invalid JSON response',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error'
                }
        else:
            return {
                'exchange': exchange_name,
                'pair': pair,
                'error': f'HTTP {response.status_code}',
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
            
    except requests.RequestException as e:
        return {
            'exchange': exchange_name,
            'pair': pair,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        }

def display_results(results: List[Dict]):
    """Display funding rate results"""
    print("\n=== Funding Rate Results ===")
    for result in results:
        print(f"\nExchange: {result['exchange']}")
        print(f"Pair: {result['pair']}")
        print(f"Status: {result['status']}")
        print(f"Timestamp: {result['timestamp']}")
        
        if result['status'] == 'success':
            print("Data:")
            print(json.dumps(result['data'], indent=2))
        else:
            print(f"Error: {result['error']}")
        print("-" * 50)

def export_to_csv(results: List[Dict], filename: str):
    """Export results to CSV file"""
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['exchange', 'pair', 'status', 'timestamp', 'data', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            # Convert data dict to string for CSV
            result_copy = result.copy()
            if 'data' in result_copy and isinstance(result_copy['data'], dict):
                result_copy['data'] = json.dumps(result_copy['data'])
            writer.writerow(result_copy)
    
    print(f"\nResults exported to {filename}")

def export_to_json(results: List[Dict], filename: str):
    """Export results to JSON file"""
    with open(filename, 'w') as jsonfile:
        json.dump(results, jsonfile, indent=2)
    
    print(f"\nResults exported to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Funding Rate CLI Tool')
    parser.add_argument('--file', '-f', default='top_clob_perp_dexes.txt',
                       help='Path to exchange data file')
    parser.add_argument('--export-csv', help='Export results to CSV file')
    parser.add_argument('--export-json', help='Export results to JSON file')
    
    args = parser.parse_args()
    
    try:
        exchanges = parse_exchange_data(args.file)
        print(f"Loaded {len(exchanges)} exchanges from {args.file}")
        
        selected_exchanges = select_exchanges(exchanges)
        if selected_exchanges is None:
            return
        
        pairs = get_pairs()
        print(f"\nSelected exchanges: {', '.join(selected_exchanges)}")
        print(f"Selected pairs: {', '.join(pairs)}")
        
        # Fetch funding rates
        results = []
        total_requests = len(selected_exchanges) * len(pairs)
        current_request = 0
        
        print(f"\nFetching funding rates... ({total_requests} total requests)")
        
        for exchange in selected_exchanges:
            if exchange in exchanges:
                funding_info = exchanges[exchange].get('funding', {})
                for pair in pairs:
                    current_request += 1
                    print(f"[{current_request}/{total_requests}] Fetching {exchange} - {pair}...")
                    result = fetch_funding_rate(exchange, pair, funding_info)
                    results.append(result)
        
        display_results(results)
        
        # Export if requested
        if args.export_csv:
            export_to_csv(results, args.export_csv)
        
        if args.export_json:
            export_to_json(results, args.export_json)
            
    except FileNotFoundError:
        print(f"Error: File {args.file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()