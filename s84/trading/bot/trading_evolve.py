#!/usr/bin/env python3
"""
Evolución de Estrategias de Trading — parámetros, selección, mutación.
"""
import json, os, math, random, time
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "synthetic_data.json")
RESULTS_FILE = os.path.join(BASE, "..", "evolution", "evolution.json")

# ── 1. Generador de datos sintéticos ──

def generate_synthetic_candles(n=1000):
    """Genera velas sintéticas: tendencia + ruido + algunos spikes."""
    candles = []
    price = 50000
    t = int(time.time() * 1000) - n * 3600000

    # Tendencia general ligeramente alcista
    trend = 1.0002  # ~0.02% por vela

    for i in range(n):
        # Ruido aleatorio
        noise = random.uniform(-0.02, 0.02)
        # Ocasional spike de volumen
        vol_spike = 1.0 if random.random() > 0.95 else random.uniform(0.5, 1.5)
        # Cambio de precio
        change = price * (trend - 1 + noise)
        if random.random() > 0.98:  # 2% de saltos bruscos
            change *= random.choice([-3, 3])

        o = price
        c = price + change
        h = max(o, c) * (1 + random.uniform(0, 0.01))
        l = min(o, c) * (1 - random.uniform(0, 0.01))
        v = 100 + random.random() * 50 * vol_spike

        candles.append({
            "t": t + i * 3600000,
            "o": round(o, 2), "c": round(c, 2),
            "h": round(h, 2), "l": round(l, 2),
            "v": round(v, 2)
        })
        price = c

    return {"symbol": "SYNTH/BTC", "timeframe": "1h", "candles": candles}

# ── 2. Estrategia ──

def random_strategy(name=None):
    """Genera una estrategia con parámetros aleatorios."""
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    entry_types = ["volume_spike", "sma_cross", "rsi", "price_level"]
    exit_types = ["stop_loss_take_profit", "trailing_stop", "time_stop"]

    return {
        "name": name or f"strat-{random.randint(1000,9999)}",
        "params": {
            "timeframe": random.choice(timeframes),
            "entry_type": random.choice(entry_types),
            "exit_type": random.choice(exit_types),
            "volume_threshold": round(random.uniform(1.2, 5.0), 1),
            "sma_fast": random.choice([5, 8, 10, 15, 20]),
            "sma_slow": random.choice([30, 40, 50, 60, 100, 200]),
            "rsi_period": random.choice([7, 9, 14, 21]),
            "rsi_overbought": random.choice([65, 70, 75, 80]),
            "rsi_oversold": random.choice([20, 25, 30, 35]),
            "stop_loss_pct": round(random.uniform(0.5, 5.0), 1),
            "take_profit_pct": round(random.uniform(1.0, 10.0), 1),
            "position_size_pct": round(random.uniform(5, 50), 0),
            "max_hold_candles": random.choice([5, 10, 20, 48, 168]),
        }
    }

def mutate_strategy(s, rate=0.3):
    """Copia una estrategia y muta ~30% de sus parámetros."""
    import copy
    s2 = copy.deepcopy(s)
    s2["name"] = f"{s['name']}-mut-{random.randint(100,999)}"
    params = s2["params"]
    for key in params:
        if random.random() < rate:
            if isinstance(params[key], str):
                # Elegir otro valor del mismo conjunto
                if key == "timeframe":
                    params[key] = random.choice(["1m","5m","15m","1h","4h","1d"])
                elif key == "entry_type":
                    params[key] = random.choice(["volume_spike","sma_cross","rsi","price_level"])
                elif key == "exit_type":
                    params[key] = random.choice(["stop_loss_take_profit","trailing_stop","time_stop"])
            elif isinstance(params[key], (int, float)):
                # Mutar entre 0.8x y 1.2x
                factor = random.uniform(0.8, 1.2)
                val = params[key] * factor
                params[key] = round(val, 1) if isinstance(params[key], float) else int(round(val))
                # Asegurar rangos mínimos
                if key == "stop_loss_pct":
                    params[key] = max(0.5, params[key])
                if key == "take_profit_pct":
                    params[key] = max(1.0, params[key])
                if "sma_fast" in key and params[key] < 3:
                    params[key] = 3
                if "sma_slow" in key and params[key] <= params.get("sma_fast", 0):
                    params[key] = params["sma_fast"] + random.randint(10, 50)
    return s2

# ── 3. Evaluador ──

