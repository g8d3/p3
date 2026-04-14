# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Streamlit web dashboard for comparing grid trading vs TP/SL trading strategies.
"""

import streamlit as st
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent))

from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.model.data import BarType
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.currencies import BTC, USDT

from backtest.runner import generate_synthetic_bars, generate_multiple_synthetic_bars, run_backtest
from strategies.grid_trading import GridTrading, GridTradingConfig
from strategies.tpsl_trading import TPSLTrading, TPSLTradingConfig


MAX_BATCH_DATASETS = 10
PRICE_SAMPLE_EVERY = 10
MAX_SIGNAL_LEVELS = 20
MAX_TABLE_ROWS = 500


st.set_page_config(page_title="Hyperliquid Trading Game", layout="wide")

st.title("Hyperliquid Trading Game")
st.markdown("""
Learn trading by comparing **Grid Trading** vs **Take-Profit/Stop-Loss Trading** strategies.
Adjust parameters, run backtests, and see which strategy performs better!
""")


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def _report_to_df(report):
    if report is None:
        return pd.DataFrame()
    if isinstance(report, pd.DataFrame):
        return report.copy()
    if isinstance(report, dict):
        try:
            return pd.DataFrame(report)
        except Exception:
            try:
                return pd.DataFrame.from_records(report)
            except Exception:
                return pd.DataFrame([report])
    if isinstance(report, list):
        return pd.DataFrame(report)
    return pd.DataFrame([{'value': report}])


def _sample_price_data(data, step=PRICE_SAMPLE_EVERY):
    if data is None:
        return None
    df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if df.empty:
        return None
    df = df.reset_index()
    sampled = df.iloc[::max(1, step)].copy()
    if len(df) > 0 and (sampled.empty or sampled.index[-1] != df.index[-1]):
        sampled = pd.concat([sampled, df.iloc[[-1]]], ignore_index=True)
    return _json_safe(sampled.to_dict(orient='records'))


def _find_column(df, aliases):
    lookup = {str(col).lower(): col for col in df.columns}
    for alias in aliases:
        col = lookup.get(alias.lower())
        if col is not None:
            return col
    return None


def _standardize_trade_table(fills_report, positions_report):
    df = _report_to_df(positions_report)
    if df.empty:
        df = _report_to_df(fills_report)

    columns = ['Entry Time', 'Exit Time', 'Side', 'Quantity', 'Entry Price', 'Exit Price', 'Duration', 'PnL']
    if df.empty:
        return pd.DataFrame(columns=columns)

    column_map = {
        'Entry Time': ['entry_time', 'open_time', 'opened_at', 'entry_ts', 'entry_datetime'],
        'Exit Time': ['exit_time', 'close_time', 'closed_at', 'exit_ts', 'exit_datetime'],
        'Side': ['side', 'direction', 'position_side'],
        'Quantity': ['quantity', 'qty', 'size', 'volume', 'units'],
        'Entry Price': ['entry_price', 'open_price', 'avg_entry_price', 'price_entry'],
        'Exit Price': ['exit_price', 'close_price', 'avg_exit_price', 'price_exit'],
        'Duration': ['duration', 'holding_period', 'hold_time'],
        'PnL': ['pnl', 'realized_pnl', 'profit', 'net_pnl'],
    }

    out = pd.DataFrame(index=df.index)
    for output_col, aliases in column_map.items():
        source_col = _find_column(df, aliases)
        if source_col is not None:
            out[output_col] = df[source_col]
        else:
            out[output_col] = np.nan

    if out['Duration'].isna().all():
        entry = pd.to_datetime(out['Entry Time'], errors='coerce')
        exit_ = pd.to_datetime(out['Exit Time'], errors='coerce')
        out['Duration'] = (exit_ - entry).apply(lambda x: str(x) if pd.notna(x) else '')

    return out.head(MAX_TABLE_ROWS)


def _compute_sharpe(balance_series):
    if not balance_series or len(balance_series) < 3:
        return None
    balances = pd.Series([float(v) for v in balance_series.values()])
    returns = balances.pct_change().dropna()
    if returns.empty or returns.std(ddof=0) == 0:
        return None
    return float(np.sqrt(len(returns)) * returns.mean() / returns.std(ddof=0))


def _compute_profit_factor(trade_df):
    if trade_df is None or trade_df.empty or 'PnL' not in trade_df.columns:
        return None
    pnl = pd.to_numeric(trade_df['PnL'], errors='coerce').dropna()
    gains = pnl[pnl > 0].sum()
    losses = pnl[pnl < 0].sum()
    if losses == 0:
        return None
    return float(gains / abs(losses))


def _get_trade_signals(result):
    signals = []
    for report_name in ('fills_report', 'positions_report'):
        df = _report_to_df(result.get(report_name, {}))
        if df.empty:
            continue
        time_col = _find_column(df, ['time', 'timestamp', 'created_at', 'filled_at', 'entry_time', 'exit_time'])
        price_col = _find_column(df, ['price', 'entry_price', 'exit_price', 'fill_price', 'avg_price'])
        side_col = _find_column(df, ['side', 'direction', 'action', 'order_side'])
        if time_col is None or price_col is None:
            continue
        sample = df[[c for c in [time_col, price_col, side_col] if c is not None]].head(MAX_TABLE_ROWS)
        for _, row in sample.iterrows():
            signals.append({
                'time': row[time_col],
                'price': row[price_col],
                'side': row[side_col] if side_col is not None else '',
            })
    return signals


def extract_metrics(results, strategy_name=None, user_id=None, include_series=False, include_reports=False, price_data=None):
    account_report = results.get('account_report', {}) if isinstance(results, dict) else {}
    if isinstance(account_report, dict) and 'total' in account_report:
        total_series = account_report['total']
        balances = list(total_series.values())
        if not balances:
            return None
        initial = float(balances[0])
        final = float(balances[-1])
        returns = (final - initial) / initial * 100 if initial else 0
        peak = initial
        max_dd = 0
        for b in balances:
            b_float = float(b)
            if b_float > peak:
                peak = b_float
            dd = (peak - b_float) / peak if peak else 0
            if dd > max_dd:
                max_dd = dd
        metrics = {
            'initial_balance': initial,
            'final_balance': final,
            'total_return_pct': returns,
            'max_drawdown_pct': max_dd * 100,
            'sharpe_ratio': _compute_sharpe(total_series),
        }
        if user_id is not None:
            metrics['user_id'] = user_id
        if strategy_name is not None:
            metrics['strategy'] = strategy_name
        if include_series:
            metrics['balance_series'] = _json_safe(total_series)
        if include_reports:
            fills_report = results.get('fills_report', {}) if isinstance(results, dict) else {}
            positions_report = results.get('positions_report', {}) if isinstance(results, dict) else {}
            fills_df = _report_to_df(fills_report).head(MAX_TABLE_ROWS)
            positions_df = _report_to_df(positions_report).head(MAX_TABLE_ROWS)
            trade_table = _standardize_trade_table(fills_df, positions_df)
            metrics['fills_report'] = _json_safe(fills_df.to_dict(orient='records'))
            metrics['positions_report'] = _json_safe(positions_df.to_dict(orient='records'))
            metrics['trade_table'] = _json_safe(trade_table.to_dict(orient='records'))
            metrics['profit_factor'] = _compute_profit_factor(trade_table)
        if price_data is not None:
            metrics['price_data'] = _sample_price_data(price_data)
        return metrics
    return None

# Data Generation Section
with st.expander("Data Generation", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        data_source = st.radio("Data Source", ["Synthetic", "Real"], horizontal=True)
        synthetic_selected = data_source == "Synthetic"
        instrument_choice = st.selectbox(
            "Instrument (trading pair)",
            ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            index=0,
            disabled=synthetic_selected,
            help="Select the instrument for backtesting. For synthetic data, this is just a placeholder."
        )
        timeframe = st.selectbox("Timeframe", ["4h", "8h", "12h", "1d"], index=0)
    with col2:
        num_bars = st.slider("Number of bars (backtest length)", min_value=50, max_value=1000, value=200, step=50)
        if synthetic_selected:
            start_price = st.number_input("Start price", value=30000.0, step=1000.0)
            volatility = st.slider(
                "Initial volatility (annualized)",
                min_value=0.01,
                max_value=1.0,
                value=0.02,
                step=0.01,
                help="Annualized volatility used to set initial variance in Bates model."
            )
            # Advanced Bates parameters
            with st.expander("Advanced Bates Model Parameters"):
                kappa = st.slider("Mean reversion speed", min_value=0.1, max_value=10.0, value=5.0, step=0.1)
                theta = st.slider("Long-term variance", min_value=0.0001, max_value=0.1, value=volatility**2, step=0.001, format="%.4f")
                sigma = st.slider("Volatility of volatility", min_value=0.01, max_value=1.0, value=0.1, step=0.01)
                rho = st.slider("Correlation (price-vol)", min_value=-1.0, max_value=0.0, value=-0.7, step=0.05)
                lambda_ = st.slider("Jump intensity", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
                mu_j = st.slider("Mean jump size", min_value=-0.5, max_value=0.5, value=0.0, step=0.01)
                sigma_j = st.slider("Jump volatility", min_value=0.01, max_value=1.0, value=0.05, step=0.01)
            # Batch generation
            with st.expander("Batch Generation"):
                batch_enabled = st.checkbox("Generate multiple datasets", value=False)
                if batch_enabled:
                    num_datasets = st.slider("Number of datasets to generate", min_value=2, max_value=10, value=5)
                    variation = st.slider("Parameter variation (%)", min_value=0, max_value=100, value=20, help="Uniform variation around base parameters")
                    # Store batch parameters in session state
                    st.session_state['batch_gen'] = {
                        'enabled': True,
                        'num_datasets': num_datasets,
                        'variation': variation / 100.0,  # convert to fraction
                    }
                else:
                    st.session_state['batch_gen'] = {'enabled': False}
        else:  # Real data
            st.info("Real data will be fetched from exchange (not yet implemented). Using synthetic data as placeholder.")
            start_price = st.number_input("Start price (placeholder)", value=30000.0, step=1000.0)
            volatility = st.slider("Volatility (placeholder)", min_value=0.01, max_value=0.1, value=0.02, step=0.005)
            kappa = theta = sigma = rho = lambda_ = mu_j = sigma_j = None
    # Store data generation parameters in session state for later use
    st.session_state['data_gen'] = {
        'data_source': data_source,
        'instrument': instrument_choice,
        'timeframe': timeframe,
        'num_bars': num_bars,
        'start_price': start_price,
        'volatility': volatility,
        'bates_params': {
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho,
            'lambda_': lambda_,
            'mu_j': mu_j,
            'sigma_j': sigma_j,
        } if synthetic_selected else None,
        'batch_gen': st.session_state.get('batch_gen', {'enabled': False}),
    }

# Strategy Configuration Section
st.header("Strategy Configuration")
col1, col2 = st.columns(2)
with col1:
    st.subheader("User Settings")
    user_id = st.text_input("Your Name/ID", value="Player1")
    st.subheader("Grid Trading")
    grid_step = st.number_input("Grid step (price increment)", value=100.0, step=10.0)
    num_levels = st.slider("Number of levels (each side)", min_value=1, max_value=10, value=3)
    grid_trade_size = st.number_input("Trade size (BTC)", value=0.01, step=0.001, format="%.3f")
    max_position = st.number_input("Max position (BTC)", value=0.1, step=0.01, format="%.2f")
with col2:
    st.subheader("TP/SL Trading")
    tp_pct = st.slider("Take-profit %", min_value=0.001, max_value=0.1, value=0.01, step=0.001, format="%.3f")
    sl_pct = st.slider("Stop-loss %", min_value=0.001, max_value=0.1, value=0.005, step=0.001, format="%.3f")
    level_spacing = st.number_input("Level spacing (price)", value=500.0, step=100.0)
    num_tpsl_levels = st.slider("Number of horizontal levels", min_value=1, max_value=20, value=5)
    tpsl_trade_size = st.number_input("Trade size (BTC) ", value=0.01, step=0.001, format="%.3f", key="tpsl_trade_size")
    st.subheader("Account")
    starting_usdt = st.number_input("Starting USDT", value=100000, step=10000)
    starting_btc = st.number_input("Starting BTC", value=1.0, step=0.1, format="%.1f")


def render_strategy_panel(title, results):
    st.subheader(title)
    account_report = results.get('account_report', {}) if isinstance(results, dict) else {}
    if isinstance(account_report, dict) and 'total' in account_report:
        total_series = account_report['total']
        df_balance = pd.DataFrame.from_dict(total_series, orient='index', columns=['Balance'])
        df_balance.index = pd.to_datetime(df_balance.index)
        df_balance = df_balance.sort_index()
        df_balance['Balance'] = pd.to_numeric(df_balance['Balance'], errors='coerce')
        initial_balance = float(df_balance['Balance'].iloc[0])
        final_balance = float(df_balance['Balance'].iloc[-1])
        total_return = (final_balance - initial_balance) / initial_balance * 100 if initial_balance else 0
        st.metric("Total Return", f"{total_return:.2f}%", delta=f"{final_balance:.4f} BTC")
        fig = px.line(df_balance, y='Balance', title=f'{title} Balance Over Time')
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text='Balance (BTC)')
        st.plotly_chart(fig, use_container_width=True)
        return df_balance
    st.write(account_report)
    return None


def render_results_view(grid_results, tpsl_results, data, selected_label=""):
    if selected_label:
        st.caption(selected_label)

    col1, col2 = st.columns(2)

    with col1:
        render_strategy_panel("Grid Trading", grid_results)

    with col2:
        render_strategy_panel("TP/SL Trading", tpsl_results)

    st.subheader("Strategy Comparison")
    grid_metrics = extract_metrics(grid_results) or {}
    tpsl_metrics = extract_metrics(tpsl_results) or {}

    comparison_df = pd.DataFrame({
        'Grid Trading': grid_metrics,
        'TP/SL Trading': tpsl_metrics,
    })
    st.table(comparison_df.style.format("{:.2f}"))

    if grid_metrics.get('total_return_pct', 0) > tpsl_metrics.get('total_return_pct', 0):
        st.success("🏆 Grid Trading wins!")
    else:
        st.success("🏆 TP/SL Trading wins!")

    st.subheader("Price Chart with Levels")
    df_price = data.copy()
    df_price.index = pd.to_datetime(df_price.index)
    df_price = df_price.sort_index()
    st.line_chart(df_price['close'])


def render_price_chart(result):
    price_data = _report_to_df(result.get('price_data', []))
    if price_data.empty:
        st.info('Price data not stored for this result.')
        return

    if 'index' in price_data.columns and 'close' not in price_data.columns:
        price_data = price_data.rename(columns={'index': 'time'})
    time_col = _find_column(price_data, ['time', 'timestamp', 'date', 'datetime']) or price_data.columns[0]
    close_col = _find_column(price_data, ['close', 'price', 'last']) or 'close'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(price_data[time_col], errors='coerce'),
        y=pd.to_numeric(price_data[close_col], errors='coerce'),
        mode='lines',
        name='Price',
    ))

    signals = _get_trade_signals(result)
    signal_prices = []
    for signal in signals:
        try:
            signal_prices.append(float(signal['price']))
        except Exception:
            continue
    for price in list(dict.fromkeys(signal_prices))[:MAX_SIGNAL_LEVELS]:
        fig.add_hline(y=price, line_width=1, line_dash='dot', line_color='gray')

    signal_df = pd.DataFrame(signals)
    if not signal_df.empty and 'time' in signal_df.columns and 'price' in signal_df.columns:
        signal_df['time'] = pd.to_datetime(signal_df['time'], errors='coerce')
        signal_df['price'] = pd.to_numeric(signal_df['price'], errors='coerce')
        signal_df = signal_df.dropna(subset=['time', 'price'])
        if not signal_df.empty:
            side_series = signal_df['side'].astype(str).str.lower() if 'side' in signal_df.columns else pd.Series([''] * len(signal_df))
            colors = np.where(side_series.str.contains('buy'), 'green', 'red')
            fig.add_trace(go.Scatter(
                x=signal_df['time'],
                y=signal_df['price'],
                mode='markers',
                marker=dict(size=8, color=colors),
                name='Signals',
            ))

    fig.update_layout(title=f"{str(result.get('strategy', '')).title() or 'Strategy'} Price Chart", xaxis_title='Time', yaxis_title='Price', height=500)
    st.plotly_chart(fig, use_container_width=True)


def render_detail_view(result, result_index):
    st.header("Backtest Details")
    st.caption(f"Result #{result_index + 1}")
    if st.button("← Back to list", key=f"back_to_list_{result_index}"):
        st.session_state['selected_backtest_index'] = None
        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Return", f"{result.get('total_return_pct', 0):.2f}%")
        st.metric("Sharpe Ratio", f"{result.get('sharpe_ratio', 0):.2f}" if result.get('sharpe_ratio') is not None else "N/A")
    with col2:
        st.metric("Max Drawdown", f"{result.get('max_drawdown_pct', 0):.2f}%")
        pf = result.get('profit_factor')
        st.metric("Profit Factor", f"{pf:.2f}" if isinstance(pf, (int, float)) and np.isfinite(pf) else "N/A")
    with col3:
        st.metric("Initial Balance", f"{result.get('initial_balance', 0):.4f}")
        st.metric("Final Balance", f"{result.get('final_balance', 0):.4f}")

    if result.get('dataset_index') is not None:
        st.info(f"Batch dataset: {result['dataset_index']}")

    st.subheader("Price Chart")
    render_price_chart(result)

    st.subheader("Balance Chart")
    balance_series = result.get('balance_series', {})
    if balance_series:
        df_balance = pd.DataFrame.from_dict(balance_series, orient='index', columns=['Balance'])
        df_balance.index = pd.to_datetime(df_balance.index)
        df_balance = df_balance.sort_index()
        df_balance['Balance'] = pd.to_numeric(df_balance['Balance'], errors='coerce')
        st.plotly_chart(px.line(df_balance, y='Balance', title='Balance Over Time'), use_container_width=True)
    else:
        st.info('Balance series not stored for this result.')

    st.subheader("Trades")
    trade_df = pd.DataFrame(result.get('trade_table', []))
    if trade_df.empty:
        trade_df = _standardize_trade_table(result.get('fills_report', {}), result.get('positions_report', {}))
    if trade_df.empty:
        st.info('No trade table available.')
    else:
        st.dataframe(trade_df, use_container_width=True, hide_index=True)

    st.subheader("Summary Metrics")
    summary_cols = st.columns(4)
    summary = {
        'Total Return': f"{result.get('total_return_pct', 0):.2f}%",
        'Max Drawdown': f"{result.get('max_drawdown_pct', 0):.2f}%",
        'Sharpe Ratio': f"{result.get('sharpe_ratio', 0):.2f}" if result.get('sharpe_ratio') is not None else 'N/A',
        'Profit Factor': f"{result.get('profit_factor', 0):.2f}" if isinstance(result.get('profit_factor'), (int, float)) and np.isfinite(result.get('profit_factor')) else 'N/A',
    }
    for col, (label, value) in zip(summary_cols, summary.items()):
        col.metric(label, value)


def _select_backtest(index):
    st.session_state['selected_backtest_index'] = index


def _clear_backtest_selection():
    st.session_state['selected_backtest_index'] = None

# Run backtest button
if st.button("Run Backtest Comparison"):
    st.session_state['selected_backtest_index'] = None
    with st.spinner("Running backtests..."):
        # Retrieve data generation parameters
        data_gen = st.session_state.get('data_gen', {})
        instrument_choice = data_gen.get('instrument', 'BTCUSDT')
        timeframe = data_gen.get('timeframe', '4h')
        num_bars = data_gen.get('num_bars', 200)
        start_price = data_gen.get('start_price', 30000.0)
        volatility = data_gen.get('volatility', 0.02)
        # Define instrument
        if instrument_choice == "BTCUSDT":
            instrument = TestInstrumentProvider.btcusdt_binance()
        elif instrument_choice == "ETHUSDT":
            instrument = TestInstrumentProvider.ethusdt_binance()
        else:
            instrument = TestInstrumentProvider.adausdt_binance()  # placeholder
        
        instrument_id = instrument.id
        venue = instrument_id.venue
        
        # Map timeframe to bar spec
        timeframe_map = {
            "4h": "4-HOUR",
            "8h": "8-HOUR",
            "12h": "12-HOUR",
            "1d": "1-DAY",
        }
        bar_spec = timeframe_map.get(timeframe, "4-HOUR")
        
        # Define bar type
        bar_type = BarType.from_str(f"{instrument_id}-{bar_spec}-LAST-EXTERNAL")
        
        # Generate synthetic data
        bates_params = data_gen.get('bates_params') if data_gen.get('data_source') == 'Synthetic' else None
        batch_gen = data_gen.get('batch_gen', {'enabled': False})
        if batch_gen.get('enabled', False) and data_gen.get('data_source') == 'Synthetic':
            # Generate multiple datasets
            num_datasets = min(batch_gen.get('num_datasets', 5), MAX_BATCH_DATASETS)
            variation = batch_gen.get('variation', 0.2)
            datasets = generate_multiple_synthetic_bars(
                instrument_id=instrument_id,
                bar_spec=bar_spec,
                start_price=start_price,
                num_bars=num_bars,
                volatility=volatility,
                bates_params=bates_params,
                num_datasets=num_datasets,
                variation=variation,
            )
            st.session_state['batch_datasets'] = datasets
            batch_grid_results = []
            batch_tpsl_results = []
            batch_dataset_metrics = []
            for idx, dataset in enumerate(datasets):
                try:
                    with st.spinner(f"Running batch dataset {idx + 1}/{len(datasets)}..."):
                        grid_results = run_backtest(
                            strategy_class=GridTrading,
                            strategy_config=GridTradingConfig(
                                instrument_id=instrument_id,
                                grid_step=Price.from_str(str(grid_step)),
                                num_levels=num_levels,
                                trade_size=Quantity(grid_trade_size, precision=6),
                                max_position=Quantity(max_position, precision=6),
                                bar_type=str(bar_type),
                            ),
                            data=dataset,
                            bar_type=bar_type,
                            instrument=instrument,
                            venue=venue,
                            starting_balances=[Money(starting_usdt, USDT), Money(starting_btc, BTC)],
                        )
                        levels = [Price.from_str(str(start_price + i * level_spacing)) for i in range(-num_tpsl_levels, num_tpsl_levels + 1)]
                        tpsl_results = run_backtest(
                            strategy_class=TPSLTrading,
                            strategy_config=TPSLTradingConfig(
                                instrument_id=instrument_id,
                                bar_type=str(bar_type),
                                horizontal_levels=levels,
                                tp_pct=tp_pct,
                                sl_pct=sl_pct,
                                trade_size=Quantity(tpsl_trade_size, precision=6),
                                max_position=Quantity(max_position, precision=6),
                            ),
                            data=dataset,
                            bar_type=bar_type,
                            instrument=instrument,
                            venue=venue,
                            starting_balances=[Money(starting_usdt, USDT), Money(starting_btc, BTC)],
                        )
                except Exception as e:
                    st.error(f"Batch dataset {idx + 1} failed: {str(e)}")
                    st.exception(e)
                    grid_results = {}
                    tpsl_results = {}

                batch_grid_results.append(grid_results)
                batch_tpsl_results.append(tpsl_results)
                batch_dataset_metrics.append({
                    'dataset_index': idx + 1,
                    'grid': extract_metrics(grid_results, 'grid', user_id, include_series=True, include_reports=True, price_data=dataset),
                    'tpsl': extract_metrics(tpsl_results, 'tpsl', user_id, include_series=True, include_reports=True, price_data=dataset),
                })

            data = datasets[0]
            st.session_state['batch_grid_results'] = batch_grid_results
            st.session_state['batch_tpsl_results'] = batch_tpsl_results
            st.session_state['batch_dataset_metrics'] = batch_dataset_metrics
            st.session_state['grid_results'] = batch_grid_results[0] if batch_grid_results else {}
            st.session_state['tpsl_results'] = batch_tpsl_results[0] if batch_tpsl_results else {}
            grid_results = st.session_state['grid_results']
            tpsl_results = st.session_state['tpsl_results']
        else:
            data = generate_synthetic_bars(
                instrument_id=instrument_id,
                bar_spec=bar_spec,
                start_price=start_price,
                num_bars=num_bars,
                volatility=volatility,
                bates_params=bates_params,
            )
            st.session_state['batch_datasets'] = None
            st.session_state['batch_grid_results'] = None
            st.session_state['batch_tpsl_results'] = None
            st.session_state['batch_dataset_metrics'] = None
            grid_config = GridTradingConfig(
                instrument_id=instrument_id,
                grid_step=Price.from_str(str(grid_step)),
                num_levels=num_levels,
                trade_size=Quantity(grid_trade_size, precision=6),
                max_position=Quantity(max_position, precision=6),
                bar_type=str(bar_type),
            )
            levels = [Price.from_str(str(start_price + i * level_spacing)) for i in range(-num_tpsl_levels, num_tpsl_levels + 1)]
            tpsl_config = TPSLTradingConfig(
                instrument_id=instrument_id,
                bar_type=str(bar_type),
                horizontal_levels=levels,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                trade_size=Quantity(tpsl_trade_size, precision=6),
                max_position=Quantity(max_position, precision=6),
            )
            starting_balances = [Money(starting_usdt, USDT), Money(starting_btc, BTC)]
        
        # Run backtests with error handling
        try:
            if not (batch_gen.get('enabled', False) and data_gen.get('data_source') == 'Synthetic'):
                with st.spinner("Running backtests... This may take a moment."):
                    grid_results = run_backtest(
                        strategy_class=GridTrading,
                        strategy_config=grid_config,
                        data=data,
                        bar_type=bar_type,
                        instrument=instrument,
                        venue=venue,
                        starting_balances=starting_balances,
                    )

                    tpsl_results = run_backtest(
                        strategy_class=TPSLTrading,
                        strategy_config=tpsl_config,
                        data=data,
                        bar_type=bar_type,
                        instrument=instrument,
                        venue=venue,
                        starting_balances=starting_balances,
                    )
        except Exception as e:
            st.error(f"An error occurred during backtest: {str(e)}")
            st.exception(e)
            # Set empty results to avoid further errors
            grid_results = {}
            tpsl_results = {}
        
        # Store results in session state
        st.session_state['grid_results'] = grid_results
        st.session_state['tpsl_results'] = tpsl_results
        st.session_state['data'] = data
        st.session_state['instrument'] = instrument
        st.session_state['bar_type'] = bar_type
        st.session_state['selected_batch_dataset'] = 0
        
        # Save results with user ID
        def wrap_metrics(metrics, strategy_name):
            if not metrics:
                return None
            return {
                'user_id': user_id,
                'strategy': strategy_name,
                'timestamp': datetime.now().isoformat(),
                **metrics,
            }

        grid_metrics = wrap_metrics(extract_metrics(grid_results, include_series=True, include_reports=True, price_data=data), 'grid')
        tpsl_metrics = wrap_metrics(extract_metrics(tpsl_results, include_series=True, include_reports=True, price_data=data), 'tpsl')
        
        # Initialize all_results in session state
        if 'all_results' not in st.session_state:
            st.session_state['all_results'] = []
        
        # Save to file
        results_file = Path('backtest_results.json')
        existing = []
        if results_file.exists():
            with open(results_file, 'r') as f:
                existing = json.load(f)
        results_to_append = []
        if st.session_state.get('batch_dataset_metrics'):
            for dataset_metrics in st.session_state['batch_dataset_metrics']:
                grid_item = dataset_metrics.get('grid')
                tpsl_item = dataset_metrics.get('tpsl')
                if grid_item:
                    results_to_append.append({
                        'user_id': user_id,
                        'strategy': 'grid',
                        'timestamp': datetime.now().isoformat(),
                        'dataset_index': dataset_metrics['dataset_index'],
                        **grid_item,
                    })
                if tpsl_item:
                    results_to_append.append({
                        'user_id': user_id,
                        'strategy': 'tpsl',
                        'timestamp': datetime.now().isoformat(),
                        'dataset_index': dataset_metrics['dataset_index'],
                        **tpsl_item,
                    })
        else:
            if grid_metrics:
                results_to_append.append(grid_metrics)
            if tpsl_metrics:
                results_to_append.append(tpsl_metrics)
        st.session_state['all_results'].extend(results_to_append)
        existing.extend(results_to_append)
        with open(results_file, 'w') as f:
            json.dump(existing, f, indent=2)

# Display results if available
if 'grid_results' in st.session_state and 'tpsl_results' in st.session_state:
    st.header("Backtest Results")
    batch_grid_results = st.session_state.get('batch_grid_results')
    batch_tpsl_results = st.session_state.get('batch_tpsl_results')
    batch_datasets = st.session_state.get('batch_datasets')

    if batch_grid_results and batch_tpsl_results and batch_datasets:
        dataset_options = [f"Dataset {idx + 1}" for idx in range(len(batch_datasets))]
        selected_batch_dataset = st.selectbox(
            "Choose a dataset to view",
            options=list(range(len(batch_datasets))),
            format_func=lambda idx: dataset_options[idx],
            key="selected_batch_dataset",
        )
        render_results_view(
            batch_grid_results[selected_batch_dataset],
            batch_tpsl_results[selected_batch_dataset],
            batch_datasets[selected_batch_dataset],
            selected_label=dataset_options[selected_batch_dataset],
        )

        st.subheader("Batch Dataset Details")
        for idx, dataset in enumerate(batch_datasets):
            with st.expander(f"View Details - {dataset_options[idx]}"):
                dataset_metrics = st.session_state.get('batch_dataset_metrics', [])
                if idx < len(dataset_metrics):
                    metrics = dataset_metrics[idx]
                    detail_df = pd.DataFrame([
                        {'Strategy': 'Grid Trading', **(metrics.get('grid') or {})},
                        {'Strategy': 'TP/SL Trading', **(metrics.get('tpsl') or {})},
                    ])
                    st.dataframe(detail_df)
                st.write(f"Rows: {len(dataset)}")
                st.dataframe(dataset.head(20))
    else:
        grid_results = st.session_state['grid_results']
        tpsl_results = st.session_state['tpsl_results']
        data = st.session_state['data']
        render_results_view(grid_results, tpsl_results, data)

else:
    st.info("Adjust parameters in the sidebar and click 'Run Backtest Comparison' to see results.")

# Show all backtest results from all users
results_file = Path('backtest_results.json')
if 'selected_backtest_index' not in st.session_state:
    st.session_state['selected_backtest_index'] = None
if 'all_results' not in st.session_state:
    st.session_state['all_results'] = []

all_results = []
if results_file.exists():
    with open(results_file, 'r') as f:
        all_results = json.load(f)
    st.session_state['all_results'] = all_results
    if all_results:
        all_results = sorted(all_results, key=lambda x: x.get('timestamp', ''), reverse=True)
        selected_index = st.session_state.get('selected_backtest_index')
        if selected_index is not None and 0 <= selected_index < len(all_results):
            render_detail_view(all_results[selected_index], selected_index)
            st.stop()
        elif selected_index is not None:
            st.session_state['selected_backtest_index'] = None

st.header("All Backtest Results")
if results_file.exists() and all_results:
    for idx, result in enumerate(all_results):
        with st.expander(f"Backtest {idx+1}: {result.get('strategy', 'Unknown')} - {result.get('timestamp', '')}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**User:** {result.get('user_id', 'N/A')}")
                st.write(f"**Strategy:** {result.get('strategy', 'N/A')}")
                st.write(f"**Initial Balance:** {result.get('initial_balance', 0):.2f}")
                st.write(f"**Final Balance:** {result.get('final_balance', 0):.2f}")
                st.write(f"**Total Return:** {result.get('total_return_pct', 0):.2f}%")
                st.write(f"**Max Drawdown:** {result.get('max_drawdown_pct', 0):.2f}%")
            with col2:
                st.button("View Details", key=f"view_details_{idx}", on_click=_select_backtest, args=(idx,))
                if 'balance_series' in result:
                    total_series = result['balance_series']
                    df_balance = pd.DataFrame.from_dict(total_series, orient='index', columns=['Balance'])
                    df_balance.index = pd.to_datetime(df_balance.index)
                    df_balance = df_balance.sort_index()
                    df_balance['Balance'] = pd.to_numeric(df_balance['Balance'], errors='coerce')
                    fig = px.line(df_balance, y='Balance', title='Balance Over Time')
                    fig.update_xaxes(title_text='Time')
                    fig.update_yaxes(title_text='Balance')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Balance series not stored for this result.")
elif results_file.exists():
    st.info("No results yet. Run some backtests!")
else:
    st.info("No results file found. Run your first backtest to start tracking results.")

# Add some educational content
st.markdown("---")
st.markdown("""
### How to Play
1. **Adjust parameters** in the sidebar to configure both strategies.
2. **Run backtest** to simulate trading on historical (synthetic) data.
3. **Compare results** to see which strategy performs better.
4. **Learn** by experimenting with different settings and timeframes.

### About the Strategies
- **Grid Trading**: Places buy/sell limit orders at fixed price intervals (horizontal levels). Profits from price oscillations within the grid.
- **TP/SL Trading**: Enters a position when price crosses a horizontal level, with predefined take-profit and stop-loss levels.

### Disclaimer
This is a simulation for educational purposes only. Past performance does not guarantee future results. Trade responsibly.
""")
