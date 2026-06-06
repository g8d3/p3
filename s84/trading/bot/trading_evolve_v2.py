#!/usr/bin/env python3
"""
Evolución V2 — múltiples semillas, cross-pollination, datos multi-regimen.
"""
import json, os, math, random, time, copy

BASE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.join(BASE, "..", "shared-bridge", "discoveries")
RESULTS = os.path.join(BASE, "..", "evolution", "evolution-v2.json")
os.makedirs(BRIDGE, exist_ok=True)

# ── 1. DATOS SINTÉTICOS MULTI-REGIMEN ──

def generate_market(regime, n=500, start=50000):
    """Genera velas con un régimen específico."""
    candles = []
    price = start
    t = int(time.time() * 1000) - n * 3600000
    volatility = 0.01
    trend = 1.0

    if regime == "alcista": trend = 1.0005
    elif regime == "bajista": trend = 0.9995
    elif regime == "lateral": trend = 1.0; volatility = 0.005
    elif regime == "volatil": trend = 1.0; volatility = 0.03
    elif regime == "ciclico": trend = 1.0
    else: regime = "lateral"

    for i in range(n):
        if regime == "ciclico":
            trend = 1.0 + 0.001 * math.sin(i * math.pi / 125)

        noise = random.gauss(0, volatility)
        spike = 1.0 if random.random() > 0.97 else random.gauss(1, 0.3)
        change = price * (trend - 1 + noise) * spike

        o = price
        c = price + change
        h = max(o, c) * (1 + abs(random.gauss(0, volatility * 0.5)))
        l = min(o, c) * (1 - abs(random.gauss(0, volatility * 0.5)))
        v = max(1, 100 + random.gauss(0, 30) * spike)

        candles.append({"t": t + i*3600000, "o": round(o,2), "c": round(c,2),
                        "h": round(h,2), "l": round(l,2), "v": round(v,2)})
        price = c

    return {"regime": regime, "n": n, "candles": candles}

# ── 2. SEMILLAS (familias de estrategias) ──

SEEDS = {
    "sma_cross": {
        "entry_types": ["sma_cross"],
        "exit_types": ["stop_loss_take_profit", "trailing_stop"],
        "params": {"sma_fast": (3,10), "sma_slow": (10,40),
                   "stop_loss_pct": (0.5,3), "take_profit_pct": (1,6)}
    },
    "volume_spike": {
        "entry_types": ["volume_spike"],
        "exit_types": ["stop_loss_take_profit", "time_stop"],
        "params": {"volume_threshold": (1.1,3), "stop_loss_pct": (0.5,3),
                   "take_profit_pct": (1,5), "max_hold_candles": (3,24)}
    },
    "rsi": {
        "entry_types": ["rsi"],
        "exit_types": ["stop_loss_take_profit", "trailing_stop"],
        "params": {"rsi_period": (5,14), "rsi_overbought": (60,80),
                   "rsi_oversold": (20,40), "stop_loss_pct": (0.5,3),
                   "take_profit_pct": (1,5)}
    },
    "price_action": {
        "entry_types": ["price_level"],
        "exit_types": ["trailing_stop", "time_stop"],
        "params": {"stop_loss_pct": (0.5,3), "take_profit_pct": (1,5),
                   "max_hold_candles": (3,24)}
    }
}

def random_from_seed(seed_name):
    """Genera estrategia aleatoria dentro de una semilla."""
    seed = SEEDS[seed_name]
    s = {"name": f"{seed_name}-{random.randint(1000,9999)}",
         "semilla": seed_name,
         "entry_type": random.choice(seed["entry_types"]),
         "exit_type": random.choice(seed["exit_types"]),
         "params": {}}
    for k, (lo, hi) in seed["params"].items():
        if k in ("sma_fast", "sma_slow", "rsi_period", "max_hold_candles"):
            s["params"][k] = random.randint(int(lo), int(hi))
        else:
            s["params"][k] = round(random.uniform(lo, hi), 1)
    if "sma_fast" in s["params"] and "sma_slow" in s["params"]:
        if s["params"]["sma_slow"] <= s["params"]["sma_fast"]:
            s["params"]["sma_slow"] = s["params"]["sma_fast"] + random.randint(10, 50)
    return s

# ── 3. EVALUADOR ──