def test_strategy(strategy, data):
    """Ejecuta una estrategia contra datos sintéticos.
    Devuelve métricas de rendimiento."""
    p = strategy["params"]
    candles = data["candles"]
    capital = 10000
    position = 0  # 0 = out, 1 = in
    entry_price = 0
    entry_bar = 0
    trades = []
    win = 0
    loss = 0

    for i in range(max(p["sma_slow"] if p["entry_type"] == "sma_cross" else 1, 1), len(candles)):
        c = candles[i]

        # Media móvil
        if p["entry_type"] == "sma_cross":
            if i < p["sma_slow"]: continue
            fast = sum(candles[j]["c"] for j in range(i-p["sma_fast"], i)) / p["sma_fast"]
            slow = sum(candles[j]["c"] for j in range(i-p["sma_slow"], i)) / p["sma_slow"]
            prev_fast = sum(candles[j]["c"] for j in range(i-p["sma_fast"]-1, i-1)) / p["sma_fast"]
            prev_slow = sum(candles[j]["c"] for j in range(i-p["sma_slow"]-1, i-1)) / p["sma_slow"]

        # Entry
        if position == 0:
            should_enter = False
            if p["entry_type"] == "volume_spike":
                avg_vol = sum(candles[j]["v"] for j in range(max(0, i-20), i)) / min(20, i)
                if avg_vol > 0 and c["v"] > avg_vol * p["volume_threshold"]:
                    should_enter = True
            elif p["entry_type"] == "sma_cross":
                if prev_fast <= prev_slow and fast > slow:
                    should_enter = True
            elif p["entry_type"] == "price_level":
                # Entra si precio rompe nivel máximo de últimas 20 velas
                max_20 = max(candles[j]["h"] for j in range(max(0, i-20), i))
                if c["c"] > max_20:
                    should_enter = True

            if should_enter:
                position = 1
                entry_price = c["c"]
                entry_bar = i
                size = capital * p["position_size_pct"] / 100

        # Exit
        elif position == 1:
            bars_held = i - entry_bar
            change_pct = (c["c"] - entry_price) / entry_price * 100
            should_exit = False
            exit_reason = ""

            if p["exit_type"] == "stop_loss_take_profit":
                if change_pct <= -p["stop_loss_pct"]:
                    should_exit = True
                    exit_reason = "stop_loss"
                elif change_pct >= p["take_profit_pct"]:
                    should_exit = True
                    exit_reason = "take_profit"
            elif p["exit_type"] == "trailing_stop":
                max_change = max((candles[j]["h"] - entry_price) / entry_price * 100
                               for j in range(entry_bar, i+1))
                if max_change - abs(change_pct) >= p["stop_loss_pct"] * 1.5:
                    should_exit = True
                    exit_reason = "trailing"
            elif p["exit_type"] == "time_stop":
                if bars_held >= p["max_hold_candles"]:
                    should_exit = True
                    exit_reason = "timeout"

            if should_exit:
                pnl = (c["c"] - entry_price) / entry_price * 100
                trades.append({"entry": entry_price, "exit": c["c"],
                               "pnl_pct": round(pnl, 2), "reason": exit_reason,
                               "bars": bars_held})
                if pnl > 0: win += 1
                else: loss += 1
                position = 0

    # Métricas
    total_trades = len(trades)
    win_rate = win / total_trades * 100 if total_trades > 0 else 0
    avg_pnl = sum(t["pnl_pct"] for t in trades) / total_trades if total_trades > 0 else 0
    profit_factor = (sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0) /
                     abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] < 0))
                     if any(t["pnl_pct"] < 0 for t in trades) else float('inf'))

    return {
        "strategy": strategy["name"],
        "params": strategy["params"],
        "metrics": {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999,
            "wins": win,
            "losses": loss
        }
    }

# ── 4. Engine evolutivo ──

def evolve(generations=10, pop_size=20, keep_ratio=0.3):
    """Loop evolutivo: genera población, prueba, selecciona, muta."""
    print(f"\n=== Evolución de Estrategias ===")
    print(f"Población: {pop_size} | Generaciones: {generations} | Keep: {keep_ratio:.0%}\n")

    # Generar datos sintéticos
    data = generate_synthetic_candles(2000)
    print(f"Datos: {len(data['candles'])} velas {data['timeframe']}\n")

    # Población inicial
    population = [random_strategy(f"gen0-{i}") for i in range(pop_size)]

    history = []

    for gen in range(generations):
        print(f"\n── Generación {gen+1}/{generations} ──")

        # Evaluar todas
        results = [test_strategy(s, data) for s in population]

        # Ordenar por profit_factor
        results.sort(key=lambda r: (r["metrics"]["profit_factor"], r["metrics"]["win_rate"]), reverse=True)

        best = results[0]
        print(f"  Mejor: {best['strategy']} → PF {best['metrics']['profit_factor']} WR {best['metrics']['win_rate']}% "
              f"({best['metrics']['wins']}W/{best['metrics']['losses']}L)")

        history.append({
            "generation": gen+1,
            "best": best["strategy"],
            "best_pf": best["metrics"]["profit_factor"],
            "best_wr": best["metrics"]["win_rate"],
            "population": len(results)
        })

        # Seleccionar mejores
        keep = max(1, int(pop_size * keep_ratio))
        survivors = [s for s in population if s["name"] in {r["strategy"] for r in results[:keep]}]

        # Clonar y mutar
        new_pop = []
        while len(new_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate_strategy(parent)
            child["name"] = f"gen{gen+1}-{len(new_pop)}"
            new_pop.append(child)

        population = survivors + new_pop[:pop_size - len(survivors)]

    # Resultado final
    final_results = [test_strategy(s, data) for s in population]
    final_results.sort(key=lambda r: (r["metrics"]["profit_factor"], r["metrics"]["win_rate"]), reverse=True)

    print(f"\n{'='*50}")
    print(f"RESULTADOS FINALES")
    print(f"{'='*50}")
    for i, r in enumerate(final_results[:5]):
        print(f"  {i+1}. {r['strategy']} | PF {r['metrics']['profit_factor']} | "
              f"WR {r['metrics']['win_rate']}% | {r['metrics']['wins']}W/{r['metrics']['losses']}L | "
              f"{r['metrics']['total_trades']} trades")

    with open(RESULTS_FILE, "w") as f:
        json.dump({"history": history, "top5": final_results[:5]}, f, indent=2)
    print(f"\nResultados guardados en {RESULTS_FILE}")

if __name__ == "__main__":
    evolve(generations=15, pop_size=30, keep_ratio=0.25)
