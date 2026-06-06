#!/usr/bin/env python3
"""
evolve.py — Evolución de estrategias de trading con múltiples semillas.

Arquitectura:
  - 4 semillas (sma_cross, volume_spike, rsi, price_action)
  - Datos sintéticos multi-régimen (alcista, bajista, lateral, volátil, cíclico)
  - Walk-forward: train en regimenes A,B → test en regimenes C
  - Selección por score compuesto (PF × WR × cobertura)
  - Mutación por tweak gaussiano de parámetros
  - Cross-pollination entre semillas diferentes
  - Descubrimientos compartidos vía shared-bridge/

Uso:  python3 evolve.py
"""

import json, os, math, random, time, copy
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.resolve()
SEMILLAS_DIR = BASE / "semillas"
RESULTADOS_DIR = BASE / "resultados"
BRIDGE_DIR = BASE.parent / "shared-bridge" / "discoveries"
SEMILLAS_DIR.mkdir(exist_ok=True)
RESULTADOS_DIR.mkdir(exist_ok=True)
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. GENERADOR DE DATOS MULTI-RÉGIMEN ──────────────────────────────

REGIMES = {
    "alcista":   {"trend": 1.0005,  "vol": 0.010, "label": "📈 Alcista"},
    "bajista":   {"trend": 0.9995,  "vol": 0.010, "label": "📉 Bajista"},
    "lateral":   {"trend": 1.0,     "vol": 0.005, "label": "➡️ Lateral"},
    "volatil":   {"trend": 1.0,     "vol": 0.030, "label": "🌪️ Volátil"},
    "ciclico":   {"trend": None,    "vol": 0.010, "label": "🔁 Cíclico"},
}


def generate_regime(regime: str, n: int = 500, start: float = 50000) -> list:
    """Genera velas 1h sintéticas para un régimen dado.
    Devuelve lista de dicts con t, o, h, l, c, v.
    """
    cfg = REGIMES[regime]
    candles = []
    price = start
    base_ts = int(time.time() * 1000) - n * 3600_000

    for i in range(n):
        # Tendencia cíclica
        if regime == "ciclico":
            trend = 1.0 + 0.002 * math.sin(i * 2 * math.pi / 250)
        else:
            trend = cfg["trend"]

        # Ruido gaussiano + spikes de volatilidad
        noise = random.gauss(0, cfg["vol"])
        spike = 1.0 if random.random() > 0.96 else random.gauss(1.0, 0.4)
        change = price * (trend - 1.0 + noise) * max(spike, 0.3)

        o, c = price, price + change
        h = max(o, c) * (1.0 + abs(random.gauss(0, cfg["vol"] * 0.5)))
        l_val = min(o, c) * (1.0 - abs(random.gauss(0, cfg["vol"] * 0.5)))
        v = max(1.0, 100.0 + random.gauss(0, 40.0) * spike)

        candles.append({
            "t": base_ts + i * 3600_000,
            "o": round(o, 2),
            "h": round(h, 2),
            "l": round(l_val, 2),
            "c": round(c, 2),
            "v": round(v, 2),
        })
        price = c

    return candles


