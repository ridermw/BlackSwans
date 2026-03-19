"""Pydantic models for API request/response schemas."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"


class TickerInfo(BaseModel):
    """Information about available ticker."""
    ticker_code: str = Field(..., description="Ticker symbol (e.g., 'sp500', 'nikkei')")
    ticker_symbol: str = Field(..., description="Yahoo Finance symbol (e.g., '^GSPC')")
    data_file: str = Field(..., description="Path to CSV data file")
    start_date: str = Field(..., description="Start date of available data")
    end_date: str = Field(..., description="End date of available data")


class TickersResponse(BaseModel):
    """List of available tickers."""
    tickers: List[TickerInfo]


class OutlierStatsResponse(BaseModel):
    """Outlier statistics for a quantile threshold."""
    quantile: float
    threshold_low: float
    threshold_high: float
    count_low: int
    count_high: int
    mean_low: float
    mean_high: float
    median_low: float
    median_high: float
    std_low: float
    std_high: float
    min_low: float
    max_high: float


class ScenarioResult(BaseModel):
    """Return scenario analysis result."""
    scenario: str
    annualized_return: float


class RegimePerformance(BaseModel):
    """Performance metrics by market regime."""
    regime: str
    trading_days: int
    mean_return: float
    std_return: float
    annualized_return: float
    sharpe_ratio: float


class AnalysisResponse(BaseModel):
    """Complete analysis results for a ticker."""
    ticker: str
    start_date: str
    end_date: str
    n_trading_days: int
    outlier_stats: List[OutlierStatsResponse]
    scenarios: List[ScenarioResult]
    regime_performance: List[RegimePerformance]


class ClaimVerdict(BaseModel):
    """Verdict for a single claim."""
    claim_name: str
    verdict: str
    p_value: Optional[float] = None
    details: Dict[str, Any] = {}


class ValidationResponse(BaseModel):
    """Full validation results for all 4 claims."""
    ticker: str
    period: str
    n_trading_days: int
    claims: Dict[str, str]
    claim_details: List[ClaimVerdict]


class ReturnDataPoint(BaseModel):
    """Single day's return with metadata."""
    date: str
    ret: float
    is_outlier: bool
    regime: Optional[int] = None


class HistogramBin(BaseModel):
    """Histogram bin data."""
    bin_center: float
    count: int
    normal_expected: float


class ChartDataResponse(BaseModel):
    """Chart-ready data for frontend visualization."""
    ticker: str
    start_date: str
    end_date: str
    n_trading_days: int
    returns: List[ReturnDataPoint]
    histogram: List[HistogramBin]
    scenario_impacts: Dict[str, float]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# v0.3: Period comparison and multi-index models
# ──────────────────────────────────────────────────────────────


class ClaimResult(BaseModel):
    """Result of a single claim check for a period."""
    verdict: str
    metrics: Dict[str, Any] = {}


class PeriodResult(BaseModel):
    """Claim results for a single time period."""
    period: str
    period_label: str
    n_trading_days: int
    start_date: str
    end_date: str
    fat_tails: ClaimResult
    outsized_influence: ClaimResult
    clustering: ClaimResult
    trend_following: ClaimResult


class PeriodComparisonResponse(BaseModel):
    """Side-by-side claim results for pre/post/full periods."""
    ticker: str
    split_date: str
    periods: List[PeriodResult]


class CagrRow(BaseModel):
    """CAGR scenario for a single period."""
    period: str
    period_label: str
    n_trading_days: int
    start_date: str
    end_date: str
    n_days_removed: int
    cagr_all: float
    cagr_miss_best: float
    cagr_miss_worst: float
    cagr_miss_both: float = Field(description="CAGR excluding both best and worst N days")
    impact_miss_best: float
    impact_miss_worst: float
    impact_miss_both: float = Field(description="CAGR impact of missing both best and worst N days")


class CagrMatrixResponse(BaseModel):
    """CAGR scenario matrix across periods."""
    ticker: str
    split_date: str
    n_days: int
    rows: List[CagrRow]


class IndexSummary(BaseModel):
    """Summary of one index across periods."""
    ticker: str
    name: str
    n_trading_days: int
    start_date: str
    end_date: str
    cagr_full: float
    cagr_pre: Optional[float] = None
    cagr_post: Optional[float] = None
    kurtosis_full: float
    clustering_pct_full: Optional[float] = None
    tf_max_drawdown: Optional[float] = None
    bh_max_drawdown: Optional[float] = None


class MultiIndexResponse(BaseModel):
    """Comparison across all indices."""
    split_date: str
    indices: List[IndexSummary]
