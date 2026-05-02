# Data-Driven Crypto Trading Strategies Using DEXes

## 1. Strategy Overview

### 1.1 Core Concept
Build systematic trading strategies that leverage on-chain data metrics to generate signals for trading across decentralized exchanges (DEXes) using various execution methods (LP, grids, TP/SL).

### 1.2 Strategy Classification Matrix

| Metric Category | Trading Approach | DEX Type | Execution Method |
|----------------|------------------|----------|------------------|
| Valuation (P/S, Profit Margin) | Mean Reversion | Spot | LP Ranges |
| Growth Metrics | Momentum | Perpetuals | Grid Trading |
| Volume/Liquidity | Market Making | Options | TP/SL Orders |
| Social Sentiment | Sentiment Trading | All | Hybrid |
| Volatility | Volatility Trading | Perpetuals | Dynamic TP/SL |

## 2. Data Sources & Metrics

### 2.1 Valuation Metrics

#### Price-to-Sales (P/S) Ratio
- **Formula**: `P/S = Market Cap / Annualized Revenue`
- **Data Sources**:
  - Token Terminal: `/v2/projects/{id}/metrics` (revenue, fees)
  - DefiLlama: `/overview/fees/{protocol}` (fees/revenue)
  - CoinGecko: `/coins/{id}` (market cap)
- **Signal Logic**:
  - Low P/S (< sector median) → Potential undervaluation → Long signal
  - High P/S (> 2x sector median) → Potential overvaluation → Short/Reduce signal
- **Implementation**:
  ```python
  def calculate_ps_ratio(protocol_id: str) -> float:
      market_cap = get_market_cap(protocol_id)
      annual_revenue = get_annualized_revenue(protocol_id)
      return market_cap / annual_revenue if annual_revenue > 0 else float('inf')
  ```

#### Profit Margin
- **Formula**: `Profit Margin = (Revenue - Expenses) / Revenue`
- **Data Sources**:
  - Token Terminal: earnings, expenses metrics
  - DefiLlama: revenue breakdown
- **Signal Logic**:
  - High margin (> 50%) → Strong protocol economics → Long bias
  - Negative margin → Unsustainable → Short bias
  - Improving margin → Positive momentum → Long signal

### 2.2 Growth Metrics

#### Revenue Growth
- **Formula**: `YoY Growth = (Current Revenue - Prior Revenue) / Prior Revenue`
- **Data Sources**:
  - Token Terminal: metric aggregations with time series
  - DefiLlama: historical fees/revenue
- **Signal Logic**:
  - Accelerating growth (> 20% QoQ) → Strong momentum → Long
  - Decelerating growth → Warning → Reduce exposure

#### TVL Growth
- **Formula**: `TVL Growth Rate = ΔTVL / TVL_start`
- **Data Sources**:
  - DefiLlama: `/v2/historicalChainTvl` and protocol-specific TVL
- **Signal Logic**:
  - TVL inflows → Positive sentiment → Long bias
  - TVL outflows → Negative sentiment → Short bias

### 2.3 Volume & Liquidity Metrics

#### Volume/Market Cap Ratio
- **Formula**: `Vol/MCap = 24h Volume / Market Cap`
- **Data Sources**:
  - DEX Screener: `/token-pairs/v1/{chain}/{address}`
  - CoinGecko: `/coins/{id}/market_chart`
- **Signal Logic**:
  - High ratio (> 0.5) → High activity → Momentum signal
  - Low ratio (< 0.01) → Illiquid → Avoid or mean-revert

#### Liquidity Depth
- **Formula**: `Depth Score = Sum of order book within ±2% / Market Cap`
- **Data Sources**:
  - DEX Screener: pair liquidity data
  - On-chain: pool reserves via contract calls
- **Signal Logic**:
  - Deep liquidity → Lower slippage → Better for large positions
  - Shallow liquidity → Higher risk → Smaller position sizes

### 2.4 Social Presence Metrics

#### Social Volume
- **Data Sources**:
  - CoinGecko: social links (Twitter, Discord, Telegram)
  - LunarCrush/Santiment (paid): social mentions, sentiment scores
  - Twitter API: mention volume, engagement rates
- **Signal Logic**:
  - Spike in social volume → Potential momentum → Entry signal
  - Declining social interest → Exit signal

#### Social Sentiment
- **Formula**: `Sentiment Score = (Positive Mentions - Negative Mentions) / Total Mentions`
- **Data Sources**:
  - LunarCrush: `galaxy_score`, `social_score`
  - Custom NLP on Twitter/Reddit mentions
