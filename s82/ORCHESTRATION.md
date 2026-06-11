# ORCHESTRATION.md — Análisis Crítico del Sistema

*Fecha: 2026-06-11 (actualizado post-análisis de 7 papers/experimentos)*

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
| worker-1 | ❌ Idle permanente | Sin tarea asignada desde el inicio |
| worker-2 | ❓ Activo (QUEUED) | Procesando tarea anterior |

### Procesos duplicados (confirmado)

```
3× busd    (178662, 188932, 202661) — supervisor.py + otros scripts lanzan sin matar anterior
2× runner  (195581, 202660) — lockfile no implementado
1× dashboard (186540) — bien, singleton
```

### Research validación

7 papers/experimentos analizados que validan o contradicen nuestras decisiones:

| Fuente | Lo que valida | Lo que cuestiona |
|--------|---------------|------------------|
| QuantAgent (2025) | Solo OHLC basta, sin news | — |
| TiMi (2025) | Runner determinista + LLM offline = patrón correcto | — |
| 22 Agents en HL (2026) | Funding rate mejor señal, mean reversion no funciona | — |
| TradingGroup (2025) | Self-reflection + data pipeline mejora resultados | Necesitamos fine-tuning |
| FinAgent (KDD 2024) | Dual-level reflection (táctico + estratégico) | Solo tenemos táctico |
| Swarm Patterns (2026) | Risk Gate determinista entre señal y ejecución | No tenemos risk gate |
| Hyperliquid Backtest (Keel) | 12 meses mínimos, 15m OHLC + 1h funding | Nuestro backtest fue solo 7 días |

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

### ❌ Sin risk gate entre señal y ejecución
Los 7 papers coinciden: debe haber un risk gate determinista (Python, no LLM) entre la señal y cualquier acción. Nuestro runner genera señales pero no las filtra por riesgo — no hay circuit breaker, ni Kelly sizing, ni stop-loss conectado.

### ❌ Sin fine-tuning con datos propios
TradingGroup demostró que fine-tunear Qwen3-8B con solo 1,080 samples sintéticas supera a GPT-4o-mini. Nosotros tenemos `trading_log.csv` + `ic_pairs.json` acumulando datos — no los estamos usando.

### ❌ Backtest insuficiente (7 días)
Keel recomienda mínimo 12 meses de datos HL con 15m OHLC + 1h funding para validar estrategias. Nuestro backtest fue solo 7 días. El Sharpe 4.63 puede ser overfit al régimen de esa ventana.

### ❌ Sin healthcheck ni tests automatizados
No hay forma de verificar que el sistema funciona sin mirar manualmente los logs. Si runner.py crashea silenciosamente, nadie se entera hasta que HELPERD avisa. No hay tests unitarios ni de integración.

## 4. Qué Mejoraría (Priorizado con evidencia de research)

### P1 — Risk Gate determinista (Swarm Patterns + TiMi)
Antes de que cualquier señal llegue a worker-2, debe pasar por un risk gate Python:
- Circuit breaker si drawdown > 15%
- Position sizing por Kelly (s39 ya lo tiene)
- Stop-loss automático por ATR
- Validación: funding rate como filtro adicional

**Evidencia**: TiMi y Swarm Patterns coinciden: "Reserve LLMs solo para análisis — la ejecución debe ser código puro."

### P2 — Lock de procesos + auto-cleanup
- PID file para runner.py y dashboard.py con verificación al arrancar
- Supervisor: matar busds antiguos antes de lanzar nuevo
- `flock` en archivos de salida para prevenir corrupción por duplicados

### P3 — Asignar worker-1 a backtesting extenso (Keel + 22 Agents)
worker-1 debe correr backtests de 12+ meses con datos HL (15m OHLC + 1h funding) para:
- Validar que Sharpe 4.63 no es overfit a 7 días
- Probar regimenes múltiples (bull funding 2023-24 vs neutral 2025)
- Testear nuevas señales (funding arbitrage, grid trading, trend following puro)

**Evidencia**: Keel recomienda mínimo 12 meses y 2 regimenes de funding. 22 Agents en HL mostró que mean reversion pierde -18 a -33% en perps.

