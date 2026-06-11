#!/usr/bin/env python3
"""Live Signal Generator — HyperLiquid ETH/BTC. Writes to bus + dashboard."""
import json, urllib.request, time, os, sys, datetime
import numpy as np

URL = "https://api.hyperliquid.xyz/info"
BUS_DIR = "/tmp/agent-bus/worker-2/in"
DATA_FILE = "/home/vuos/code/p3/s82/data/live_signals.json"

def hl_post(data):
    b = json.dumps(data).encode()
    r = urllib.request.Request(URL, data=b, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=10).read())

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

def direction(rsi, mh):
    if rsi < 40 and mh > 0: return "LONG"
    if rsi > 60 and mh < 0: return "SHORT"
    return "NEUTRAL"

def compute(coin, ctx, meta):
    now = int(time.time() * 1000)
    c = hl_post({"type":"candleSnapshot","req":{"coin":coin,"interval":"1h","startTime":now-200*3600*1000,"endTime":now}})
    if not isinstance(c, list) or len(c) < 20: return None
    close = np.array([float(x["c"]) for x in c])
    rsi = calc_rsi(close)
    macd_v, macd_h = calc_macd(close)
    for i, a in enumerate(meta):
        if a["name"] == coin:
            fr = float(ctx[i].get("fundingRate", 0))
            oi = float(ctx[i].get("openInterest", 0))
            break
    else:
        fr, oi = 0, 0
    d = direction(rsi, macd_h)
    return {"coin":coin,"price":round(close[-1],2),"rsi":round(rsi,1),
            "macd":round(macd_v,2),"macd_hist":round(macd_h,2),
            "funding_rate":f"{fr*100:.5f}%","open_interest":round(oi,0),
            "direction":d}

os.makedirs(BUS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

raw = hl_post({"type":"metaAndAssetCtxs"})
meta, ctx = raw[0]["universe"], raw[1]

siglist = []
for coin in ["ETH","BTC"]:
    s = compute(coin, ctx, meta)
    if s:
        siglist.append(s)
        print(f"[{s['coin']}] ${s['price']} RSI={s['rsi']} MACDh={s['macd_hist']:+.2f} FR={s['funding_rate']} OI={s['open_interest']:>9,.0f} → {s['direction']}")

if not siglist:
    print("ERROR: no signals"); sys.exit(1)

# Bus (worker-2)
ts = int(time.time())
fname = f"signal-{ts}--{os.getpid()}"
with open(f"{BUS_DIR}/{fname}", "w") as f:
    json.dump({"type":"market_signals","signals":siglist,"ts":ts}, f)

# Dashboard
desc = lambda d: {"LONG":"RSI bajo + MACD alcista — entrada LONG",
                  "SHORT":"RSI alto + MACD bajista — entrada SHORT",
                  "NEUTRAL":"Señales mixtas, mercado lateral"}[d]
dp = {"signals":[{"asset":s["coin"],"direction":s["direction"],
                  "rsi":str(s["rsi"]),"macd":str(s["macd_hist"]),
                  "signal":desc(s["direction"])} for s in siglist],
      "status":"live",
      "updated":datetime.datetime.now(datetime.UTC).isoformat()}
with open(DATA_FILE, "w") as f:
    json.dump(dp, f, indent=2)

print(f"✅ Bus: {BUS_DIR}/{fname}")
print(f"✅ Dashboard: {DATA_FILE}")
print(f"   curl -s http://localhost:9093/api/signals")