def generate_multi_regime(
    train_regimes: list[str],
    test_regimes: list[str],
    n_per_regime: int = 2000,
) -> tuple[list, list]:
    """Genera train + test combinando múltiples regímenes."""
    train = []
    for r in train_regimes:
        train.extend(generate_regime(r, n_per_regime, start=50000))
    test = []
    for r in test_regimes:
        test.extend(generate_regime(r, n_per_regime // 2, start=52000))
    return train, test


# ── 2. SEMILLAS — familias de estrategias ────────────────────────────

SEEDS = {
    "sma_cross": {
        "entry_types": ["sma_cross"],
        "exit_types": ["stop_loss_take_profit", "trailing_stop"],
        "params": {
            "sma_fast":    {"lo": 3,   "hi": 15,   "type": int},
            "sma_slow":    {"lo": 15,  "hi": 100,  "type": int},
            "stop_loss":   {"lo": 1.5, "hi": 6.0,  "type": float},
            "take_profit": {"lo": 2.0, "hi": 10.0, "type": float},
            "max_vol":     {"lo": 0.5, "hi": 5.0,  "type": float},
        },
    },
    "volume_spike": {
        "entry_types": ["volume_spike"],
        "exit_types": ["stop_loss_take_profit", "time_stop"],
        "params": {
            "vol_threshold":  {"lo": 1.1, "hi": 2.0, "type": float},
            "stop_loss":      {"lo": 1.5, "hi": 6.0, "type": float},
            "take_profit":    {"lo": 2.0, "hi": 10.0, "type": float},
            "max_hold":       {"lo": 5,   "hi": 48,  "type": int},
            "max_vol":        {"lo": 0.5, "hi": 5.0, "type": float},
        },
    },
    "rsi": {
        "entry_types": ["rsi"],
        "exit_types": ["stop_loss_take_profit", "trailing_stop"],
        "params": {
            "rsi_period":    {"lo": 7,   "hi": 21,  "type": int},
            "rsi_ob":        {"lo": 60,  "hi": 80,  "type": int},
            "rsi_os":        {"lo": 20,  "hi": 40,  "type": int},
            "stop_loss":     {"lo": 1.5, "hi": 6.0,  "type": float},
            "take_profit":   {"lo": 2.0, "hi": 10.0, "type": float},
            "max_vol":       {"lo": 0.5, "hi": 5.0, "type": float},
        },
    },
    "price_action": {
        "entry_types": ["price_level"],
        "exit_types": ["trailing_stop", "time_stop"],
        "params": {
            "pa_lookback":   {"lo": 5,   "hi": 20,  "type": int},
            "stop_loss":     {"lo": 1.5, "hi": 6.0, "type": float},
            "take_profit":   {"lo": 2.0, "hi": 10.0, "type": float},
            "max_hold":      {"lo": 5,   "hi": 48,  "type": int},
            "max_vol":       {"lo": 0.5, "hi": 5.0, "type": float},
        },
    },
}


def spawn(seed_name: str) -> dict:
    """Genera un individuo aleatorio dentro de una semilla."""
    seed = SEEDS[seed_name]
    ind = {
        "name": f"{seed_name}-{random.randint(1000, 9999)}",
        "semilla": seed_name,
        "entry_type": random.choice(seed["entry_types"]),
        "exit_type": random.choice(seed["exit_types"]),
        "params": {},
    }
    for k, spec in seed["params"].items():
        if spec["type"] == int:
            ind["params"][k] = random.randint(spec["lo"], spec["hi"])
        else:
            ind["params"][k] = round(random.uniform(spec["lo"], spec["hi"]), 1)

    # Sanidad: sma_slow > sma_fast
    if "sma_fast" in ind["params"] and "sma_slow" in ind["params"]:
        if ind["params"]["sma_slow"] <= ind["params"]["sma_fast"]:
            ind["params"]["sma_slow"] = ind["params"]["sma_fast"] + random.randint(10, 60)
    # Sanidad: rsi_os < rsi_ob
    if "rsi_os" in ind["params"] and "rsi_ob" in ind["params"]:
        if ind["params"]["rsi_os"] >= ind["params"]["rsi_ob"]:
            ind["params"]["rsi_ob"] = ind["params"]["rsi_os"] + random.randint(10, 30)
    return ind


# ── 3. EVALUADOR ─────────────────────────────────────────────────────

def calc_sma(candles: list, idx: int, period: int) -> float:
    """Media móvil simple."""
    if idx < period:
        return 0.0
    return sum(c["c"] for c in candles[idx - period:idx]) / period


def calc_rsi(candles: list, idx: int, period: int) -> float:
    """RSI clásico."""
    if idx < period + 1:
        return 50.0
    gains, losses = [], []
    for j in range(idx - period + 1, idx + 1):
        diff = candles[j]["c"] - candles[j - 1]["c"]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    avg_g = sum(gains) / period
    avg_l = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - 100.0 / (1.0 + rs)


def evaluate(individual: dict, candles: list, capital: float = 10_000) -> dict:
    """Ejecuta una estrategia contra velas sintéticas.
    Devuelve métricas completas.
    """
    p = individual["params"]
    et = individual["entry_type"]
    xt = individual["exit_type"]

    # Asegurar parámetros requeridos según entry_type
    if et == "rsi" and "rsi_period" not in p:
        p["rsi_period"] = random.randint(7, 21)
        p["rsi_os"] = p.get("rsi_os", random.randint(20, 40))
        p["rsi_ob"] = p.get("rsi_ob", random.randint(60, 80))
    if et == "sma_cross":
        if "sma_fast" not in p: p["sma_fast"] = random.randint(3, 15)
        if "sma_slow" not in p: p["sma_slow"] = random.randint(15, 100)
    if et == "volume_spike" and "vol_threshold" not in p:
        p["vol_threshold"] = round(random.uniform(1.1, 3.0), 1)

    # Asegurar parámetros requeridos según exit_type
    if xt in ("stop_loss_take_profit", "trailing_stop") and "stop_loss" not in p:
        p["stop_loss"] = round(random.uniform(0.5, 3.0), 1)
    if xt == "stop_loss_take_profit" and "take_profit" not in p:
        p["take_profit"] = round(random.uniform(1.0, 6.0), 1)
    if xt in ("time_stop", "trailing_stop") and "max_hold" not in p:
        p["max_hold"] = random.randint(5, 48)

    pos = 0          # 0=out, 1=in
    entry_px = 0.0
    entry_bar = 0
    trades: list[dict] = []
    wins = losses = 0
    equity_curve = [capital]

    min_bars = max(p.get("sma_slow", 1), p.get("rsi_period", 1), 1)

    for i in range(min_bars, len(candles)):
        c = candles[i]

        # Precalcular SMAs si aplica
        fast = slow = prev_fast = prev_slow = 0.0
        if individual["entry_type"] == "sma_cross" and i >= p["sma_slow"]:
            fast = calc_sma(candles, i, p["sma_fast"])
            slow = calc_sma(candles, i, p["sma_slow"])
            prev_fast = calc_sma(candles, i - 1, p["sma_fast"])
            prev_slow = calc_sma(candles, i - 1, p["sma_slow"])

        # ── ENTRY ──
        if pos == 0:
            # Calcular volatilidad reciente para filtro
            recent_vol = 99
            vol_window = min(20, i)
            if vol_window > 5:
                returns_20 = [
                    abs((candles[j]["c"] - candles[j - 1]["c"]) / candles[j - 1]["c"]) * 100
                    for j in range(i - vol_window, i)
                    if candles[j - 1]["c"] > 0
                ]
                recent_vol = sum(returns_20) / len(returns_20) if returns_20 else 0

            enter = False
            et = individual["entry_type"]

            # Saltar si volatilidad > máximo permitido
            if recent_vol > p.get("max_vol", 99):
                pass

            if et == "sma_cross":
                if fast > slow and prev_fast <= prev_slow:
                    enter = True
            elif et == "volume_spike":
                lookback = min(20, i)
                if lookback > 0:
                    avg_vol = sum(candles[j]["v"] for j in range(i - lookback, i)) / lookback
                    if avg_vol > 0 and c["v"] > avg_vol * p.get("vol_threshold", 2.0):
                        enter = True
            elif et == "rsi":
                if i >= p.get("rsi_period", 14):
                    rsi = calc_rsi(candles, i, p["rsi_period"])
                    if rsi < p.get("rsi_os", 30):
                        enter = True
            elif et == "price_level":
                lb = max(1, min(p.get("pa_lookback", 12), i))
                hi_n = max(candles[j]["h"] for j in range(i - lb, i))
                if c["c"] > hi_n:
                    enter = True

            if enter:
                pos = 1
                entry_px = c["c"]
                entry_bar = i

        # ── EXIT ──
        elif pos == 1:
            change = (c["c"] - entry_px) / entry_px * 100
            held = i - entry_bar
            should_exit = False
            reason = ""

            xt = individual["exit_type"]
            if xt == "stop_loss_take_profit":
                if change <= -p.get("stop_loss", 999):
                    should_exit, reason = True, "sl"
                elif change >= p.get("take_profit", 999):
                    should_exit, reason = True, "tp"
            elif xt == "trailing_stop":
                max_runup = max(
                    (candles[j]["h"] - entry_px) / entry_px * 100
                    for j in range(entry_bar, i + 1)
                )
                trail_pct = p.get("stop_loss", 2.0) * 1.2
                if max_runup > 0.8 and (max_runup - abs(change)) >= trail_pct:
                    should_exit, reason = True, "trail"
            elif xt == "time_stop":
                if held >= p.get("max_hold", 48):
                    should_exit, reason = True, "time"

            if should_exit:
                pnl_pct = change
                trades.append({
                    "entry": round(entry_px, 2),
                    "exit": round(c["c"], 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": reason,
                    "bars": held,
                })
                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1
                pos = 0

        # Equity (marcado a mercado)
        if pos == 0:
            equity_curve.append(capital)
        else:
            unrealized = capital * (1.0 + (c["c"] - entry_px) / entry_px)
            equity_curve.append(unrealized)

    # ── Métricas agregadas ──
    total = len(trades)
    win_rate = (wins / total * 100) if total > 0 else 0.0
    avg_pnl = sum(t["pnl_pct"] for t in trades) / total if total > 0 else 0.0

    gains_sum = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
    losses_sum = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] < 0)
    profit_factor = (
        gains_sum / abs(losses_sum)
        if losses_sum != 0
        else (999.0 if gains_sum > 0 else 0.0)
    )

    # Sharpe ratio (anualizado aproximado)
    returns = [
        (equity_curve[k] - equity_curve[k - 1]) / equity_curve[k - 1]
        for k in range(1, len(equity_curve))
        if equity_curve[k - 1] > 0
    ]
    avg_ret = sum(returns) / len(returns) if returns else 0.0
    std_ret = (
        math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns))
        if len(returns) > 1
        else 0.001
    )
    sharpe = (avg_ret / std_ret) * math.sqrt(365 * 24) if std_ret > 0 else 0.0

    # Drawdown máximo
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Score compuesto: PF * WR * trade_penalty * (1 - dd/100)^2 * loss_penalty
    pf_for_score = min(profit_factor, 10.0) if profit_factor != 999 else 10.0
    trade_penalty = min(1.0, total / 25) if total > 8 else 0.0
    dd_factor = max(0.0, (1.0 - max_dd / 100) ** 2)
    # Penalizar 0 pérdidas: estadísticamente improbable, probable overfitting
    loss_penalty = 1.0
    if losses == 0 and total >= 5:
        loss_penalty = 0.2
    elif losses == 0:
        loss_penalty = 0.0
    score = pf_for_score * (win_rate / 100.0) * trade_penalty * dd_factor * loss_penalty

    return {
        "total_trades": total,
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != 999 else 999,
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "score": round(score, 2),
        "wins": wins,
        "losses": losses,
    }


