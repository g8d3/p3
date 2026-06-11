#!/usr/bin/env python3
"""Continuous trading signal runner. Loops every 5 min, never stops.
Signals: RSI(14), MACD, funding rate regime, orderbook imbalance.
Tracks IC (Information Coefficient) and IC decay per signal.
Assets: ETH, BTC, SOL, HYPE (extensible)."""
import json, urllib.request, time, os, sys, datetime, csv
import numpy as np
from pathlib import Path
from scipy import stats

URL = "https://api.hyperliquid.xyz/info"
BUS_DIR = "/tmp/agent-bus/worker-2/in"
DATA_DIR = Path("/home/vuos/code/p3/s82/data")
ART_DIR = Path("/home/vuos/code/p3/s82/artifacts/trading")
WEB_DIR = Path("/home/vuos/code/p3/s82/web")
CSV_FILE = DATA_DIR / "trading_log.csv"
SIGNALS_FILE = DATA_DIR / "live_signals.json"
IC_FILE = DATA_DIR / "ic_stats.json"
TRADING_MD = Path("/home/vuos/code/p3/s82/progress/TRADING.md")
INTERVAL = 300
REPORT_INTERVAL = 6
ALERT_THRESHOLD = 0.0001

cycle_count = 0
# IC tracking: persists pairs across cycles (and to file for survival across restarts)
IC_PAIRS_FILE = DATA_DIR / "ic_pairs.json"
prev_prices = {}
prev_signals = {}
ic_pair_buffer: dict = {}  # {coin: [{"sig": val, "ret": ret}, ...]}

def load_ic_pairs():
    global ic_pair_buffer
    if IC_PAIRS_FILE.exists():
        try:
            with open(IC_PAIRS_FILE) as f: ic_pair_buffer = json.load(f)
        except: ic_pair_buffer = {}
    for k in list(ic_pair_buffer.keys()):
        if not isinstance(ic_pair_buffer[k], list):
            ic_pair_buffer[k] = []

def save_ic_pairs():
    with open(IC_PAIRS_FILE, "w") as f:
        json.dump(ic_pair_buffer, f, indent=2)

load_ic_pairs()

def hl_post(data):
    b = json.dumps(data).encode()
    r = urllib.request.Request(URL, data=b, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=15).read())

def calc_rsi(p, n=14):
    d = np.diff(p); g = np.where(d > 0, d, 0); l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-n:]) if len(g) >= n else np.mean(g)
    al = np.mean(l[-n:]) if len(l) >= n else np.mean(l)
    if al == 0: return 100.0
    return 100 - (100 / (1 + ag / al))

def calc_macd(p):
    import pandas as pd
    s = pd.Series(p)
    m = s.ewm(span=12).mean() - s.ewm(span=26).mean()
    h = m - m.ewm(span=9).mean()
    return float(m.iloc[-1]), float(h.iloc[-1])

def compute_ic(pairs):
    """Compute Information Coefficient: Spearman rank correlation between signal values and forward returns.
    pairs: list of (signal_value, forward_return) tuples."""
    if len(pairs) < 10: return 0.0
    vals = np.array([p[0] for p in pairs])
    rets = np.array([p[1] for p in pairs])
    if np.std(vals) < 1e-10 or np.std(rets) < 1e-10: return 0.0
    return float(stats.spearmanr(vals, rets)[0])

def compute_ic_decay(pairs, window=10):
    """IC decay: correlation of signal with returns, computed over sliding windows.
    Returns list of IC values per window (older → newer)."""
    if len(pairs) < window + 5: return []
    ics = []
    for i in range(len(pairs) - window):
        chunk = pairs[i:i+window]
        ic = compute_ic(chunk)
        if not np.isnan(ic): ics.append(ic)
    return ics

COINS = ["ETH", "BTC", "SOL", "HYPE"]