- **Signal Logic**:
  - Extreme positive sentiment → Contrarian short signal
  - Extreme negative sentiment → Contrarian long signal
  - Neutral/slightly positive → Trend continuation

### 2.5 Volatility Metrics

#### Realized Volatility
- **Formula**: `RV = Std(Log Returns) * √252`
- **Data Sources**:
  - CoinGecko: `/coins/{id}/ohlc`
  - GMX: `/prices/ohlcv`
  - DEX Screener: OHLCV data
- **Signal Logic**:
  - High RV (> 100% annualized) → Wide grid ranges, larger TP/SL
  - Low RV (< 50% annualized) → Tight ranges, smaller stops

#### Volatility Regime Detection
- **Formula**: `Vol Regime = RV / Rolling_Median(RV, 30d)`
- **Signal Logic**:
  - Regime > 1.5 → High vol regime → Reduce leverage, widen stops
  - Regime < 0.7 → Low vol regime → Potential breakout setup

## 3. Trading Approaches

### 3.1 Liquidity Provider (LP) Strategies

#### Strategy 1: Mean Reversion LP
- **Concept**: Provide liquidity in ranges around fair value based on valuation metrics
- **Entry Criteria**:
  - P/S ratio below sector median
  - Profit margin positive and stable
  - Sufficient volume for fee generation
- **Range Sizing**:
  - Base range: ±10% from current price
  - Adjusted by volatility: `Range = Base ± (Volatility * Multiplier)`
- **Risk Management**:
  - Stop loss: Price exits range by 2x range width
  - Rebalancing: Weekly or when price breaches 50% of range
- **DEX**: Uniswap V3, SushiSwap concentrated liquidity

#### Strategy 2: Growth-Driven LP
- **Concept**: Provide liquidity for protocols with accelerating growth metrics
- **Entry Criteria**:
  - Revenue growth > 20% QoQ
  - TVL increasing
  - Social volume rising
- **Range Sizing**:
  - Asymmetric range: 15% downside, 30% upside (growth bias)
- **Risk Management**:
  - Take profit: Sell LP position when growth decelerates
  - Stop loss: Price drops 20% below entry

### 3.2 Grid Trading Strategies

#### Strategy 1: Volatility-Adaptive Grid
- **Concept**: Grid spacing adapts to current volatility regime
- **Grid Parameters**:
  - Number of grids: 10-20
  - Grid spacing: `ATR(n) * Grid_Multiplier`
  - Upper/Lower bounds: `Price ± (ATR * Bound_Multiplier)`
- **Entry Criteria**:
  - Volatility regime stable (not spiking)
  - Sufficient liquidity for grid execution
- **Risk Management**:
  - Max position size: 5% of portfolio per grid
  - Emergency close: If price breaks bounds by 2x

#### Strategy 2: Volume-Weighted Grid
- **Concept**: More grids at price levels with historical high volume
- **Implementation**:
  - Analyze volume profile from historical data
  - Place more grid levels at high-volume nodes
  - Fewer grids at low-volume areas
- **Data Sources**:
  - DEX Screener historical trades
  - CoinGecko OHLCV with volume

### 3.3 TP/SL (Take Profit/Stop Loss) Strategies

#### Strategy 1: ATR-Based TP/SL
- **Concept**: Dynamic TP/SL levels based on Average True Range
- **Formulas**:
  - `Stop Loss = Entry - (ATR * Stop_Multiplier)`
  - `Take Profit = Entry + (ATR * TP_Multiplier)`
  - Typical multipliers: Stop=2, TP=3 (1.5:1 R:R)
- **Adjustments**:
  - Widen stops in high volatility regimes
  - Tighten stops in low volatility regimes
- **DEX Implementation**:
  - GMX: Native TP/SL order types
  - dYdX: Conditional orders
  - Others: Off-chain keeper monitoring

#### Strategy 2: Metric-Triggered TP/SL
- **Concept**: TP/SL levels adjusted based on fundamental metric changes
- **Take Profit Triggers**:
  - P/S ratio reaches sector median (mean reversion complete)
  - Growth rate decelerates below threshold
  - Social sentiment reaches extreme positive
- **Stop Loss Triggers**:
  - Revenue turns negative
  - TVL drops > 20% in 7 days
  - Social volume collapses > 50%

## 4. DEX-Specific Implementations

### 4.1 Perpetual Futures (GMX, dYdX)