# ── 4. MUTACIÓN ──────────────────────────────────────────────────────

def mutate(individual: dict, rate: float = 0.25) -> dict:
    """Copia y muta parámetros numéricos con tweak gaussiano."""
    child = copy.deepcopy(individual)
    child["name"] = f"{individual['semilla']}-mut-{random.randint(100, 999)}"

    for k, v in child["params"].items():
        if random.random() > rate:
            continue
        factor = random.gauss(1.0, 0.20)  # ~20% de cambio típico
        new_val = v * factor
        if isinstance(v, int):
            child["params"][k] = max(1, int(round(new_val)))
        else:
            child["params"][k] = round(max(0.1, new_val), 1)

    # Sanidad post-mutación
    _sanitize(child)
    return child


def _sanitize(ind: dict):
    """Corrige inconsistencias en parámetros."""
    p = ind["params"]
    if "sma_fast" in p and "sma_slow" in p:
        if p["sma_slow"] <= p["sma_fast"]:
            p["sma_slow"] = p["sma_fast"] + random.randint(10, 60)
    if "rsi_os" in p and "rsi_ob" in p:
        if p["rsi_os"] >= p["rsi_ob"]:
            p["rsi_ob"] = p["rsi_os"] + random.randint(10, 30)
    if "stop_loss" in p:
        p["stop_loss"] = max(0.1, p["stop_loss"])
    if "take_profit" in p:
        p["take_profit"] = max(0.2, p["take_profit"])


