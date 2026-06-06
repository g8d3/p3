# Engine Evolutivo Básico

## Qué encontré
El `trading_evolve.py` en 03-trading/ ejecuta selección natural
sobre estrategias de trading con datos sintéticos.

## Cómo funciona
- Genera 2000 velas sintéticas con tendencia + ruido + spikes
- Crea población de 30 estrategias con parámetros aleatorios
- Evalúa cada una contra los mismos datos
- Selecciona las mejores (top 25%)
- Muta y replica para siguiente generación
- 15 generaciones

## Resultados
- Las estrategias convergen rápido pero con pocas trades
- PF 999 (infinito) en generación 1 es sospechoso
- Solo 4-5 trades en 2000 velas → umbrales muy restrictivos

## Qué falta
1. Múltiples semillas (familias de estrategias)
2. Cross-pollination entre semillas
3. Datos sintéticos con diferentes regimes de mercado
4. Walk-forward validation
5. Más trades por estrategia (umbrales más sensibles)

## Código base
`p3/s84/03-trading/trading_evolve.py`