def evaluate(strategy, candles, capital=10000):
    p = strategy["params"]
    position = 0; entry_price = 0; entry_bar = 0; trades = []
    win = loss = 0

    for i in range(max(p.get("sma_slow", 1), 1), len(candles)):
        c = candles[i]

        # MAs for sma_cross
        sf = p.get("sma_fast", 10)
        ss = p.get("sma_slow", 50)
        fast = slow = pf = ps = 0
        if ss and i >= ss:
            fast = sum(candles[j]["c"] for j in range(i-sf, i)) / sf
            slow = sum(candles[j]["c"] for j in range(i-ss, i)) / ss
            pf = sum(candles[j]["c"] for j in range(i-sf-1, i-1)) / sf
            ps = sum(candles[j]["c"] for j in range(i-ss-1, i-1)) / ss

        # Entry
        if position == 0:
            enter = False
            et = strategy["entry_type"]
            if et == "sma_cross" and pf <= ps and fast > slow:
                enter = True
            elif et == "volume_spike":
                avg = sum(candles[j]["v"] for j in range(max(0,i-20), i)) / min(20,i)
                if avg > 0 and c["v"] > avg * p.get("volume_threshold", 2):
                    enter = True
            elif et == "rsi" and i >= p.get("rsi_period", 14):
                rp = p.get("rsi_period", 14)
                if i < rp: continue
                gains = [max(0, candles[j]["c"]-candles[j-1]["c"]) for j in range(i-rp+1, i+1)]
                losses = [max(0, candles[j-1]["c"]-candles[j]["c"]) for j in range(i-rp+1, i+1)]
                avg_g = sum(gains)/rp if gains else 0
                avg_l = sum(losses)/rp if losses else 1
                rs = avg_g/avg_l if avg_l > 0 else 999
                rsi = 100 - 100/(1+rs)
                if rsi < p.get("rsi_oversold",30): enter = True
            elif et == "price_level":
                hi20 = max(candles[j]["h"] for j in range(max(0,i-20), i))
                if c["c"] > hi20: enter = True

            if enter:
                position = 1; entry_price = c["c"]; entry_bar = i

        # Exit
        elif position == 1:
            change = (c["c"] - entry_price) / entry_price * 100
            held = i - entry_bar
            exit = False; reason = ""
            xt = strategy["exit_type"]

            if xt == "stop_loss_take_profit":
                if change <= -p["stop_loss_pct"]: exit = True; reason = "sl"
                elif change >= p["take_profit_pct"]: exit = True; reason = "tp"
            elif xt == "trailing_stop":
                best = max((candles[j]["h"]-entry_price)/entry_price*100 for j in range(entry_bar, i+1))
                if best > 3 and best - abs(change) > p.get("stop_loss_pct",2)*1.5:
                    exit = True; reason = "trail"
            elif xt == "time_stop" and held >= p.get("max_hold_candles",48):
                exit = True; reason = "time"

            if exit:
                trades.append({"entry": round(entry_price,2), "exit": round(c["c"],2),
                               "pnl": round(change,2), "reason": reason})
                if change > 0: win += 1
                else: loss += 1
                position = 0

    total = len(trades)
    wr = win/total*100 if total > 0 else 0
    avg_pnl = sum(t["pnl"] for t in trades)/total if total > 0 else 0
    gains = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    losses_sum = sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = gains/abs(losses_sum) if losses_sum != 0 else (999 if gains > 0 else 0)
    # Drawdown máximo
    peak = capital
    dd = 0
    for t in trades:
        peak = max(peak, capital * (1 + t["pnl"]/100))
        dd = max(dd, (peak - capital * (1 + t["pnl"]/100)) / peak * 100)
    drawdown = dd
    score = pf * (wr/100) * min(1, total/20) * max(0, 1 - drawdown/200)

    # Penalizar si muy pocas trades (no confiable)
    trade_penalty = min(1, total / 20)
    score = pf * (wr/100) * trade_penalty * (1 - abs(drawdown)/100) if total > 5 else 0

    return {"total_trades": total, "win_rate": round(wr,1), "avg_pnl": round(avg_pnl,2),
            "profit_factor": round(pf,2) if pf != 999 else 999,
            "score": round(score,2), "wins": win, "losses": loss}

# ── 4. MUTACIÓN Y CROSS-POLLINATION ──

def mutate(s):
    s2 = copy.deepcopy(s)
    s2["name"] = f"{s['semilla']}-mut-{random.randint(100,999)}"
    for k, v in s2["params"].items():
        if random.random() < 0.3:
            if isinstance(v, int):
                s2["params"][k] = max(1, int(v * random.uniform(0.8, 1.2)))
            else:
                s2["params"][k] = round(v * random.uniform(0.8, 1.2), 1)
    return s2

def cross_pollinate(s1, s2):
    """Combina parámetros de dos estrategias de diferentes semillas."""
    child = copy.deepcopy(s1)
    child["name"] = f"cross-{s1['semilla']}-{s2['semilla']}-{random.randint(100,999)}"
    child["semilla"] = f"{s1['semilla']}+{s2['semilla']}"
    # Tomar algunos parámetros de s2
    for k in s2["params"]:
        if random.random() < 0.4:
            child["params"][k] = s2["params"][k]
    # Puede mutar el entry_type
    if random.random() < 0.2:
        child["entry_type"] = s2["entry_type"]
    return child

# ── 5. ENGINE PRINCIPAL ──

