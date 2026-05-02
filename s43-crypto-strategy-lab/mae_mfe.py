import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import matplotlib.pyplot as plt
import seaborn as sns
import os
import pickle
from datetime import datetime, timedelta
import argparse
import json

class ExcursionAnalyzer:
    def __init__(self, tickers, tf="1h", period="2y", cache_dir="./cache", cache_days=1):
        self.tickers = tickers
        self.tf = tf
        self.period = period
        self.data = {}
        self.cache_dir = cache_dir
        self.cache_days = cache_days
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_data(self, force_refresh=False):
        print(f"Fetching data for {self.tickers}...")
        for ticker in self.tickers:
            cache_file = os.path.join(self.cache_dir, f"{ticker}_{self.tf}_{self.period}.pkl")
            load_from_cache = False
            if not force_refresh and os.path.exists(cache_file):
                # Check age
                mod_time = os.path.getmtime(cache_file)
                age_days = (datetime.now() - datetime.fromtimestamp(mod_time)).total_seconds() / 86400
                if age_days <= self.cache_days:
                    print(f"  {ticker}: loading from cache (age {age_days:.1f} days)")
                    try:
                        df = pd.read_pickle(cache_file)
                        load_from_cache = True
                    except Exception as e:
                        print(f"  {ticker}: cache load failed ({e}), re-downloading")
            if not load_from_cache:
                df = yf.download(ticker, period=self.period, interval=self.tf)
                print(f"  {ticker}: shape {df.shape}, columns {list(df.columns)}")
                if not df.empty:
                    # Flatten MultiIndex columns if present
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(1)
                    # Save to cache
                    df.to_pickle(cache_file)
                    print(f"  {ticker}: saved to cache")
                else:
                    print(f"  {ticker}: empty data, not caching")
            if not df.empty:
                self.data[ticker] = df

    def analyze(self, rsi_len=14, oversold=30, overbought=70, window=24):
        all_events = []

        for ticker, df in self.data.items():
            # Calculate Indicators
            df = df.copy()
            df['RSI'] = ta.rsi(df['Close'], length=rsi_len)
            
            # Find Signal Crosses (First candle to hit threshold)
            df['long_signal'] = (df['RSI'] < oversold) & (df['RSI'].shift(1) >= oversold)
            df['short_signal'] = (df['RSI'] > overbought) & (df['RSI'].shift(1) <= overbought)

            for i in range(len(df) - window):
                if df['long_signal'].iloc[i]:
                    event_type = f"rsi<{oversold}"
                    event = self._process_event(df, i, window, mode='long', event_type=event_type)
                    event['ticker'] = ticker
                    all_events.append(event)
                elif df['short_signal'].iloc[i]:
                    event_type = f"rsi>{overbought}"
                    event = self._process_event(df, i, window, mode='short', event_type=event_type)
                    event['ticker'] = ticker
                    all_events.append(event)

        print(f"Total events found: {len(all_events)}")
        return pd.DataFrame(all_events)

    def _process_event(self, df, start_idx, window, mode, event_type=None):
        trigger_price = df['Close'].iloc[start_idx]
        trigger_time = df.index[start_idx]
        future_slice = df.iloc[start_idx : start_idx + window]
        close_prices = future_slice['Close'].values.tolist()
        
        # Compute MAE and MFE as before
        if mode == 'long':
            max_adverse = future_slice['Low'].min()
            max_favorable = future_slice['High'].max()
            mae = (trigger_price - max_adverse) / trigger_price
            mfe = (max_favorable - trigger_price) / trigger_price
        else:
            max_adverse = future_slice['High'].max()
            max_favorable = future_slice['Low'].min()
            mae = (max_adverse - trigger_price) / trigger_price
            mfe = (trigger_price - max_favorable) / trigger_price
            
        return {
            'time': trigger_time,
            'mae_pct': mae * 100,
            'mfe_pct': mfe * 100,
            'type': event_type if event_type else mode,
            'window_prices': close_prices
        }

