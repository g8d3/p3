# TAREA: Evolución de Estrategias de Trading — Múltiples Semillas

## Objetivo
Construir un sistema donde múltiples estrategias de trading evolucionan
por selección natural: nacen, compiten, mutan, las mejores sobreviven.

## Qué existe ya en 03-trading/
- `trading_evolve.py` — engine evolutivo básico con datos sintéticos
- `trading_bot.py` — bot que lee datos reales de Hyperliquid

## Qué construir aquí

### 1. Múltiples semillas
No una sola estrategia, sino varias familias que evolucionan en paralelo:
- Semilla A: estrategias de cruce de medias móviles
- Semilla B: estrategias de volumen
- Semilla C: estrategias de RSI
- Semilla D: estrategias de price action

Cada semilla genera su propia población y compite dentro de su nicho.
Ocasionalmente hay cross-polination entre semillas.

### 2. Datos sintéticos más realistas
- Diferentes regimes: tendencia alcista, bajista, lateral, volátil
- Ruido, gaps, spikes de volumen
- Comisiones y slippage

### 3. Evaluación robusta
- Win rate, profit factor, Sharpe ratio, drawdown máximo
- Trades mínimo para considerar una estrategia válida
- Walk-forward: entrenar en datos A, testear en datos B

### 4. Arquitectura
- Cada estrategia es un archivo JSON en `semillas/`
- El engine evolutivo está en `evolve.py`
- Reportes en `resultados/`
- Todo cabe en ~500 líneas de Python sin dependencias externas

## Stack
- Python 3 stdlib (json, os, math, random)
- Sin bases de datos, sin APIs externas
- Sin hyperliquid SDK (datos sintéticos)

## Formato de entrega
- Código funcionando que se pueda ejecutar con `python3 evolve.py`
- Reporte en terminal con los resultados de cada generación
- README.md explicando el diseño
