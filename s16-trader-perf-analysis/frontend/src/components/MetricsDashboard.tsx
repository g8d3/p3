import React from 'react';
import { Card, CardContent, Typography, Grid, Box, LinearProgress } from '@mui/material';
import {
  PerformanceOverview,
  ReturnMetrics,
  RiskMetrics,
  TradingStatistics
} from '../types';
import { formatPercentage, formatNumber } from '../utils/formatters';

interface MetricsDashboardProps {
  performance: PerformanceOverview;
  returns: ReturnMetrics;
  risk: RiskMetrics;
  trading: TradingStatistics;
  loading?: boolean;
}

const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  performance,
  returns,
  risk,
  trading,
  loading = false
}) => {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">Loading metrics...</Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  const MetricCard: React.FC<{ title: string; value: string; subtitle?: string }> = ({
    title,
    value,
    subtitle
  }) => (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h5" component="div">
          {value}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Key Metrics Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Performance Overview */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Performance Overview
          </Typography>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Return"
            value={formatPercentage(performance.total_return_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Annualized Return"
            value={formatPercentage(performance.annualized_return_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Sharpe Ratio"
            value={formatNumber(performance.sharpe_ratio, 2)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Max Drawdown"
            value={formatPercentage(performance.max_drawdown_pct)}
          />
        </Grid>

        {/* Risk Metrics */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Risk Metrics
          </Typography>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Volatility"
            value={formatPercentage(risk.volatility_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Value at Risk (95%)"
            value={formatPercentage(risk.value_at_risk_95_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Sortino Ratio"
            value={formatNumber(risk.sortino_ratio, 2)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Expected Shortfall (95%)"
            value={formatPercentage(risk.expected_shortfall_95_pct)}
          />
        </Grid>

        {/* Trading Statistics */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Trading Statistics
          </Typography>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Trades"
            value={formatNumber(trading.total_trades)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Win Rate"
            value={formatPercentage(trading.win_rate_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Profit Factor"
            value={formatNumber(trading.profit_factor, 2)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Trade Duration"
            value={`${formatNumber(trading.avg_trade_duration_hours, 1)}h`}
          />
        </Grid>

        {/* Return Metrics */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Return Metrics
          </Typography>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Best Month"
            value={formatPercentage(returns.best_month_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Worst Month"
            value={formatPercentage(returns.worst_month_pct)}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Positive Months"
            value={`${returns.positive_months}/${returns.positive_months + returns.negative_months}`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Monthly Return"
            value={formatPercentage(
              Object.values(returns.monthly_returns).reduce((a, b) => a + b, 0) /
              Object.values(returns.monthly_returns).length
            )}
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default MetricsDashboard;