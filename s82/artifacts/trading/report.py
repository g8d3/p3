#!/usr/bin/env python3
"""Generate trading_report.html from trading_log.csv. Run hourly."""
import csv, json, datetime
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = Path("/home/vuos/code/p3/s82/data")
CSV_FILE = DATA_DIR / "trading_log.csv"
SIGNALS_FILE = DATA_DIR / "live_signals.json"
OUTPUT = DATA_DIR / "trading_report.html"

def load_csv():
    rows = []
    if not CSV_FILE.exists():
        return rows
    with open(CSV_FILE) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def load_signals():
    if not SIGNALS_FILE.exists():
        return {}
    with open(SIGNALS_FILE) as f:
        return json.load(f)

def make_chart(rows):
    """Bar chart: RSI + MACDh for ETH/BTC over last 24 entries."""
    recent = rows[-24:] if len(rows) > 24 else rows
    if len(recent) < 2:
        return None
    # Deduplicate by timestamp+asset
    seen = set()
    eth_rsis, btc_rsis = [], []
    eth_macd, btc_macd = [], []
    labels = []
    for r in recent:
        key = (r.get("timestamp",""), r.get("asset",""))
        if key in seen: continue
        seen.add(key)
        ts = r.get("timestamp","")[-8:] if r.get("timestamp") else ""
        asset = r.get("asset","")
        if asset == "ETH":
            eth_rsis.append(float(r.get("rsi",0)))
            eth_macd.append(float(r.get("macd_hist",0)))
        else:
            btc_rsis.append(float(r.get("rsi",0)))
            btc_macd.append(float(r.get("macd_hist",0)))
        labels.append(ts)

    n = max(len(eth_rsis), len(btc_rsis))
    x = np.arange(n)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), facecolor="#1a1a2e")
    ax1.set_facecolor("#16213e")
    ax2.set_facecolor("#16213e")
    ax1.bar(x[:len(eth_rsis)], eth_rsis, alpha=0.8, label="ETH RSI", color="#00d4aa", width=0.4)
    ax1.bar(x[:len(btc_rsis)], btc_rsis, alpha=0.8, label="BTC RSI", color="#ff6b6b", width=0.4)
    ax1.axhline(70, color="#ff6b6b", ls="--", alpha=0.5)
    ax1.axhline(30, color="#00d4aa", ls="--", alpha=0.5)
    ax1.set_ylabel("RSI", color="white")
    ax1.legend()
    ax1.tick_params(colors="white")
    ax2.bar(x[:len(eth_macd)], eth_macd, alpha=0.8, label="ETH MACDh", color="#00d4aa", width=0.4)
    ax2.bar(x[:len(btc_macd)], btc_macd, alpha=0.8, label="BTC MACDh", color="#ff6b6b", width=0.4)
    ax2.axhline(0, color="white", lw=0.5)
    ax2.set_ylabel("MACD Hist", color="white")
    ax2.legend()
    ax2.tick_params(colors="white")
    plt.tight_layout()
    chart_path = DATA_DIR / "trading_chart.png"
    plt.savefig(chart_path, dpi=120, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    return chart_path

def generate():
    rows = load_csv()
    signals_data = load_signals()

    # --- Current signals from live_signals.json ---
    current_rows = ""
    for s in signals_data.get("signals", []):
        d = s.get("direction","?")
        color = "#00d4aa" if d == "LONG" else "#ff6b6b" if d == "SHORT" else "#ffd93d"
        current_rows += f"""<tr>
            <td>{s.get("asset","")}</td>
            <td style="color:{color};font-weight:bold">{d}</td>
            <td>{s.get("rsi","")}</td>
            <td>{s.get("macd","")}</td>
            <td>{s.get("funding","")}</td>
            <td>{s.get("ob_imbalance","")}</td>
        </tr>"""

    # --- History table (last 24h) ---
    now = datetime.datetime.now(datetime.UTC)
    cutoff = now - datetime.timedelta(hours=24)
    recent = [r for r in rows if r.get("timestamp") and _parse_ts(r["timestamp"], cutoff)]
    recent = recent[-48:]  # max 48 rows

    hist_rows = ""
    for r in recent:
        d = r.get("signal","?")
        color = "#00d4aa" if d == "LONG" else "#ff6b6b" if d == "SHORT" else "#ffd93d"
        hist_rows += f"""<tr>
            <td>{r.get("timestamp","")[-8:]}</td>
            <td>{r.get("asset","")}</td>
            <td>${r.get("price","")}</td>
            <td>{r.get("rsi","")}</td>
            <td>{r.get("macd_hist","")}</td>
            <td>{r.get("funding_rate","")}</td>
            <td>{r.get("ob_imbalance","")}</td>
            <td style="color:{color};font-weight:bold">{d}</td>
        </tr>"""

    # --- Performance indicator ---
    long_count = sum(1 for r in recent if r.get("signal") == "LONG")
    short_count = sum(1 for r in recent if r.get("signal") == "SHORT")
    neutral_count = sum(1 for r in recent if r.get("signal") == "NEUTRAL")
    total = max(long_count + short_count + neutral_count, 1)

    # --- Chart ---
    chart_file = make_chart(recent)

    chart_img = ""
    if chart_file and chart_file.exists():
        chart_img = f'<img src="trading_chart.png" alt="Chart" style="width:100%;max-width:800px;border-radius:8px;margin:20px 0">'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Trading Report</title>
<style>
  body {{ font-family:'Courier New',monospace; background:#0f0f23; color:#ccc; padding:20px; max-width:1000px; margin:auto }}
  h1,h2,h3 {{ color:#fff }}
  table {{ width:100%; border-collapse:collapse; margin:15px 0 }}
  th,td {{ padding:8px 12px; text-align:left; border-bottom:1px solid #333 }}
  th {{ background:#1a1a3e; color:#8af }}
  tr:hover {{ background:#1a1a3e }}
  .card {{ background:#16213e; border-radius:8px; padding:15px; margin:15px 0 }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:12px; font-weight:bold }}
  .badge.long {{ background:#00d4aa22; color:#00d4aa }}
  .badge.short {{ background:#ff6b6b22; color:#ff6b6b }}
  .badge.neutral {{ background:#ffd93d22; color:#ffd93d }}
  .stat {{ display:inline-block; margin:10px 20px 10px 0 }}
  .stat .num {{ font-size:28px; font-weight:bold }}
  .stat .label {{ font-size:12px; color:#888 }}
</style></head>
<body>
<h1>📊 Trading Report</h1>
<p>Updated: {datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")}</p>

<div class="card">
  <h3>Current Signals</h3>
  <table>
    <tr><th>Asset</th><th>Signal</th><th>RSI</th><th>MACDh</th><th>Funding</th><th>OB Imb</th></tr>
    {current_rows}
  </table>
</div>

<div class="card">
  <h3>Performance (24h)</h3>
  <div class="stat"><div class="num" style="color:#00d4aa">{long_count}</div><div class="label">LONG</div></div>
  <div class="stat"><div class="num" style="color:#ff6b6b">{short_count}</div><div class="label">SHORT</div></div>
  <div class="stat"><div class="num" style="color:#ffd93d">{neutral_count}</div><div class="label">NEUTRAL</div></div>
  <div class="stat"><div class="num" style="color:#8af">{total}</div><div class="label">Total Cycles</div></div>
</div>

<div class="card">
  <h3>RSI & MACD History</h3>
  {chart_img}
</div>

<div class="card">
  <h3>Last 24h History</h3>
  <table>
    <tr><th>Time</th><th>Asset</th><th>Price</th><th>RSI</th><th>MACDh</th><th>Funding</th><th>OB</th><th>Signal</th></tr>
    {hist_rows}
  </table>
</div>
</body></html>"""

    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"Report written: {OUTPUT}", flush=True)

def _parse_ts(ts, cutoff):
    try:
        t = datetime.datetime.fromisoformat(ts)
        return t > cutoff
    except:
        return False

if __name__ == "__main__":
    generate()
