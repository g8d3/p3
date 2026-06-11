#!/usr/bin/env python3
"""Señal sintética: simula precios ETH, calcula RSI + MACD + FundingRate."""
import numpy as np
import pandas as pd

np.random.seed(42)

# Simular 200 velas 1H de ETH (~8 días)
n = 200
price = 1650.0
prices = []
for _ in range(n):
    ret = np.random.normal(0, 0.008)  # 0.8% volatilidad horaria
    price *= (1 + ret)
    prices.append(round(price, 2))

close = np.array(prices)
s = pd.Series(close)

# RSI(14)
deltas = np.diff(close)
gains = np.where(deltas > 0, deltas, 0)
losses = np.where(deltas < 0, -deltas, 0)
avg_g = np.mean(gains[-14:])
avg_l = np.mean(losses[-14:])
rsi = 100 - (100 / (1 + avg_g / avg_l)) if avg_l != 0 else 100

# MACD(12,26,9)
ema_f = s.ewm(span=12).mean()
ema_s = s.ewm(span=26).mean()
macd_line = ema_f - ema_s
sig_line = macd_line.ewm(span=9).mean()
macd_hist = (macd_line - sig_line).iloc[-1]

# Funding rate sintético (cíclico, correlacionado con precio)
funding = 0.0001 * np.sin(np.linspace(0, 4*np.pi, n)) + 0.00002 * np.random.randn(n)
funding_current = funding[-1]

# Dirección combinada
def direction(rsi, mh, fr):
    signals = []
    if rsi < 40: signals.append("RSI sobrevendido")
    elif rsi > 60: signals.append("RSI sobrecompra")
    else: signals.append("RSI neutral")
    if mh > 0: signals.append("MACD alcista")
    elif mh < 0: signals.append("MACD bajista")
    if fr > 0.0001: signals.append("funding alto (bajista)")
    elif fr < -0.0001: signals.append("funding negativo (alcista)")
    short_count = sum(1 for s in signals if "bajista" in s or "sobrecompra" in s)
    long_count = sum(1 for s in signals if "alcista" in s or "sobrevendido" in s or "negativo" in s)
    if long_count > short_count: return "LONG"
    if short_count > long_count: return "SHORT"
    return "NEUTRAL"

dir_final = direction(rsi, macd_hist, funding_current)

print(f"=== Señal Sintética ETH ===")
print(f"Velas simuladas: {n} velas 1H")
print(f"Precio actual:   ${close[-1]:.2f}")
print(f"Rango:           ${close.min():.2f} - ${close.max():.2f}")
print(f"Volatilidad:     {np.std(np.diff(close)/close[:-1]):.4f}")
print(f"")
print(f"RSI(14):         {rsi:.1f}")
print(f"MACD hist:       {macd_hist:.2f}")
print(f"Funding Rate:    {funding_current*100:.5f}%")
print(f"")
print(f"Dirección:       {dir_final}")