#### GMX Implementation
- **SDK**: `@gmx-io/sdk`
- **Key Functions**:
  ```javascript
  // Open position
  const params = {
    token: collateralToken,
    amount: collateralAmount,
    indexToken: indexToken,
    isLong: true,
    acceptablePrice: currentPrice * 1.01,
    executionFee: gasPrice * 1.5
  };
  await gmxSdk.createIncreasePosition(params);
  
  // Set TP/SL
  await gmxSdk.createOrder({
    orderType: ORDER_TYPE_TP,
    triggerPrice: takeProfitPrice,
    // ... additional params
  });
  ```
- **Data Sources**:
  - Markets info: `https://arbitrum-api.gmxinfra.io/markets/info`
  - Prices: `https://arbitrum-api.gmxinfra.io/prices/ohlcv`

#### dYdX v4 Implementation
- **Endpoints**:
  - Indexer: `https://indexer.dydx.trade/v4`
  - WebSocket: `wss://indexer.dydx.trade/v4/ws`
- **Key Operations**:
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

### 4.2 Options (Deribit)

#### Deribit Implementation
- **API Base**: `https://www.deribit.com/api/v2`
- **Key Methods**:
  ```javascript
  // Get options instruments
  const instruments = await deribit.getInstruments({
    currency: "BTC",
    kind: "option",
    expired: false
  });
  
  // Get option chain
  const ticker = await deribit.ticker({
    instrumentName: "BTC-25APR25-60000-C"
  });
  
  // Place option order
  const order = await deribit.buy({
    instrumentName: "BTC-25APR25-60000-C",
    amount: 1,
    type: "limit",
    price: 0.05
  });
  ```

### 4.3 Spot DEX (Uniswap, SushiSwap)

#### Uniswap V3 Implementation
- **SDK**: `@uniswap/v3-sdk`, `@uniswap/sdk-core`
- **LP Position Management**:
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
    liquidity: liquidityAmount,
    recipient: walletAddress,
    deadline: deadline
  });
  ```

## 5. Implementation Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
├─────────────────────────────────────────────────────────────┤
│  CoinGecko │ DEX Screener │ Token Terminal │ DefiLlama      │
│  Twitter   │ LunarCrush   │ On-chain RPCs                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Feature Engineering                       │
├─────────────────────────────────────────────────────────────┤
│  P/S Ratio │ Growth Metrics │ Volatility │ Social Sentiment │
│  Volume Profile │ Liquidity Depth │ Regime Detection        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Signal Generation                         │
├─────────────────────────────────────────────────────────────┤
│  Mean Reversion │ Momentum │ Sentiment │ Volatility Trading │
│  Multi-factor scoring │ Signal aggregation                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Risk Management                           │
├─────────────────────────────────────────────────────────────┤
│  Position Sizing │ Portfolio Limits │ Drawdown Controls      │
│  Correlation Checks │ Liquidity Filters                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
├─────────────────────────────────────────────────────────────┤
│  GMX SDK │ dYdX Client │ Uniswap SDK │ Deribit API          │
│  Order Routing │ Slippage Protection │ Gas Optimization     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring & Reporting                    │
├─────────────────────────────────────────────────────────────┤
│  P&L Tracking │ Performance Metrics │ Alert System          │
│  Backtesting │ Walk-forward Analysis                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Technology Stack

#### Option A: Python-First
- **Core**: Python 3.11+
- **Data**: pandas, numpy, requests
- **Backtesting**: vectorbt, freqtrade
- **DEX Integration**: web3.py, ccxt
- **Database**: PostgreSQL + TimescaleDB
- **Task Queue**: Celery + Redis
- **Monitoring**: Grafana + Prometheus

#### Option B: TypeScript-First
- **Core**: Node.js 20+ / TypeScript
- **Data**: axios, lodash, date-fns
- **DEX Integration**: ethers.js/viem, Uniswap SDK, GMX SDK
- **Database**: PostgreSQL + Prisma
- **Task Queue**: BullMQ + Redis
- **Monitoring**: Custom dashboard

#### Option C: Hybrid
- **Data Collection**: Python (better data science libraries)
- **Signal Generation**: Python (pandas, numpy)
- **Execution**: TypeScript (better DEX SDK support)
- **Communication**: REST API or message queue

## 6. Risk Management Framework

### 6.1 Position Sizing

#### Fixed Fractional Risk
```python
def calculate_position_size(
    account_balance: float,
    risk_per_trade: float,  # e.g., 0.02 for 2%
    entry_price: float,
    stop_loss_price: float
) -> float:
    risk_amount = account_balance * risk_per_trade
    price_risk = abs(entry_price - stop_loss_price) / entry_price
    return risk_amount / price_risk
```

#### ATR-Based Sizing
```python
def atr_position_size(
    account_balance: float,
    atr: float,
    atr_multiplier: float = 2.0,
    target_risk: float = 0.02
) -> float:
    stop_distance = atr * atr_multiplier
    risk_amount = account_balance * target_risk
    return risk_amount / stop_distance