# ── 5. CROSS-POLLINATION ────────────────────────────────────────────

def cross_pollinate(ind_a: dict, ind_b: dict) -> dict:
    """Combina parámetros de dos individuos de diferentes semillas.
    El hijo hereda la semilla de ind_a con parámetros mezclados de ind_b.
    """
    child = copy.deepcopy(ind_a)
    child["name"] = f"cross-{ind_a['semilla']}-{ind_b['semilla']}-{random.randint(100, 999)}"
    child["semilla"] = f"{ind_a['semilla']}+{ind_b['semilla']}"

    # Mezclar parámetros
    for k in ind_b["params"]:
        if random.random() < 0.4:
            child["params"][k] = ind_b["params"][k]

    # Posible herencia de entry_type / exit_type
    if random.random() < 0.2:
        child["entry_type"] = ind_b["entry_type"]
    if random.random() < 0.2:
        child["exit_type"] = ind_b["exit_type"]

    _sanitize(child)
    return child


# ── 6. PERSISTENCIA ──────────────────────────────────────────────────

def save_individual(individual: dict, metrics: dict):
    """Guarda estrategia como JSON en semillas/."""
    fname = f"{individual['name']}.json"
    path = SEMILLAS_DIR / fname
    with open(path, "w") as f:
        json.dump({"strategy": individual, "metrics": metrics}, f, indent=2)