def run_cycle():
    global cycle_count, prev_prices, prev_signals
    now = int(time.time())
    now_dt = datetime.datetime.now(datetime.UTC)

    # --- Fetch market data ---
    raw = hl_post({"type": "metaAndAssetCtxs"})
    meta, ctx = raw[0]["universe"], raw[1]
    prices = {}
    for i, a in enumerate(meta):
        mp = ctx[i].get("markPx")
        if mp: prices[a["name"]] = float(mp)

    # --- Orderbook data ---
    ob_data = {}
    for coin in COINS:
        try:
            book = hl_post({"type": "l2Book", "coin": coin})
            bids = book["levels"][0]; asks = book["levels"][1]
            ob_data[coin] = (sum(float(b["sz"]) for b in bids), sum(float(a["sz"]) for a in asks))
        except:
            ob_data[coin] = (0, 0)

    # --- Compute signals ---
    siglist = []
    for coin in COINS:
        try:
            candles = hl_post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": now * 1000 - 200 * 3600 * 1000, "endTime": now * 1000}})
            if not isinstance(candles, list) or len(candles) < 20:
                continue
            close = np.array([float(x["c"]) for x in candles])
            rsi = calc_rsi(close)
            macd_v, macd_h = calc_macd(close)
            # Direction
            d = "LONG" if rsi < 40 and macd_h > 0 else ("SHORT" if rsi > 60 and macd_h < 0 else "NEUTRAL")
            # Funding + OI
            fr = 0; oi = 0
            for i, a in enumerate(meta):
                if a["name"] == coin:
                    fr = float(ctx[i].get("fundingRate", 0))
                    oi = float(ctx[i].get("openInterest", 0))
                    break
            # Orderbook
            bv, av = ob_data.get(coin, (0,0))
            imb = (bv - av) / (bv + av + 1e-10)
            # Normalized RSI as signal value [-1, 1] for IC tracking
            signal_val = (rsi - 50) / 50  # -1 (oversold) to +1 (overbought)
            siglist.append({"coin": coin, "price": round(close[-1], 2), "close": close[-1],
                            "rsi": round(rsi, 1), "macd": round(macd_v, 2), "macd_hist": round(macd_h, 2),
                            "funding_rate": f"{fr*100:.5f}%", "funding_raw": fr,
                            "open_interest": round(oi, 0), "ob_imb": round(imb, 4),
                            "direction": d, "signal_val": signal_val})
        except Exception as e:
            print(f"[{coin}] error: {e}", flush=True)

    if not siglist:
        return

    # --- IC tracking (persistent) ---
    for s in siglist:
        coin = s["coin"]
        curr_price = s["close"]
        signal_val = s["signal_val"]
        if coin in prev_prices and coin in prev_signals:
            fwd_ret = (curr_price - prev_prices[coin]) / prev_prices[coin]
            prev_sig = prev_signals[coin]
            if coin not in ic_pair_buffer:
                ic_pair_buffer[coin] = []
            ic_pair_buffer[coin].append({"sig": prev_sig, "ret": fwd_ret})
        prev_prices[coin] = curr_price
        prev_signals[coin] = signal_val

    # Compute IC from accumulated buffer
    ic_summary = {}
    for coin, pairs in ic_pair_buffer.items():
        pair_list = [(p["sig"], p["ret"]) for p in pairs]
        ic = compute_ic(pair_list)
        decay = compute_ic_decay(pair_list)
        ic_summary[coin] = {
            "ic": round(ic, 4),
            "n": len(pair_list),
            "ic_decay": round(decay[-1] - decay[0], 4) if len(decay) > 5 else 0,
            "ic_trend": "improving" if len(decay) > 5 and decay[-1] > decay[0] else "decaying" if len(decay) > 5 else "insufficient"
        }

    save_ic_pairs()
    with open(IC_FILE, "w") as f:
        json.dump(ic_summary, f, indent=2)

    # --- CSV append (extended) ---
    btc_price = prices.get("BTC", 0)
    is_new = not CSV_FILE.exists()
    cols = ["timestamp", "asset", "price", "rsi", "macd_hist", "funding_rate",
            "ob_imbalance", "signal", "btc_price", "ic", "ic_decay"]
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(cols)
        for s in siglist:
            coin = s["coin"]
            ic_v = ic_summary.get(coin, {}).get("ic", "")
            ic_d = ic_summary.get(coin, {}).get("ic_decay", "")
            w.writerow([now_dt.isoformat(), s["coin"], s["price"], s["rsi"],
                        s["macd_hist"], s["funding_rate"], s["ob_imb"],
                        s["direction"], btc_price, ic_v, ic_d])

    # --- JSON signals file ---
    desc = lambda d: {"LONG": "RSI bajo + MACD alcista",
                      "SHORT": "RSI alto + MACD bajista",
                      "NEUTRAL": "Señales mixtas, mercado lateral"}[d]
    dp = {"signals": [{"asset": s["coin"], "direction": s["direction"],
                       "rsi": str(s["rsi"]), "macd": str(s["macd_hist"]),
                       "funding": s["funding_rate"], "ob_imbalance": s["ob_imb"],
                       "signal": desc(s["direction"])} for s in siglist],
          "ic": {k: {"ic": v["ic"], "trend": v["ic_trend"]} for k, v in ic_summary.items()},
          "status": "live", "updated": now_dt.isoformat()}
    with open(SIGNALS_FILE, "w") as f:
        json.dump(dp, f, indent=2)

    # --- Bus notification ---
    os.makedirs(BUS_DIR, exist_ok=True)
    for s in siglist:
        fname = f"signal-{now}--{os.getpid()}"
        with open(f"{BUS_DIR}/{fname}", "w") as f:
            json.dump({"type": "market_signals", "signals": [s], "ts": now}, f)
    with open(f"{BUS_DIR}/trading-update", "w") as f:
        dire = " ".join(f"{s['coin']}={s['direction']}" for s in siglist)
        f.write(f"señal actualizada: {dire}")

    # --- Report ---
    if cycle_count % REPORT_INTERVAL == 0:
        try:
            sys.path.insert(0, str(WEB_DIR))
            from trading_report import generate
            generate()
        except Exception as e:
            print(f"  Report error: {e}", flush=True)

    # --- Alerts ---
    try:
        for s in siglist:
            alerts = []
            if s["rsi"] > 70:
                alerts.append(f"RSI extremo: {s['coin']} RSI={s['rsi']}")
            elif s["rsi"] < 30:
                alerts.append(f"RSI extremo: {s['coin']} RSI={s['rsi']}")
            if s["funding_raw"] > ALERT_THRESHOLD:
                alerts.append(f"Funding alto: {s['coin']} FR={s['funding_rate']}")
            elif s["funding_raw"] < -ALERT_THRESHOLD:
                alerts.append(f"Funding negativo: {s['coin']} FR={s['funding_rate']}")
            if alerts:
                fname = f"alert-{now}--{s['coin']}"
                with open(f"{BUS_DIR}/{fname}", "w") as f:
                    json.dump({"type": "video_alert", "coin": s["coin"],
                               "reason": " | ".join(alerts), "ts": now}, f)
    except Exception as e:
        print(f"  Alert error: {e}", flush=True)

    # --- Print ---
    dir_str = " ".join(f"{s['coin']}={s['direction']} RSI={s['rsi']}" for s in siglist)
    ic_str = " ".join(f"{k}:IC={v['ic']:.3f}" for k, v in ic_summary.items())
    print(f"[{now_dt.isoformat()}] {dir_str} | {ic_str}", flush=True)

    cycle_count += 1

# --- Main loop ---
os.makedirs(BUS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
print(f"Runner v4 started (IC tracking + {len(COINS)} assets). PID={os.getpid()}", flush=True)

while True:
    try:
        run_cycle()
    except Exception as e:
        import traceback
        print(f"[FATAL] {e}", flush=True)
        traceback.print_exc()
    time.sleep(INTERVAL)
