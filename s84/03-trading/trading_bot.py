#!/usr/bin/env python3
"""
Hyperliquid Signal Bot — señales de volumen y liquidez vía API directa.
"""
import json, os, time, urllib.request, urllib.error
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SIGNAL_FILE = os.path.join(BASE, "signals.json")
HL_INFO = "https://api.hyperliquid.xyz/info"
SYMBOLS = ["BTC", "ETH", "SOL", "ARB"]

def info(method, params=None):
    body = {"type": method}
    if params is not None:
        body["params"] = params
    data = json.dumps(body).encode()
    req = urllib.request.Request(HL_INFO, data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
    except Exception as e:
        return 0, 0
    except Exception as e:
        return None
    if isinstance(result, list) and len(result) > 0:
        c = result[0]
        return {
            "open": float(c["o"]),
            "high": float(c["h"]),
            "low": float(c["l"]),
            "close": float(c["c"]),
            "volume": float(c["v"]),
            "timestamp": c["t"]
        }
    return None

def get_coin_names():
    body = json.dumps({"type": "meta"}).encode()
    req = urllib.request.Request(HL_INFO, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        meta = json.loads(resp.read())
        if isinstance(meta, dict) and "universe" in meta:
            return [c["name"] for c in meta["universe"]]
    except: pass
    return []

def get_l2(coin):
    """Obtiene orderbook L2 para liquidez."""
    body = json.dumps({"type": "l2Book", "coin": coin}).encode()
    req = urllib.request.Request(HL_INFO, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if isinstance(result, dict) and "levels" in result:
            levels = result["levels"]
            bids = levels[0][:3] if len(levels) > 0 else []
            asks = levels[1][:3] if len(levels) > 1 else []
            bid_liq = sum(float(b["px"]) * float(b["sz"]) for b in bids)
            ask_liq = sum(float(a["px"]) * float(a["sz"]) for a in asks)
            return bid_liq, ask_liq
    except:
        pass
    return 0, 0

def candle_snapshot(coin):
    now = int(time.time() * 1000)
    day_ago = now - 86400000
    body = json.dumps({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d", "startTime": day_ago, "endTime": now}}).encode()
    req = urllib.request.Request(HL_INFO, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if isinstance(result, list) and len(result) > 0:
            c = result[0]
            return {"open": float(c["o"]), "high": float(c["h"]), "low": float(c["l"]),
                    "close": float(c["c"]), "volume": float(c["v"]), "timestamp": c["t"]}
    except: pass
    return None

def get_avg_volume(symbol):
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE) as f:
                h = json.load(f)
                vols = [s["volume"] for s in h if s["symbol"] == symbol and s.get("volume") and s["volume"] > 0]
                if len(vols) >= 3:
                    return sum(vols[-5:]) / min(len(vols[-5:]), 5)
        except: pass
    return None

def analyze(symbol, candle, bid_liq, ask_liq):
    if not candle:
        return {"symbol": symbol, "signal": "error", "reason": "sin datos"}

    vol = candle["volume"]
    liq = min(bid_liq, ask_liq)
    avg = get_avg_volume(symbol) or vol * 0.5
    price = candle["close"]
    change = (candle["close"] - candle["open"]) / candle["open"] * 100

    reasons = []
    confidence = 0

    if avg > 0 and vol > avg * 2:
        reasons.append(f"vol {vol/avg:.1f}x")
        confidence += 2
    else:
        reasons.append(f"vol ${vol:.0f}")

    if liq >= 50000:
        reasons.append(f"liq ${liq:.0f}")
    else:
        reasons.append(f"liq baja ${liq:.0f}")
        confidence -= 1

    if abs(change) > 3:
        reasons.append(f"{change:+.1f}%")
        confidence += 1

    if confidence >= 2 and liq >= 50000:
        signal = "comprar"
    elif confidence >= 1:
        signal = "observar"
    else:
        signal = "neutral"

    return {
        "symbol": symbol,
        "signal": signal,
        "price": price,
        "confidence": confidence,
        "volume": vol,
        "liquidity": liq,
        "change_pct": round(change, 2),
        "reason": "; ".join(reasons),
        "timestamp": datetime.now().isoformat()
    }

def save(signal):
    signals = []
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE) as f:
                signals = json.load(f)
        except: pass
    signals.append(signal)
    with open(SIGNAL_FILE, "w") as f:
        json.dump(signals[-500:], f, indent=2)

def show(signal):
    s, sym = signal["signal"], signal["symbol"]
    p = f"${signal['price']}" if signal.get("price") else "-"
    r = signal.get("reason", "")
    icons = {"comprar": "🟢", "observar": "🟡", "neutral": "⚪", "error": "🔴"}
    print(f"  {icons.get(s, '⚪')} {sym} {p} | {s.upper()} | {r}")

def main():
    print(f"\n=== HL Signals — {datetime.now().strftime('%H:%M')} ===")

    coins = get_coin_names()
    mids_data = info("allMids")
    print(f"  Mercados: {len(coins)} monedas")

    for sym in SYMBOLS:
        if sym not in coins:
            print(f"  ⚪ {sym} no encontrado en Hyperliquid")
            continue
        candle = candle_snapshot(sym)
        time.sleep(0.1)
        bid, ask = get_l2(sym)
        time.sleep(0.1)
        sig = analyze(sym, candle, bid, ask)
        save(sig)
        show(sig)

    print(f"  → {SIGNAL_FILE}")

if __name__ == "__main__":
    main()