def save_report(generation: int, population: list, results: list, elapsed: float):
    """Guarda reporte de generación en resultados/."""
    report = {
        "generation": generation,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(elapsed, 2),
        "population_size": len(population),
        "top5": [
            {
                "name": r[3]["name"],
                "semilla": r[3]["semilla"],
                "score": r[0],
                "metrics": r[1],
            }
            for r in results[:5]
        ],
    }
    path = RESULTADOS_DIR / f"gen-{generation:03d}.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


def share_discovery(top5: list, config: dict):
    """Escribe descubrimiento en shared-bridge/discoveries/."""
    ts = time.strftime("%Y-%m-%d")
    path = BRIDGE_DIR / f"{ts}-evolucion-multi-seed.md"
    with open(path, "w") as f:
        f.write(f"# Evolución Multi-Semilla — {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"## Configuración\n")
        f.write(f"- Generaciones: {config['generations']}\n")
        f.write(f"- Población: {config['pop_per_seed']} por semilla ({len(SEEDS)} semillas)\n")
        f.write(f"- Train: {', '.join(config['train_regimes'])}\n")
        f.write(f"- Test: {', '.join(config['test_regimes'])}\n")
        f.write(f"- Validación final: {config['final_regime']}\n")
        f.write(f"- Tasa de mutación: {config['mutation_rate']}\n")
        f.write(f"- Tasa de cross-pollination: {config['cross_rate']}\n\n")
        f.write(f"## Top 5 Estrategias\n\n")
        f.write(f"| # | Nombre | Semilla | PF | WR | Sharpe | DD | Trades |\n")
        f.write(f"|---|--------|---------|----|----|--------|----|--------|\n")
        for i, (score, ind, metrics) in enumerate(top5, 1):
            f.write(
                f"| {i} | {ind['name']} | {ind['semilla']} "
                f"| {metrics['profit_factor']} | {metrics['win_rate']}% "
                f"| {metrics['sharpe']} | {metrics['max_drawdown']}% "
                f"| {metrics['total_trades']} |\n"
            )
        f.write(f"\n→ Detalle en 04-evolucion-trading/resultados/\n")
    return path


# ── 7. ENGINE PRINCIPAL ──────────────────────────────────────────────

def evolve(
    generations: int = 25,
    pop_per_seed: int = 10,
    mutation_rate: float = 0.35,
    cross_rate: float = 0.20,
    keep_ratio: float = 0.3,
    train_regimes: list[str] = None,
    test_regimes: list[str] = None,
    final_regime: str = "volatil",
):
    """Loop evolutivo principal."""
    if train_regimes is None:
        train_regimes = ["alcista", "lateral", "volatil"]
    if test_regimes is None:
        test_regimes = ["bajista", "ciclico"]

    config = {
        "generations": generations,
        "pop_per_seed": pop_per_seed,
        "mutation_rate": mutation_rate,
        "cross_rate": cross_rate,
        "keep_ratio": keep_ratio,
        "train_regimes": train_regimes,
        "test_regimes": test_regimes,
        "final_regime": final_regime,
    }

    print(f"\n{'='*70}")
    print(f"  🧬 EVOLUCIÓN MULTI-SEMILLA")
    print(f"{'='*70}")
    print(f"  Semillas: {', '.join(SEEDS.keys())}")
    print(f"  Población: {len(SEEDS) * pop_per_seed} ({pop_per_seed}/semilla)")
    print(f"  Generaciones: {generations}")
    print(f"{'='*70}\n")

    # Generar datos
    train_data, test_data = generate_multi_regime(train_regimes, test_regimes)
    print(f"  📊 Train: {len(train_data)} velas ({', '.join(train_regimes)})")
    print(f"  📊 Test:  {len(test_data)} velas ({', '.join(test_regimes)})")
    print(f"  📊 Final: {final_regime}\n")

    # ── Población inicial ──
    population: list[dict] = []
    for seed_name in SEEDS:
        for _ in range(pop_per_seed):
            population.append(spawn(seed_name))

    print(f"  🌱 Población inicial: {len(population)} individuos\n")
    start_time = time.time()

    # Cabecera de tabla
    print(f"  {'Gen':>4} | {'Mejor':>30} | {'PF':>7} | {'WR':>6} | {'Losses':>6} | {'Score':>7} | {'Trades':>6}")
    print(f"  {'-'*4}-+-{'-'*30}-+-{'-'*7}-+-{'-'*6}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}")

    history = []
    best_score_ever = 0.0
    gens_without_improvement = 0

    for gen in range(generations):
        results = []
        for ind in population:
            m_train = evaluate(ind, train_data)
            m_test = evaluate(ind, test_data)
            # Score compuesto con penalización por overfitting
            train_part = m_train["score"]
            test_part = m_test["score"]
            overfit_penalty = 1.0 - min(1.0, abs(train_part - test_part) / max(train_part, 0.01)) * 0.3
            score = (train_part * 0.55 + test_part * 0.45) * overfit_penalty
            results.append((score, m_train, m_test, ind))

        results.sort(key=lambda x: x[0], reverse=True)
        best = results[0]

        # Anti-stagnation tracking
        if best[0] > best_score_ever:
            best_score_ever = best[0]
            gens_without_improvement = 0
        else:
            gens_without_improvement += 1
        history.append({
            "gen": gen + 1,
            "best_name": best[3]["name"],
            "best_score": round(best[0], 2),
            "best_pf": best[1]["profit_factor"],
            "best_wr": best[1]["win_rate"],
        })

        print(
            f"  {gen+1:>4} | {best[3]['name']:>30} "
            f"| {best[1]['profit_factor']:>7} "
            f"| {best[1]['win_rate']:>5.1f}% "
            f"| {best[1]['losses']:>6} "
            f"| {best[0]:>7.1f} "
            f"| {best[1]['total_trades']:>6}"
        )

        # Guardar mejor de cada generación
        save_individual(best[3], best[1])

        # Selección — mejores + campeón de cada semilla
        n_survivors = max(1, int(len(population) * keep_ratio))
        survivors = [r[3] for r in results[:n_survivors]]

        # Asegurar que cada semilla tenga al menos un representante
        for seed_name in SEEDS:
            seed_individuals = [
                r[3] for r in results if r[3]["semilla"].startswith(seed_name)
            ]
            if seed_individuals:
                survivors.append(seed_individuals[0])

        # Dedup por nombre único
        seen = set()
        unique_survivors = []
        for s in survivors:
            if s["name"] not in seen:
                seen.add(s["name"])
                unique_survivors.append(s)
        survivors = unique_survivors

        # ── Nueva generación ──
        new_pop = list(survivors)
        target_size = len(SEEDS) * pop_per_seed
        while len(new_pop) < target_size:
            roll = random.random()
            if roll < cross_rate and len(survivors) >= 2:
                # Cross-pollination
                parent_a = random.choice(survivors)
                pool_b = [s for s in survivors if s["semilla"] != parent_a["semilla"]]
                parent_b = random.choice(pool_b if pool_b else survivors)
                child = cross_pollinate(parent_a, parent_b)
            else:
                # Mutación
                parent = random.choice(survivors)
                child = mutate(parent, rate=mutation_rate)
            new_pop.append(child)

        # Anti-stagnation: inyectar 30% de sangre fresca si 4 gens sin mejora
        if gens_without_improvement >= 4:
            n_inject = max(4, int(len(new_pop) * 0.30))
            seed_names = list(SEEDS.keys())
            for _ in range(n_inject):
                new_pop.append(spawn(random.choice(seed_names)))
            gens_without_improvement = 0

        population = new_pop

    # ── Validación final en régimen no visto ──
    elapsed = time.time() - start_time
    print(f"\n  {'─'*70}")
    final_candles = generate_regime(final_regime, n=600)
    print(f"  🔬 Validación final: {final_regime} ({len(final_candles)} velas)\n")

    final_results = []
    for ind in population:
        m = evaluate(ind, final_candles)
        final_results.append((m["score"], ind, m))

    final_results.sort(key=lambda x: x[0], reverse=True)
    top5 = final_results[:5]

    # Mostrar top 5
    print(f"  {'#':>2} | {'Nombre':>30} | {'Semilla':>18} | {'PF':>7} | {'WR':>6} | {'Sharpe':>7} | {'DD':>6} | {'Trades':>6}")
    print(f"  {'-'*2}-+-{'-'*30}-+-{'-'*18}-+-{'-'*7}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}-+-{'-'*6}")
    for i, (score, ind, m) in enumerate(top5, 1):
        print(
            f"  {i:>2} | {ind['name']:>30} | {ind['semilla']:>18} "
            f"| {m['profit_factor']:>7} | {m['win_rate']:>5.1f}% "
            f"| {m['sharpe']:>7} | {m['max_drawdown']:>5.1f}% "
            f"| {m['total_trades']:>6}"
        )

    # Guardar reporte final
    final_report = {
        "config": config,
        "elapsed_seconds": round(elapsed, 2),
        "history": history,
        "top5": [
            {
                "name": ind["name"],
                "semilla": ind["semilla"],
                "entry_type": ind["entry_type"],
                "exit_type": ind["exit_type"],
                "params": ind["params"],
                "metrics": m,
            }
            for _, ind, m in top5
        ],
    }
    report_path = RESULTADOS_DIR / "final.json"
    with open(report_path, "w") as f:
        json.dump(final_report, f, indent=2)

    # Compartir descubrimiento
    bridge_path = share_discovery(top5, config)

    print(f"\n  {'='*70}")
    print(f"  ✅ Evolución completada en {elapsed:.1f}s")
    print(f"  📁 Reporte:        {report_path}")
    print(f"  📁 Estrategias:    {SEMILLAS_DIR}/")
    print(f"  📁 Puente:         {bridge_path}")
    print(f"  {'='*70}\n")


# ── 8. CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🧬 Evolución multi-semilla de estrategias de trading"
    )
    parser.add_argument("--generations", type=int, default=25, help="Número de generaciones")
    parser.add_argument("--pop-per-seed", type=int, default=10, help="Individuos por semilla")
    parser.add_argument("--mutation-rate", type=float, default=0.35, help="Tasa de mutación")
    parser.add_argument("--cross-rate", type=float, default=0.20, help="Tasa de cross-pollination")
    parser.add_argument("--keep", type=float, default=0.3, help="Fracción de supervivientes")
    parser.add_argument("--final", type=str, default="volatil", help="Régimen de validación final")
    parser.add_argument("--seed", type=int, default=None, help="Semilla aleatoria (reproducibilidad)")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    evolve(
        generations=args.generations,
        pop_per_seed=args.pop_per_seed,
        mutation_rate=args.mutation_rate,
        cross_rate=args.cross_rate,
        keep_ratio=args.keep,
        final_regime=args.final,
    )
