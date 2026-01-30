# Trader Evaluation Metrics: Identifying Skill vs Luck

## Core Principle
**Luck** = Random chance, unpredictable, short-term
**Skill** = Consistent performance over time, measurable, sustainable

## Statistical Metrics (Probability & Statistics)

### 1. Risk-Adjusted Return Metrics

| Metric | Description | Why it matters |
|--------|-------------|----------------|
| Sharpe Ratio | Risk-adjusted returns per unit of risk. Higher = better risk-adjusted performance | Identifies traders who generate returns relative to their risk taken, not just high-risk gamblers |
| Sortino Ratio | Downside risk-adjusted returns. Measures excess return per unit of downside risk. | Penalizes high volatility/downside, favors steady consistent winners |
| Calmar Ratio | Average return divided by standard deviation of returns. Higher = more consistent returns | Measures consistency - high score means steady, predictable performance not volatile ups/downs |
| Maximum Drawdown (MDD) | Largest peak-to-trough decline in account value. Lower = better risk management | Shows how badly a trader can hurt your account before recovering. 20% MDD means at worst point you'd be down 20% from peak |
| VaR (Value at Risk) | Maximum loss at a given confidence level (e.g., 95% VaR) | Quantifies worst-case loss scenario at probability level |
| Beta (vs Market) | Volatility relative to benchmark | Identifies if returns are due to skill or just riding overall market volatility |

### 2. Win Rate & Consistency Metrics

| Metric | Description | Why it matters |
|--------|-------------|----------------|
| Win Rate | Percentage of profitable trades. But needs sample size context | 55% win rate on 10 trades could be luck; 55% on 1000 trades shows consistency |
| Win/Loss Ratio | Average profit divided by average loss | Ratio > 1 shows profitable strategies that work over time |
| Average Holding Time | How long positions are held (longer = conviction, shorter = scalping/gambling) | Distinguishes conviction-based trading from quick flips |
| Monthly ROI | Monthly return percentage | Shows sustainable performance over time, not just one lucky month |
| Rolling Returns (30/60/90 day) | Returns over different time windows | Identifies if performance is consistent across different market conditions |

### 3. Volume & Activity Metrics

| Metric | Description | Why it matters |
|--------|-------------|----------------|
| Total Trades | Total number of trades executed | High volume with low win rate = gambling; moderate volume with high win rate = skill |
| Trading Volume (USD) | Total notional value traded | Shows if trader has actual market impact and scale |
| Return on Account (ROA) | Percentage of profit relative to average account balance | Measures capital efficiency and sustainability |
| Return on Equity (ROE) | Profit/loss relative to total equity invested | True measure of how much money made, not just percentages |
| Profit Factor | Total profit / Total loss | Must be > 1 for long-term success | Shows ability to compound wins and minimize losses |

### 4. Statistical Significance Metrics

| Metric | Description | Why it matters |
|--------|-------------|----------------|
| Standard Deviation of Returns | Volatility of trader's PnL over time | Low SD = more predictable and consistent strategy |
| T-Test / P-Value | Statistical test if returns are statistically significant (not random) | P < 0.05 suggests skill, not random chance |
| Correlation with Market | How closely trader follows market trends | Positive correlation > 0.5 could mean just riding market (less skill) |
| Z-Score | How many standard deviations above/below mean performance | Consistently positive over time = skill |

### Red Flags: Signs of Luck vs Risk-Taking

1. **High leverage with small account** - Using 50x leverage on a $1000 account suggests gambling
2. **Short holding periods** - Holding positions for < 1 hour suggests scalping/gambling
3. **High win rate but low average profit** - Could be many small wins but a few big losses
4. **Inconsistent performance across timeframes** - Good one month, terrible next month = luck
5. **Lack of transparency in strategy** - Trader won't explain edge or methodology
6. **Changing strategy frequently** - Adapting to recent market conditions without a system = less skill
7. **Concentrated positions** - All profit from one trade or asset = fragile, not sustainable

### Notes:
- **Look for track record of 6+ months minimum** - Anything less is likely luck/variance
- **Prioritize risk-adjusted metrics over raw returns** - A 100% ROI achieved with 50% MDD is dangerous
- **Consistency beats intensity** - Steady 30% annual return with 5% MDD > volatile 200% return with 50% MDD
- **Beware of survivorship bias** - Only looking at profitable traders ignores those who blew up
