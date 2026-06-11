# ORCHESTRATION.md — Análisis Crítico del Sistema

*Fecha: 2026-06-11*

## 1. Estado Actual

### Daemons

| Proceso | Estado | PIDs | Notas |
|---------|--------|------|-------|
| supervisor | ✅ | 106466 | 1 instancia |
| busd | ⚠️ **3 instancias** | 178662, 188932, 202661 | Debería ser singleton |
| runner.py (trading) | ⚠️ **2 instancias** | 195581, 202660 | Debería ser singleton |
| dashboard.py | ✅ | 186540 | 1 instancia, puerto 9095 |
| inotifywait | ⚠️ **3 instancias** | 178671, 188939, 202668 | 1 por cada busd |

### Workers

| Worker | Estado | Última actividad |
|--------|--------|------------------|
| worker-1 | ❌ Idle > 15 min | Sin tarea asignada |
| worker-2 | ❓ Activo (QUEUED) | Procesando tarea anterior |

## 2. Qué Funciona (Fortalezas)

### ✅ Pipeline de datos completo
HL API → runner.py → CSV + JSON + bus, ciclo cada 5min, 4 assets (ETH/BTC/SOL/HYPE). Sin intervención manual desde que arranca.

### ✅ Señales multi-factor
RSI + MACD + funding rate + orderbook imbalance → dirección unificada. El backtest histórico mostró Sharpe 4.63 con datos reales de HL.

### ✅ IC Tracking persistente
`ic_pairs.json` acumula pares señal→forward return entre reinicios. Cuando tenga N≥10 mostrará IC con significado estadístico.

### ✅ Reportes generados automáticamente
- `trading_report.html` (~30min)
- `live_signals.json` (cada 5min)
- Dashboard `:9095` con auto-refresh

### ✅ Alertas al bus
RSI > 70 o < 30 escribe alerta a worker-2 inbox para posible video.

## 3. Qué No Funciona (Debilidades)

### ❌ Duplicación de procesos
Hay **2 runners** y **3 busds** corriendo. El supervisor.py inicia busd, pero también lo inician otros scripts. No hay un mecanismo de PID lock. Los runners duplicados compiten por escribir al mismo CSV y JSON.

### ❌ worker-1 totalmente ocioso
worker-1 lleva > 15 min sin tarea asignada. Se está desperdiciando 50% de capacidad de cómputo de workers.

### ❌ Sin mechanismo de PID file en runner.py
El runner no verifica si ya hay otro runner corriendo. Fácil de arreglar con lockfile.

### ❌ IC tracking necesita ~2h para madurar
`compute_ic()` requiere N≥10 pares. Con 1 par por ciclo de 5min, toma ~50 min tener IC significativo. Y cada reinicio del runner pierde el buffer (parcialmente mitigado con `ic_pairs.json` persistente).

### ❌ Sin test automatizado
No hay forma de verificar que el sistema funciona sin mirar manualmente los logs. Si runner.py crashea silenciosamente, nadie se entera hasta que HELPERD avisa.

## 4. Qué Mejoraría (Priorizado)

### P1 — Lock de procesos
Añadir PID file a runner.py y dashboard.py. Antes de arrancar, verificar si el PID existe y el proceso está vivo. `flock` en el archivo.

### P2 — Asignar worker-1
worker-1 debería correr el backtest de s39 periódicamente o hacer análisis históricos de `trading_log.csv`. También podría ser el "research agent" que lee papers y actualiza TRADING.md automáticamente.

### P3 — Healthcheck endpoint
Añadir un endpoint HTTP simple al runner (puerto 9096) que devuelva:
- Último ciclo ejecutado
- Señales actuales
- IC stats
- Uptime
- Si el runner está atrasado (>6min sin ciclo)

### P4 — Auto-cleanup de busd duplicados
El supervisor debería matar busds antiguos antes de arrancar uno nuevo. O mejor: que busd escriba su PID y se verifique.

### P5 — Review estratégico semanal
El runner ya calcula forward returns pero no los consume. Añadir un ciclo semanal que:
1. Lea `ic_pairs.json` completo
2. Compute IC por señal (RSI, MACD, funding, OB)
3. Ajuste pesos de `direction()` según IC histórico
4. Escriba reporte a `TRADING.md`

### P6 — Más assets
Añadir TOPIX, ARB, DOGE, TRUMP al runner. La API de HL responde en ~900ms para todos los assets simultáneamente — no hay costo adicional.

### P7 — Modo dry-run conectado al RiskManager de s39
Conectar el RiskManager de `s39-trading-bot/mega_alpha` al runner para tener:
- Circuit breaker si drawdown > 15%
- Position sizing por Kelly
- Stop-loss automático

### P8 — Fine-tuning con datos propios
`trading_log.csv` + `ic_pairs.json` ya tienen datos estructurados. Fine-tunear Qwen3-8B (como hizo TradingGroup con 1,080 samples) para crear un modelo especializado en señales HL.

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Runner duplicado corrompe CSV/JSON | Alta | Medio | PID lock (P1) |
| API HL rate limitea | Baja | Alto | Cache en `live_signals.json` |
| Busd múltiple entrega mensajes duplicados | Media | Bajo | Dedup en worker (idempotencia) |
| Sin healthcheck, nadie detecta caída | Alta | Alto | Healthcheck endpoint (P3) |
| IC nunca madura por reinicios | Media | Medio | `ic_pairs.json` persistente (✅) |

## 6. Resumen

El sistema genera señales de trading funcionales (Sharpe 4.63 backtest, 4 assets en vivo), pero la orquestación tiene problemas de运维 (procesos duplicados, workers ociosos, sin healthcheck). Las 3 prioridades inmediatas son:

1. **PID lock** para evitar duplicados
2. **Asignar worker-1** a backtesting/research
3. **Healthcheck endpoint** para detectar caídas

Después: review estratégico semanal con IC → ajuste de pesos → fine-tuning.
