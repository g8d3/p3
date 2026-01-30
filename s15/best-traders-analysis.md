# Best Traders Analysis - Hyperliquid (Skill-Based Metrics)

## Data Source: Hyperliquid Leaderboard
- URL: https://app.hyperliquid.xyz/leaderboard
- Timestamp: 2026-01-29
- Time Window: All-time (excludes accounts < $100k account value or < $10M volume)

## Methodology
Using statistical metrics from `trader-evaluation-metrics.md` to distinguish skill vs luck:

**High Skill Indicators**:
- High Sharpe Ratio (> 2.0) - Risk-adjusted performance
- Low Max Drawdown (< 30%) - Risk management
- High Win Rate (> 55%) - Consistency with sufficient sample size
- Stable ROI across timeframes - Not just one lucky month
- High Volume with moderate leverage - Not gambling with small account

**Luck Indicators**:
- Extreme ROI with tiny account value (e.g., 3000% ROI with $2 balance)
- Low sample size (< 100 trades)
- High leverage use on small accounts
- Volatile performance across months

## Top Traders Table (Hyperliquid)

| Rank | Trader Name | Wallet | Account Value | PNL (All-time) | ROI (All-time) | Volume (All-time) | Risk Assessment | Recommendation |
|-------|--------------|--------|----------------|------------------|------------------|---------------------|------------------|----------------|
| 1 | 0xecb6...2b00 | 0xecb6...2b00 | $95,810,789.60 | $178,242,770.45 | 176.59% | $216,695,998,822.59 | **High Risk** - Extreme ROI with small account, likely luck or high-leverage gambling | Caution - Need detailed risk metrics |
| 2 | 0x5b5d...c060 | 0x5b5d...c060 | $81,195,089.91 | $168,437,361.61 | 52.09% | $3,718,475,331.58 | **Moderate Risk** - Moderate ROI with significant volume, potential skill | Moderate - Needs Sharpe/DD verification |
| 3 | thank you jefef | - | $9,128,411.93 | $152,460,198.72 | 3,545.97% | $4,655,922.47 | **Very High Risk** - Extreme ROI with relatively small account | High Risk - Probably luck/gambling |
| 4 | BobbyBigSize | - | $38,219,216.48 | $145,391,719.51 | 235.45% | $9,912,870,641.46 | **High Risk** - High ROI with substantial account size | High Risk - Needs detailed analysis |
| 5 | 0x9794...333b | 0x9794...333b | $1,361.44 | $144,134,548.29 | 758.66% | **Very High Risk** - Extreme ROI with tiny account ($1,361) | Very High Risk - Avoid or small allocation |
| 6 | 0xb83d...6e36 | 0xb83d...6e36 | $43,016,326.90 | $119,746,605.81 | 84.40% | $3,334,568,053.79 | **Moderate Risk** - Solid volume with reasonable ROI | Moderate - Needs detailed metrics |
| 7 | 0x2ea1...23f4 | 0x2ea1...23f4 | $2.37 | $106,341,324.52 | 673.35% | $2,139,884,917.17 | **Very High Risk** - Extreme ROI with almost no account ($2.37) | Very High Risk - Avoid - likely pump/dump |
| 8 | x.com/SilkBtc | - | $42,990,166.99 | $98,794,885.07 | 141.43% | $5,932,561,946.49 | **High Risk** - High ROI with large account | Moderate-High Risk - Needs Sharpe/DD |
| 9 | 0xbde2...60b1 | 0xbde2...60b1 | $1.01 | $97,508,580.88 | 4,332.81% | $25,191,221.12 | **Extreme Risk** - Impossible ROI with tiny account | Extreme Risk - Likely error or manipulation |
| 10 | 0xa312...ad1e | 0xa312...ad1e | $12,855,690.52 | $92,950,978.83 | 323.79% | $992,305,365.80 | **High Risk** - High ROI with moderate account | High Risk - Needs detailed verification |

## Detailed Metrics Available on Hyperdash

To properly evaluate skill vs luck, the following metrics from `trader-evaluation-metrics.md` are needed:

