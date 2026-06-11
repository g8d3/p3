#!/usr/bin/env python3
"""Genera trading_report.html desde trading_log.csv con gráfico y alertas."""
import csv, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).parent.parent
CSV = BASE / "data" / "trading_log.csv"
SIGNALS = BASE / "data" / "live_signals.json"
IC_STATS = BASE / "data" / "ic_stats.json"
HTML = BASE / "data" / "trading_report.html"

def load_csv():
    if not CSV.exists(): return []
    with open(CSV) as f:
        return list(csv.DictReader(f))

def make_chart(rows):
    recent = rows[-48:] if len(rows) > 48 else rows
    if len(recent) < 4: return None
    seen = set()
    eth_r, btc_r, eth_m, btc_m, lbls = [], [], [], [], []
    for r in recent:
        k = (r.get("timestamp",""), r.get("asset",""))
        if k in seen: continue
        seen.add(k)
        ts = r.get("timestamp","")[-8:]
        a = r.get("asset","")
        try:
            if a == "ETH":
                eth_r.append(float(r.get("rsi",50)))
                eth_m.append(float(r.get("macd_hist",0)))
            else:
                btc_r.append(float(r.get("rsi",50)))
                btc_m.append(float(r.get("macd_hist",0)))
        except: pass
        lbls.append(ts)
    n = max(len(eth_r), len(btc_r))
    x = np.arange(n)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10,5.5), facecolor="#0d1117")
    for ax in (a1, a2): ax.set_facecolor("#161b22"); ax.tick_params(colors="#8b949e")
    a1.bar(x[:len(eth_r)], eth_r, alpha=0.8, label="ETH RSI", color="#3fb950", width=0.35)
    a1.bar(x[:len(btc_r)], btc_r, alpha=0.8, label="BTC RSI", color="#f85149", width=0.35)
    a1.axhline(70, color="#f85149", ls="--", alpha=0.4)
    a1.axhline(30, color="#3fb950", ls="--", alpha=0.4)
    a1.set_ylabel("RSI", color="#8b949e"); a1.legend()
    a2.bar(x[:len(eth_m)], eth_m, alpha=0.8, label="ETH MACDh", color="#3fb950", width=0.35)
    a2.bar(x[:len(btc_m)], btc_m, alpha=0.8, label="BTC MACDh", color="#f85149", width=0.35)
    a2.axhline(0, color="white", lw=0.4); a2.set_ylabel("MACD Hist", color="#8b949e"); a2.legend()
    plt.tight_layout()
    p = BASE / "data" / "trading_chart.png"
    plt.savefig(p, dpi=110, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    return p

def generate():
    rows = load_csv()
    sig_data = {}
    if SIGNALS.exists():
        with open(SIGNALS) as f: sig_data = json.load(f)
    ic_data = {}
    if IC_STATS.exists():
        with open(IC_STATS) as f: ic_data = json.load(f)
    now = datetime.now(timezone.utc)
    signals = sig_data.get("signals", [])

    # Current signals table
    cur_rows = ""
    for s in signals:
        d = s.get("direction","?")
        cls = "long" if d=="LONG" else "short" if d=="SHORT" else "neutral"
        cur_rows += f"<tr><td>{s.get('asset','')}</td><td><span class='signal {cls}'>{d}</span></td><td>{s.get('rsi','')}</td><td>{s.get('macd','')}</td><td>{s.get('funding','')}</td><td>{s.get('ob_imbalance','')}</td></tr>\n"

    # Last 24h history
    cutoff = now - timedelta(hours=24)
    recent_24h = [r for r in rows if r.get("timestamp") and _parse_ts(r["timestamp"]) > cutoff][-48:]
    hist_rows = ""
    for r in recent_24h:
        d = r.get("signal","?").upper()
        cls = "long" if "LONG" in d else "short" if "SHORT" in d else "neutral"
        ts = r.get("timestamp","")
        if len(ts) > 8: ts = ts[-8:]
        hist_rows += f"<tr><td>{ts}</td><td>{r.get('asset','')}</td><td>${r.get('price','')}</td><td>{r.get('rsi','')}</td><td>{r.get('macd_hist','')}</td><td>{r.get('funding_rate','')}</td><td><span class='signal {cls}'>{d[:5]}</span></td></tr>\n"

    # Performance stats
    lc = sum(1 for r in rows if r.get("signal","").upper() == "LONG")
    sc = sum(1 for r in rows if r.get("signal","").upper() == "SHORT")
    nc = sum(1 for r in rows if r.get("signal","").upper() == "NEUTRAL")
    # Alerts: count RSI extremes
    rsi_extremes = sum(1 for r in rows if r.get("rsi") and (float(r["rsi"]) > 70 or float(r["rsi"]) < 30))

    # Chart
    chart = make_chart(rows)
    img = f'<img src="trading_chart.png" style="width:100%;max-width:800px;border-radius:6px;margin-top:10px">' if chart and chart.exists() else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trading Report</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,monospace; background:#0d1117; color:#c9d1d9; padding:20px; }}
h1 {{ color:#58a6ff; font-size:20px; margin-bottom:16px; }}
h2 {{ color:#8b949e; font-size:14px; text-transform:uppercase; letter-spacing:1px; margin:20px 0 8px; }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; margin-bottom:12px; }}
.signal {{ display:inline-block; padding:2px 10px; border-radius:10px; font-size:12px; font-weight:bold; }}
.long {{ background:#1b4a1b; color:#3fb950; }}
.short {{ background:#4a1b1b; color:#f85149; }}
.neutral {{ background:#4a3b1b; color:#d29922; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
th {{ text-align:left; color:#8b949e; padding:8px 4px; border-bottom:1px solid #30363d; }}
td {{ padding:6px 4px; border-bottom:1px solid #21262d; }}
.stat {{ display:inline-block; margin:8px 24px 8px 0; }}
.stat .n {{ font-size:26px; font-weight:bold; }}
.stat .l {{ font-size:11px; color:#484f58; }}
.alert {{ display:inline-block; padding:3px 10px; border-radius:10px; font-size:11px; background:#4a1b1b; color:#f85149; margin:2px; }}
.meta {{ color:#484f58; font-size:11px; margin-top:16px; }}
a {{ color:#58a6ff; }}
</style></head>
<body>
<h1>📊 Trading Report</h1>
<p style="color:#8b949e;margin-bottom:16px">{now.strftime("%Y-%m-%d %H:%M UTC")} · {len(rows)} registros</p>

<div class="card">
  <h2>Señales Actuales</h2>
  <table><tr><th>Asset</th><th>Dirección</th><th>RSI</th><th>MACDh</th><th>Funding</th><th>OB Imb</th></tr>
  {cur_rows}</table>
</div>

<div class="card">
  <h2>Performance</h2>
  <div class="stat"><div class="n" style="color:#3fb950">{lc}</div><div class="l">LONG</div></div>
  <div class="stat"><div class="n" style="color:#f85149">{sc}</div><div class="l">SHORT</div></div>
  <div class="stat"><div class="n" style="color:#d29922">{nc}</div><div class="l">NEUTRAL</div></div>
  <div class="stat"><div class="n" style="color:#58a6ff">{len(rows)}</div><div class="l">Total Cycles</div></div>
  <div class="stat"><div class="n" style="color:#f85149">{rsi_extremes}</div><div class="l">Alertas RSI</div></div>
</div>

<div class="card">
  <h2>Information Coefficient (IC)</h2>
  <table><tr><th>Asset</th><th>IC</th><th>Samples</th><th>Trend</th></tr>
  {''.join(f'<tr><td>{k}</td><td style="color:#3fb950" if v.get("ic",0)>0 else "#f85149">{v.get("ic","?")}</td><td>{v.get("n",0)}</td><td>{v.get("ic_trend","?")}</td></tr>' for k, v in sorted(ic_data.items())) if ic_data else '<tr><td colspan=4 style="color:#484f58">Acumulando datos (necesita ≥10 ciclos)</td></tr>'}
  </table>
  <p style="color:#484f58;font-size:11px;margin-top:8px">IC = Spearman rank correlation between signal and forward return. IC > 0 = predictivo.</p>
</div>

<div class="card">
  <h2>RSI & MACD History</h2>
  {img}
</div>

<div class="card">
  <h2>Últimas 24h</h2>
  <div style="max-height:400px;overflow-y:auto">
  <table><tr><th>Time</th><th>Asset</th><th>Price</th><th>RSI</th><th>MACDh</th><th>Funding</th><th>Signal</th></tr>
  {hist_rows}</table>
  </div>
</div>

<div class="meta">
  Generado automáticamente ·
  <a href="/p3/s82/data/trading_log.csv">CSV</a> ·
  <a href="/p3/s82/progress/TRADING.md">Progreso</a>
</div>
</body></html>"""
    HTML.write_text(html)
    print(f"Report: {HTML} ({len(rows)} rows)", flush=True)

def _parse_ts(ts):
    try: return datetime.fromisoformat(ts)
    except: return datetime.min.replace(tzinfo=timezone.utc)

if __name__ == "__main__":
    generate()
