# Crypto Trading Strategy Quick Reference

## Core Metrics & Formulas

### Valuation Metrics
| Metric | Formula | Data Source | Signal |
|--------|---------|-------------|--------|
| P/S Ratio | Market Cap / Annual Revenue | Token Terminal, DefiLlama | Low = Long, High = Short |
| Profit Margin | (Revenue - Expenses) / Revenue | Token Terminal | High = Long bias |
| Revenue Growth | (Current - Prior) / Prior | Token Terminal | Accelerating = Long |

### Technical Metrics
| Metric | Formula | Data Source | Usage |
|--------|---------|-------------|-------|
| Realized Volatility | Std(Log Returns) * √252 | CoinGecko, GMX | Grid spacing, TP/SL width |
| ATR | Average True Range (14) | OHLCV data | Position sizing, stops |
| Volatility Regime | RV / Rolling_Median(RV, 30d) | Custom calc | Regime detection |

### Market Metrics
| Metric | Formula | Data Source | Signal |
|--------|---------|-------------|--------|
| Vol/MCap | 24h Volume / Market Cap | DEX Screener | High = momentum |
| Liquidity Depth | Sum(±2% orderbook) / MCap | On-chain, DEX Screener | Deep = better execution |
| Social Sentiment | (Pos - Neg) / Total | LunarCrush, Custom NLP | Extreme = contrarian |

---

## Strategy Templates

### 1. Mean Reversion LP
```
Entry: P/S < sector median, stable profit margin
Range: ±10% base, adjusted by volatility
Stop: Price exits range by 2x width
Rebalance: Weekly or at 50% range breach
DEX: Uniswap V3, SushiSwap
```

### 2. Growth-Driven LP
```
Entry: Revenue growth > 20% QoQ, TVL increasing
Range: Asymmetric (15% down, 30% up)
Stop: Growth decelerates or price -20%
DEX: Uniswap V3
```

### 3. Volatility-Adaptive Grid
```
Grids: 10-20 levels
Spacing: ATR(n) * Multiplier
Bounds: Price ± (ATR * Bound_Multiplier)
Stop: Price breaks bounds by 2x
DEX: GMX, dYdX (for perps)
```

### 4. ATR-Based TP/SL
```
Stop Loss: Entry - (ATR * 2)
Take Profit: Entry + (ATR * 3)
Adjustment: Widen in high vol, tighten in low vol
DEX: GMX (native), dYdX (conditional)
```

### 5. Metric-Triggered TP/SL
```
Take Profit Triggers:
- P/S reaches sector median
- Growth decelerates below threshold
- Social sentiment extreme positive

Stop Loss Triggers:
- Revenue turns negative
- TVL drops > 20% in 7 days
- Social volume collapses > 50%
```

---

## Position Sizing Formulas

### Fixed Fractional Risk
```python
position_size = (account_balance * risk_per_trade) / abs(entry - stop_loss) / entry
# Typical: risk_per_trade = 0.02 (2%)
```

### ATR-Based Sizing
```python
stop_distance = atr * atr_multiplier  # Typical: 2.0
position_size = (account_balance * target_risk) / stop_distance
# Typical: target_risk = 0.02 (2%)
```

---

## Risk Limits

| Parameter | Limit | Notes |
|-----------|-------|-------|
| Max Leverage | 3x (perps), 1x (spot) | |
| Max Position Size | 10% of portfolio | Per asset |
| Max Sector Exposure | 30% of portfolio | |
| Max Correlation | 0.7 between positions | |
| Max Drawdown | 20% portfolio-wide | Hard stop |
| Daily Loss Limit | 5% of portfolio | |

---

## DEX Integration Quick Reference

### GMX (Perpetuals)
```javascript
// Open position
await gmxSdk.createIncreasePosition({
  token: collateral,
  amount: size,
  indexToken: index,
  isLong: true,
  acceptablePrice: price * 1.01
});

// Set TP/SL
await gmxSdk.createOrder({
  orderType: ORDER_TYPE_TP,
  triggerPrice: takeProfitPrice
});
```

### dYdX v4 (Perpetuals)
```python
# Get market data
markets = await indexer.get_perpetual_markets()
orderbook = await indexer.get_perpetual_market_orderbook("BTC-USD")

# Place order
order = await client.create_order(
  market="BTC-USD",
  side="BUY",
  type="LIMIT",
  size="0.01",
  price="50000"
)
```

### Uniswap V3 (LP)
```typescript
// Create LP position
const position = new Position({
  pool: pool,
  liquidity: liquidityAmount,
  tickLower: tickLower,
  tickUpper: tickUpper
});

// Mint NFT position
const { calldata, value } = NonfungiblePositionManager.addPositionParameters({
  tokenA: tokenA,
  tokenB: tokenB,
  fee: FeeAmount.MEDIUM,
  tickLower: tickLower,
  tickUpper: tickUpper,
  liquidity: liquidityAmount
});
```

### Deribit (Options)
```javascript
// Get options instruments
const instruments = await deribit.getInstruments({
  currency: "BTC",
  kind: "option"
});

// Place option order
const order = await deribit.buy({
  instrumentName: "BTC-25APR25-60000-C",
  amount: 1,
  type: "limit",
  price: 0.05
});
```

---

## Data Source Endpoints

### CoinGecko
- `/coins/{id}` - Basic info, market cap
- `/coins/{id}/market_chart` - Historical prices
- `/coins/{id}/ohlc` - OHLC data
- `/onchain/networks/{network}/tokens/{address}/info` - On-chain token info

### DEX Screener
- `/latest/dex/search` - Search pairs
- `/latest/dex/pairs/{chainId}/{pairId}` - Pair details
- `/token-pairs/v1/{chainId}/{tokenAddress}` - Token pairs

### Token Terminal
- `/v2/projects` - List projects
- `/v2/projects/{id}/metrics` - Project metrics
- `/v2/projects/{id}/metric-aggregations` - Aggregated metrics

### DefiLlama
- `/overview/fees/{protocol}` - Protocol fees/revenue
- `/v2/historicalChainTvl` - Historical TVL
- Protocol-specific endpoints for detailed data

### GMX
- `https://arbitrum-api.gmxinfra.io/markets/info` - Market info
- `https://arbitrum-api.gmxinfra.io/prices/ohlcv` - Price data

### dYdX v4
- Indexer: `https://indexer.dydx.trade/v4`
- WebSocket: `wss://indexer.dydx.trade/v4/ws`

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Set up data collection (CoinGecko, DEX Screener)
- [ ] Implement metric calculations
- [ ] Create database schema
- [ ] Build signal generation framework

### Phase 2: Strategy Development
- [ ] Implement mean reversion LP
- [ ] Implement volatility grid
- [ ] Implement ATR TP/SL
- [ ] Create backtesting framework

### Phase 3: DEX Integration
- [ ] Integrate GMX SDK
- [ ] Integrate Uniswap V3 SDK
- [ ] Order management system
- [ ] Gas optimization

### Phase 4: Risk & Monitoring
- [ ] Position sizing algorithms
- [ ] Portfolio risk controls
- [ ] Monitoring dashboard
- [ ] Alerting system

### Phase 5: Optimization
- [ ] Walk-forward optimization
- [ ] Parameter sensitivity
- [ ] Paper trading
- [ ] Performance attribution
