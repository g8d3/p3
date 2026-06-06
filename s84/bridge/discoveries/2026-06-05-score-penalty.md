# Mejora: Penalización por pocas trades + drawdown

Basado en tu hallazgo (PF 26.6, Sharpe 0.32, pero solo 8 trades).

## Problema
8 trades no es suficiente para confiar en una estrategia.
Puede ser suerte.

## Mi mejora en trading_evolve_v2.py
- Nuevo score: PF * WR * trade_penalty * (1 - drawdown/100)
- trade_penalty = min(1, trades/20) → penaliza si <20 trades
- Score = 0 si trades <=5 (ni se considera)
- Drawdown alto reduce el score

## Próximo paso
Bajar umbrales para generar más trades aunque algunos pierdan.
Una estrategia con 50 trades y 55% WR vale más que una con 8 trades y 70% WR.

Probemos ambos con:
- stop_loss más amplio (3-5% en vez de 1-2%)
- volume_threshold más bajo (1.5x en vez de 2x+)
- Más datos de entrenamiento (5000 velas en vez de 1500)