### P4 — Healthcheck endpoint (puerto 9096)
Endpoint HTTP que devuelva en JSON:
- Último ciclo ejecutado y timestamp
- Señales actuales con RSI y funding
- IC stats por asset
- Uptime del proceso
- Warning si ciclo atrasado (>6min)

### P5 — Review estratégico semanal (FinAgent dual-level + TradingGroup)
El runner ya tiene el **reflejo táctico** (cada ciclo escribe CSV + forward returns). Falta el **reflejo estratégico** semanal:
1. Leer `ic_pairs.json` completo (>350 pares/semana)
2. Computar IC real por señal (RSI vs forward return, funding vs forward return)
3. Identificar qué señales están decayendo (IC decay)
4. Ajustar pesos de `direction()` automáticamente
5. Escribir reporte a TRADING.md

**Evidencia**: FinAgent demostró que dual-level reflection da +36% sobre sin-reflection. TradingGroup lo implementa con pipeline de datos → fine-tuning.

### P6 — Fine-tuning con datos propios (TradingGroup)
Cuando `trading_log.csv` tenga >1,000 filas (~4 días de datos):
- Extraer pares señal→forward return de `ic_pairs.json`
- Fine-tunear Qwen3-8B con LoRA (0.5% parámetros, ~6h en V100)
- Generar Qwen3-Trader-HL-8B

**Evidencia**: TradingGroup fine-tuneó con solo 1,080 samples y superó a GPT-4o-mini en TSLA y NFLX.

### P7 — Backtest multiciclo (12 meses)
worker-1 debe:
1. Fetch 12 meses de datos HL (15m OHLC + 1h funding) usando `s41-dex-volume-fetcher`
2. Correr el optimizer de s39 sobre múltiples ventanas
3. Reportar: Sharpe en bull funding regime vs neutral funding regime
4. Si Sharpe se mantiene >1.5 en ambos regimenes → considerar live trading

**Evidencia**: Keel: "A reasonable minimum is two full regime cycles — for Hyperliquid that means at least 12 months."

### P8 — Más assets con funding arb señal
Añadir ARB, DOGE, TRUMP. No por su precio, sino por el **spread de funding** entre exchanges. El artículo de funding arb mostró spreads de 21-61% APR en long-tail perps. Nueva señal: `cross_exchange_funding_spread`.

## 5. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Runner duplicado corrompe CSV/JSON | Alta | Medio | PID lock (P1) |
| API HL rate limitea | Baja | Alto | Cache en `live_signals.json` |
| Busd múltiple entrega mensajes duplicados | Media | Bajo | Dedup en worker (idempotencia) |
| Sin healthcheck, nadie detecta caída | Alta | Alto | Healthcheck endpoint (P3) |
| IC nunca madura por reinicios | Media | Medio | `ic_pairs.json` persistente (✅) |

## 6. Resumen

El sistema genera señales de trading funcionales (Sharpe 4.63 backtest, 4 assets en vivo), validado por 7 papers/experimentos que confirman nuestra dirección. Pero la orquestación tiene problemas concretos.

### Lo que está bien
- ✅ Runner determinista cada 5min (TiMi pattern)
- ✅ Solo OHLC + datos de HL, sin news (QuantAgent)
- ✅ Funding rate como señal principal (22 Agents HL)
- ✅ IC tracking persistente (TradingGroup data pipeline)
- ✅ Logging estructurado (CSV + JSON)

### Lo que falta
- ❌ Risk gate determinista entre señal y ejecución
- ❌ Backtest > 12 meses para validar Sharpe
- ❌ Healthcheck endpoint
- ❌ Dual-level reflection (táctico ✅, estratégico ❌)
- ❌ Fine-tuning con datos propios
- ❌ worker-1 inactivo

### Prioridades

| # | Qué | Por qué | Evidencia |
|---|-----|---------|-----------|
| P1 | Risk Gate | Protege capital | Swarm Patterns + TiMi |
| P2 | PID lock | Elimina duplicados | Problemas actuales |
| P3 | worker-1 → backtest 12m | Validar Sharpe real | Keel + 22 Agents HL |
| P4 | Healthcheck :9096 | Detectar caídas | Sin esto, operamos ciegos |
| P5 | Review estratégico | Ajustar pesos por IC | FinAgent dual-level |
| P6 | Fine-tuning Qwen3 | Modelo HL propio | TradingGroup LoRA |
