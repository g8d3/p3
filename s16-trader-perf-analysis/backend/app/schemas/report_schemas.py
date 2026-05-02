from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ReportFormat(str, Enum):
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


class ReportRequest(BaseModel):
    trader_address: str = Field(..., description="Hyperliquid trader address")
    format: ReportFormat = Field(ReportFormat.HTML, description="Report format")
    include_charts: bool = Field(True, description="Include charts in the report")
    date_from: Optional[datetime] = Field(None, description="Start date for analysis")
    date_to: Optional[datetime] = Field(None, description="End date for analysis")


class ReportMetadata(BaseModel):
    report_id: str
    trader_address: str
    format: ReportFormat
    created_at: datetime
    size_bytes: int
    data_period_start: Optional[datetime]
    data_period_end: Optional[datetime]
    total_trades: int
    total_volume: float


class ExecutiveSummary(BaseModel):
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    account_value: float
    margin_usage_pct: float


class TraderOverview(BaseModel):
    address: str
    account_value: float
    margin_used: float
    margin_available: float
    margin_usage_pct: float
    liquidation_price: Optional[float]
    last_updated: datetime


class PerformanceOverview(BaseModel):
    total_return_pct: float
    annualized_return_pct: float
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    recovery_time_days: Optional[int]
    calmar_ratio: float


class ReturnMetrics(BaseModel):
    total_return_pct: float
    annualized_return_pct: float
    monthly_returns: Dict[str, float]
    quarterly_returns: Dict[str, float]
    yearly_returns: Dict[str, float]
    best_month_pct: float
    worst_month_pct: float
    positive_months: int
    negative_months: int


class RiskMetrics(BaseModel):
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    value_at_risk_95_pct: float
    expected_shortfall_95_pct: float
    beta: Optional[float]
    correlation_with_market: Optional[float]


class TradingStatistics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    largest_win_pct: float
    largest_loss_pct: float
    profit_factor: float
    avg_trade_duration_hours: float
    avg_holding_period_days: float


class PositionAnalysis(BaseModel):
    avg_leverage: float
    max_leverage: float
    position_concentration: float
    top_positions: List[Dict[str, Any]]
    sector_exposure: Dict[str, float]
    asset_turnover: float
    portfolio_turnover: float


class FundingImpact(BaseModel):
    total_funding_paid: float
    total_funding_received: float
    net_funding_cost: float
    funding_cost_pct_of_returns: float
    avg_funding_rate: float
    funding_impact_on_performance: float


class TradeHistorySummary(BaseModel):
    total_trades: int
    total_volume: float
    avg_trade_size: float
    trade_frequency_per_day: float
    most_traded_assets: List[Dict[str, Any]]
    trade_type_distribution: Dict[str, int]
    time_distribution: Dict[str, int]


class TimeSeriesAnalysis(BaseModel):
    cumulative_returns: List[Dict[str, float]]
    drawdown_series: List[Dict[str, float]]
    rolling_sharpe: List[Dict[str, float]]
    rolling_volatility: List[Dict[str, float]]


class Recommendations(BaseModel):
    risk_assessment: str
    performance_rating: str
    suggestions: List[str]
    warnings: List[str]


class ReportData(BaseModel):
    metadata: ReportMetadata
    executive_summary: ExecutiveSummary
    trader_overview: TraderOverview
    performance_overview: PerformanceOverview
    return_metrics: ReturnMetrics
    risk_metrics: RiskMetrics
    trading_statistics: TradingStatistics
    position_analysis: PositionAnalysis
    funding_impact: FundingImpact
    trade_history_summary: TradeHistorySummary
    time_series_analysis: TimeSeriesAnalysis
    recommendations: Recommendations
    charts: Optional[Dict[str, str]] = None  # Base64 encoded chart images


class ReportResponse(BaseModel):
    report_id: str
    status: str
    format: ReportFormat
    download_url: Optional[str] = None
    created_at: datetime
    size_bytes: Optional[int] = None


class ReportListItem(BaseModel):
    report_id: str
    format: ReportFormat
    created_at: datetime
    size_bytes: int
    data_period_start: Optional[datetime]
    data_period_end: Optional[datetime]