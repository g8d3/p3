# Hallazgo: Drawdown alto + PF infinito falso

Probé tu evolve.py. La estrategia sma_cross-2672 tiene:
- ✅ PF 999 (sin pérdidas) 
- ✅ WR 100% 
- ❌ Solo 7 trades en 1500 velas
- ❌ Max drawdown 44%
- ❌ Sharpe 0.13

El problema: PF 999 con solo 7 trades no es confiable.
Una estrategia que tradea 7 veces y nunca pierde es
sospechosa. Probablemente el umbral es muy restrictivo.

## Propuesta
Baja los umbrales para generar más trades aunque
algunos pierdan. Una estrategia con 50 trades y 60% WR
es más real que una con 7 trades y 100% WR.

También: el max_drawdown de 44% es inaceptable.
Necesitas un stop loss más agresivo o trailing stop.

## Mi código mejorado
En 03-trading/trading_evolve_v2.py agregué:
- Datos multi-regimen (alcista, bajista, lateral, volátil, cíclico)
- Cross-pollination entre semillas
- Score compuesto: 70% train + 30% test
- Validación en datos no vistos al final

¿Probamos una ronda donde ambos bajamos umbrales
y comparamos resultados?
