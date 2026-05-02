// Types based on backend schemas

export enum ReportFormat {
  HTML = 'html',
  PDF = 'pdf',
  JSON = 'json',
}

export interface ReportRequest {
  trader_address: string;
  format?: ReportFormat;
  include_charts?: boolean;
  date_from?: string; // ISO date string
  date_to?: string; // ISO date string
}

export interface ReportMetadata {
  report_id: string;
  trader_address: string;
  format: ReportFormat;
  created_at: string; // ISO date string
  size_bytes: number;
  data_period_start?: string;
  data_period_end?: string;
  total_trades: number;
  total_volume: number;
}

export interface ExecutiveSummary {
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  profit_factor: number;
  total_trades: number;
  account_value: number;
  margin_usage_pct: number;
}

export interface TraderOverview {
  address: string;
  account_value: number;
  margin_used: number;
  margin_available: number;
  margin_usage_pct: number;
  liquidation_price?: number;
  last_updated: string;
}

export interface PerformanceOverview {
  total_return_pct: number;
  annualized_return_pct: number;
  volatility_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  recovery_time_days?: number;
  calmar_ratio: number;
}

export interface ReturnMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  monthly_returns: Record<string, number>;
  quarterly_returns: Record<string, number>;
  yearly_returns: Record<string, number>;
  best_month_pct: number;
  worst_month_pct: number;
  positive_months: number;
  negative_months: number;
}

export interface RiskMetrics {
  volatility_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  value_at_risk_95_pct: number;
  expected_shortfall_95_pct: number;
  beta?: number;
  correlation_with_market?: number;
}

export interface TradingStatistics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  largest_win_pct: number;
  largest_loss_pct: number;
  profit_factor: number;
  avg_trade_duration_hours: number;
  avg_holding_period_days: number;
}

export interface PositionAnalysis {
  avg_leverage: number;
  max_leverage: number;
  position_concentration: number;
  top_positions: Array<Record<string, any>>;
  sector_exposure: Record<string, number>;
  asset_turnover: number;
  portfolio_turnover: number;
}

export interface FundingImpact {
  total_funding_paid: number;
  total_funding_received: number;
  net_funding_cost: number;
  funding_cost_pct_of_returns: number;
  avg_funding_rate: number;
  funding_impact_on_performance: number;
}

export interface TradeHistorySummary {
  total_trades: number;
  total_volume: number;
  avg_trade_size: number;
  trade_frequency_per_day: number;
  most_traded_assets: Array<Record<string, any>>;
  trade_type_distribution: Record<string, number>;
  time_distribution: Record<string, number>;
}

export interface TimeSeriesAnalysis {
  cumulative_returns: Array<Record<string, number>>;
  drawdown_series: Array<Record<string, number>>;
  rolling_sharpe: Array<Record<string, number>>;
  rolling_volatility: Array<Record<string, number>>;
}

export interface Recommendations {
  risk_assessment: string;
  performance_rating: string;
  suggestions: string[];
  warnings: string[];
}

export interface ReportData {
  metadata: ReportMetadata;
  executive_summary: ExecutiveSummary;
  trader_overview: TraderOverview;
  performance_overview: PerformanceOverview;
  return_metrics: ReturnMetrics;
  risk_metrics: RiskMetrics;
  trading_statistics: TradingStatistics;
  position_analysis: PositionAnalysis;
  funding_impact: FundingImpact;
  trade_history_summary: TradeHistorySummary;
  time_series_analysis: TimeSeriesAnalysis;
  recommendations: Recommendations;
  charts?: Record<string, string>; // Base64 encoded
}

export interface ReportResponse {
  report_id: string;
  status: string;
  format: ReportFormat;
  download_url?: string;
  created_at: string;
  size_bytes?: number;
}

export interface ReportListItem {
  report_id: string;
  format: ReportFormat;
  created_at: string;
  size_bytes: number;
  data_period_start?: string;
  data_period_end?: string;
}

// Additional types for trader endpoints
export interface Trade {
  id: string;
  timestamp: string;
  asset: string;
  side: 'BUY' | 'SELL';
  price: number;
  size: number;
  starting_position: number;
  closed_pnl: number;
  fees: number;
  tx_hash: string;
  leverage: number;
}

export interface Position {
  asset: string;
  size: number;
  entry_price: number;
  mark_price: number;
  liquidation_price: number;
  leverage: number;
  margin_used: number;
  unrealized_pnl: number;
  roe: number;
  timestamp: string;
}

export interface Funding {
  timestamp: string;
  asset: string;
  amount: number;
  rate: number;
}

// API Error types
export interface ApiError {
  message: string;
  status: number;
  details?: any;
}