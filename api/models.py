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