```

### 6.2 Portfolio Limits

- **Max leverage**: 3x for perps, 1x for spot
- **Max position size**: 10% of portfolio per asset
- **Max sector exposure**: 30% of portfolio
- **Max correlation**: Avoid > 0.7 correlation between positions
- **Max drawdown**: 20% portfolio-wide stop
- **Daily loss limit**: 5% of portfolio

### 6.3 Liquidity Filters

```python
def check_liquidity(
    token_address: str,
    chain: str,
    position_size_usd: float
) -> bool:
    pair_data = get_dex_screener_data(chain, token_address)
    liquidity = pair_data['liquidity']['usd']
    
    # Position should be < 5% of liquidity
    max_position = liquidity * 0.05
    
    # Check slippage for intended size
    expected_slippage = estimate_slippage(position_size_usd, liquidity)
    
    return position_size_usd <= max_position and expected_slippage < 0.02
```

## 7. Backtesting Framework

### 7.1 Data Requirements

- **OHLCV data**: 1-minute to daily resolution
- **On-chain metrics**: Daily snapshots of TVL, volume, fees
- **Social metrics**: Daily aggregated sentiment scores
- **Funding rates**: For perpetuals backtesting
- **Gas costs**: For realistic execution cost modeling

### 7.2 Backtesting Approach

#### Walk-Forward Analysis
```python
def walk_forward_backtest(
    strategy,
    data,
    train_window=90,  # days
    test_window=30,    # days
    step_size=7        # days
):
    results = []
    
    for start in range(0, len(data) - train_window - test_window, step_size):
        train_data = data[start:start + train_window]
        test_data = data[start + train_window:start + train_window + test_window]
        
        # Optimize on train data
        best_params = optimize_strategy(strategy, train_data)
        
        # Test on out-of-sample data
        test_result = run_backtest(strategy, test_data, best_params)
        results.append(test_result)
    
    return aggregate_results(results)
```

### 7.3 Performance Metrics

- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk-adjusted returns
- **Max Drawdown**: Worst peak-to-trough decline
- **Calmar Ratio**: Return / Max Drawdown
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Average R:R**: Average win / Average loss

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up data collection infrastructure
- [ ] Implement metric calculations (P/S, growth, volatility)
- [ ] Create database schema for historical data
- [ ] Build basic signal generation framework

### Phase 2: Strategy Development (Weeks 3-4)
- [ ] Implement mean reversion LP strategy
- [ ] Implement volatility-adaptive grid strategy
- [ ] Implement ATR-based TP/SL strategy
- [ ] Create backtesting framework

### Phase 3: DEX Integration (Weeks 5-6)
- [ ] Integrate GMX SDK for perpetuals
- [ ] Integrate Uniswap V3 SDK for LP
- [ ] Implement order management system
- [ ] Add gas optimization and slippage protection

### Phase 4: Risk & Monitoring (Weeks 7-8)
- [ ] Implement position sizing algorithms
- [ ] Add portfolio-level risk controls
- [ ] Create monitoring dashboard
- [ ] Set up alerting system

### Phase 5: Optimization (Weeks 9-10)
- [ ] Walk-forward optimization
- [ ] Parameter sensitivity analysis
- [ ] Live paper trading
- [ ] Performance attribution analysis

## 9. Key Considerations

### 9.1 Data Quality
- Validate data from multiple sources
- Handle missing data gracefully
- Account for API rate limits
- Cache frequently accessed data

### 9.2 Execution Risks
- Smart contract risks (audits, upgradability)
- Oracle manipulation risks
- Front-running protection
- MEV (Maximal Extractable Value) considerations

### 9.3 Regulatory Considerations
- Jurisdiction-specific restrictions
- KYC/AML requirements for some DEXes
- Tax reporting obligations
- Record keeping for trades

### 9.4 Cost Considerations
- Gas costs for on-chain operations
- API subscription costs (Token Terminal, LunarCrush)
- Infrastructure costs (servers, databases)
- Development and maintenance time

## 10. Next Steps

1. **Choose technology stack** (Python, TypeScript, or Hybrid)
2. **Set up development environment**
3. **Implement data collection for 2-3 key metrics**
4. **Build and backtest one strategy end-to-end**
5. **Paper trade for 2-4 weeks**
6. **Graduate to live trading with small position sizes**

---

*This plan provides a comprehensive framework for building data-driven crypto trading strategies. The key to success will be rigorous backtesting, careful risk management, and continuous monitoring and adaptation.*