| Metric | Description | Why it Matters |
|---------|-------------|-----------------|
| **Sharpe Ratio** | Risk-adjusted returns per unit of risk | Identifies traders who generate consistent returns vs volatility |
| **Sortino Ratio** | Downside risk-adjusted returns | Penalizes high volatility/downside, favors steady winners |
| **Max Drawdown (MDD)** | Largest peak-to-trough decline in % | Shows worst-case scenario trader experienced |
| **Win Rate** | Percentage of profitable trades | Needs sample size context (100 trades > 50 trades) |
| **Rolling 30/60/90 Day Returns** | Performance across different timeframes | Identifies consistency across market conditions |
| **Standard Deviation of Returns** | Volatility of trader's PnL | Low SD = more predictable, consistent strategy |
| **Monthly ROI** | Average monthly return percentage | Shows sustainable performance over time |
| **Profit Factor** | Total profit / Total loss | Must be > 1 for long-term success |
| **Beta vs Market** | Correlation with overall market trends | High correlation (>0.5) could mean just riding market (less skill) |

## Missing Data from Hyperliquid Leaderboard

The Hyperliquid leaderboard **does NOT provide** critical skill metrics:
- ❌ Win Rate
- ❌ Sharpe Ratio / Sortino Ratio
- ❌ Max Drawdown
- ❌ Total number of trades
- ❌ Monthly/breakdown returns
- ❌ Standard deviation of returns
- ❌ Average holding time per trade

Without these metrics, **ROI alone is insufficient** to distinguish skill from luck. A trader could have:
- 3000% ROI with 2 successful trades (gambling, not skill)
- 50% ROI with 1000 trades showing steady consistent performance (skill)

## Next Steps for Proper Evaluation

1. **Visit Hyperdash** (https://hyperdash.com/explore/global) for detailed trader analytics
2. **Extract detailed metrics** for top 10-20 traders including:
   - Sharpe Ratio (30D, 90D, 180D)
   - Max Drawdown
   - Win Rate (with trade count)
   - Rolling returns (30d, 60d, 90d)
   - Profit factor
   - Standard deviation
3. **Filter by skill indicators**:
   - Sharpe > 2.0 (minimum)
   - Max Drawdown < 30%
   - Win Rate > 55% with > 100 trades
   - Rolling ROI consistency (positive across all timeframes)
4. **Risk assessment**: Assign risk score based on combination of metrics

## Quick Assessment: Trader #2 (0x5b5d...c060)

**Why potentially skilled**:
- ROI: 52.09% - Strong but not astronomical
- Volume: $3.7B - Shows substantial market participation
- Account Value: $81M - Large enough to support sophisticated strategies

**What we need to verify**:
- Sharpe Ratio: Is risk-adjusted performance solid?
- Max Drawdown: Did they experience >30% drops?
- Win Rate: Is it consistently >55%?
- Monthly breakdown: Or was ROI concentrated in one lucky month?

## Quick Assessment: Trader #6 (0xb83d...6e36)

**Why potentially skilled**:
- ROI: 84.40% - Strong performance
- Volume: $3.3B - Excellent market participation
- Account Value: $43M - Substantial capital base

**What we need to verify**:
- Sharpe Ratio: Is the high ROI achieved with moderate volatility?
- Win Rate: Consistent or volatile?
- Max Drawdown: Did they manage risk well?

## Traders to Avoid (Luck-Based)

Based on available data, these traders show red flags:

1. **Trader #5** (0x9794...333b) - 758.66% ROI with only $1,361 account
   - Extreme leverage or one lucky trade
   - Not sustainable or replicable
   
2. **Trader #7** (0x2ea1...23f4) - 673.35% ROI with $2.37 account
   - Impossible math - likely data error or manipulation
   
3. **Trader #9** (0xbde2...60b1) - 4,332.81% ROI with $1.01 account
   - Clearly error or anomaly, avoid

## Summary

**Current Status**: Incomplete evaluation - Hyperliquid leaderboard lacks skill metrics
**Next Required Action**: Extract detailed metrics from Hyperdash to properly assess:
1. Sharpe Ratio
2. Max Drawdown
3. Win Rate (with trade count)
4. Rolling returns
5. Profit factor

**File Updated**: 2026-01-29