def evolve(generations=20, pop_per_seed=10, keep=0.3):
    print(f"\n{'='*60}")
    print(f"  EVOLUCIÓN V2 — MÚLTIPLES SEMILLAS + CROSS-POLLINATION")
    print(f"{'='*60}")
    print(f"  Semillas: {', '.join(SEEDS.keys())}")
    print(f"  Población: {len(SEEDS)*pop_per_seed} ({pop_per_seed} por semilla)")
    print(f"  Generaciones: {generations}")
    print(f"{'='*60}\n")

    # Datos: entrenar en un régimen, testear en otro
    train_data = generate_market("alcista", 500)["candles"] + \
                 generate_market("volatil", 500)["candles"] + \
                 generate_market("lateral", 500)["candles"]
    test_data = generate_market("bajista", 300)["candles"] + \
                generate_market("ciclico", 300)["candles"]
    print(f"  Train: {len(train_data)} velas | Test: {len(test_data)} velas\n")

    # Población inicial: N por semilla
    population = []
    for seed_name in SEEDS:
        for _ in range(pop_per_seed):
            population.append(random_from_seed(seed_name))
    print(f"  Población inicial: {len(population)}\n")

    history = []

    for gen in range(generations):
        results = []
        for s in population:
            m = evaluate(s, train_data)
            # Validar en test
            m_test = evaluate(s, test_data)
            # Score compuesto: 70% train + 30% test
            score = m["score"] * 0.7 + m_test["score"] * 0.3
            results.append((score, m, m_test, s))

        results.sort(key=lambda x: x[0], reverse=True)
        best = results[0]
        print(f"  Gen {gen+1:2d}: mejor {best[3]['name']:30s} | "
              f"PF {best[1]['profit_factor']:>5} | WR {best[1]['win_rate']:5.1f}% | "
              f"score {best[0]:.1f}")

        history.append({"gen": gen+1, "best": best[3]["name"],
                        "pf": best[1]["profit_factor"],
                        "wr": best[1]["win_rate"],
                        "score": round(best[0], 1)})

        # Selección y reproducción
        survivors = [r[3] for r in results[:max(1, int(len(population)*keep))]]

        # La mejor estrategia de cada semilla sobrevive siempre
        for seed_name in SEEDS:
            best_in_seed = [r for r in results if r[3]["semilla"].startswith(seed_name)]
            if best_in_seed:
                survivors.append(best_in_seed[0][3])

        # Nueva generación
        # Remove duplicates by name
        seen = set()
        unique = []
        for s in survivors:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique.append(s)
        new_pop = unique
        while len(new_pop) < len(population):
            if random.random() < 0.15 and len(new_pop) > 5:
                # Cross-pollination: mezclar dos semillas diferentes
                s1 = random.choice(new_pop)
                s2 = random.choice([s for s in new_pop if s["semilla"] != s1["semilla"]] + new_pop)
                child = cross_pollinate(s1, s2)
            else:
                parent = random.choice(survivors)
                child = mutate(parent)
            new_pop.append(child)

        population = new_pop

    # Final: re-evaluar top 10 en test (datos no vistos)
    final_data = generate_market("volatil", 500)["candles"]
    final = [(evaluate(s, final_data)["score"], s) for s in population]
    final.sort(key=lambda x: x[0], reverse=True)

    print(f"\n{'='*60}")
    print(f"  TOP 5 ESTRATEGIAS (validación en datos volátiles no vistos)")
    print(f"{'='*60}")
    for i, (sc, s) in enumerate(final[:5]):
        m = evaluate(s, final_data)
        print(f"  {i+1}. {s['name']:30s} | {s['semilla']:15s} | "
              f"PF {m['profit_factor']:>5} | WR {m['win_rate']:5.1f}% | "
              f"{m['wins']}W/{m['losses']}L | score {sc:.1f}")

    # Compartir descubrimiento
    discovery = {
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "generations": generations,
        "population": len(population),
        "seeds": list(SEEDS.keys()),
        "top5": [{"name": s["name"], "seed": s["semilla"],
                   "pf": evaluate(s, final_data)["profit_factor"],
                   "wr": evaluate(s, final_data)["win_rate"]}
                 for _, s in final[:5]]
    }
    with open(RESULTS, "w") as f:
        json.dump(discovery, f, indent=2)

    # Escribir descubrimiento al puente
    bridge_file = os.path.join(BRIDGE, f"{time.strftime('%Y-%m-%d')}-evolution-v2.md")
    with open(bridge_file, "w") as f:
        f.write(f"# Evolución V2 — {discovery['date']}\n\n")
        f.write(f"Semillas: {', '.join(discovery['seeds'])}\n")
        f.write(f"Generaciones: {generations}\n\n")
        f.write("## Top 5\n\n")
        for t in discovery["top5"]:
            f.write(f"- {t['name']} | PF {t['pf']} | WR {t['wr']}%\n")
        f.write(f"\n→ Resultados completos en evolution-v2.json\n")

    print(f"\n  → Descubrimiento compartido en: {bridge_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    evolve(generations=20, pop_per_seed=8, keep=0.25)