# --- Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAE/MFE Excursion Analyzer")
    parser.add_argument("--tickers", nargs="+", default=["BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "AAPL"],
                        help="List of tickers to analyze")
    parser.add_argument("--tf", default="1h", help="Timeframe (e.g., 1h, 1d)")
    parser.add_argument("--period", default="1y", help="Period for yfinance (e.g., 1y, 2y)")
    parser.add_argument("--rsi_len", type=int, default=14, help="RSI length")
    parser.add_argument("--oversold", type=int, default=25, help="Oversold threshold")
    parser.add_argument("--overbought", type=int, default=75, help="Overbought threshold")
    parser.add_argument("--window", type=int, default=48, help="Window for MAE/MFE calculation")
    parser.add_argument("--cache_days", type=int, default=1, help="Cache freshness in days")
    parser.add_argument("--cache_dir", default="./cache", help="Directory for cache files")
    parser.add_argument("--force_refresh", action="store_true", help="Force re-download data")
    parser.add_argument("--no_plot", action="store_true", help="Skip showing plot")
    parser.add_argument("--output", default=None, help="Save plot to file (e.g., plot.png)")
    parser.add_argument("--csv_output", default=None, help="Save results to CSV file (e.g., results.csv)")
    parser.add_argument("--csv_auto", action="store_true", help="Save results to CSV with auto-generated filename")
    args = parser.parse_args()
    
    analyzer = ExcursionAnalyzer(args.tickers, tf=args.tf, period=args.period, cache_dir=args.cache_dir, cache_days=args.cache_days)
    analyzer.fetch_data(force_refresh=args.force_refresh)
    
    results = analyzer.analyze(rsi_len=args.rsi_len, oversold=args.oversold, overbought=args.overbought, window=args.window)
    
    # Save to CSV if requested
    csv_file = args.csv_output
    if args.csv_auto and csv_file is None:
        # Generate descriptive filename
        tickers_str = '_'.join(sorted(args.tickers))[:30]  # limit length
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"mae_mfe_{tickers_str}_{args.tf}_{args.period}_{args.window}_{args.rsi_len}_{args.oversold}_{args.overbought}_{timestamp}.csv"
    
    if csv_file and not results.empty:
        # Convert list columns to JSON strings for CSV compatibility
        df_export = results.copy()
        list_cols = ['window_prices']
        for col in list_cols:
            if col in df_export.columns:
                df_export[col] = df_export[col].apply(json.dumps)
        df_export.to_csv(csv_file, index=False)
        print(f"Results saved to {csv_file}")
    
    if results.empty:
        print("No events found. Check data and parameters.")
    else:
        print("Results columns:", results.columns.tolist())
        print("Results shape:", results.shape)
        print(results.head())
        if not args.no_plot or args.output:
            # Visualization of Probabilities
            plt.figure(figsize=(12, 6))
            sns.kdeplot(data=results, x="mae_pct", hue="type", fill=True, common_norm=False)
            plt.title("Probability Distribution of Overshoot (MAE %)")
            plt.axvline(results['mae_pct'].median(), color='red', linestyle='--', label='Median Overshoot')
            
            # Determine output file
            output_file = args.output
            if output_file is None and not args.no_plot:
                output_file = "mae_mfe_plot.png"
            
            if output_file:
                plt.savefig(output_file, dpi=150, bbox_inches='tight')
                print(f"Plot saved to {output_file}")
            
            if not args.no_plot:
                try:
                    plt.show()
                except Exception as e:
                    print(f"Could not display plot (headless environment?): {e}")
                    plt.close()
            else:
                plt.close()
        
        print(f"Average Reversal (MFE): {results['mfe_pct'].mean():.2f}%")
        print(f"75th Percentile Overshoot (MAE): {results['mae_pct'].quantile(0.75):.2f}%")