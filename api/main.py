"""FastAPI backend for BlackSwans market outlier analysis."""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

from blackswans.data.loaders import fetch_price_data
from blackswans.data.transforms import compute_daily_returns
from blackswans.analysis.outliers import calculate_outlier_stats
from blackswans.analysis.scenarios import scenario_returns, annualised_return
from blackswans.analysis.regimes import (
    moving_average_regime,
    regime_performance,
)
from blackswans.validate_claims import run_full_validation

from .models import (
    HealthResponse,
    TickerInfo,
    TickersResponse,
    OutlierStatsResponse,
    ScenarioResult,
    RegimePerformance,
    AnalysisResponse,
    ValidationResponse,
    ClaimVerdict,
    ChartDataResponse,
    ReturnDataPoint,
    HistogramBin,
    ErrorResponse,
)

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BlackSwans API",
    description="API for validating Faber's market outlier analysis",
    version="0.2.0",
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ticker mapping: code -> (yahoo_symbol, csv_filename)
TICKER_MAP = {
    "sp500": ("^GSPC", "_GSPC_1928-09-01_to_2010-12-31.csv"),
    "nikkei": ("^N225", "_N225_1970-01-01_to_2010-12-31.csv"),
    "ftse": ("^FTSE", "_FTSE_1970-01-01_to_2010-12-31.csv"),
    "dax": ("^GDAXI", "_GDAXI_1970-01-01_to_2010-12-31.csv"),
    "cac": ("^FCHI", "_FCHI_1970-01-01_to_2010-12-31.csv"),
    "asx": ("^AXJO", "_AXJO_1970-01-01_to_2010-12-31.csv"),
    "tsx": ("^GSPTSE", "_GSPTSE_1970-01-01_to_2010-12-31.csv"),
    "hsi": ("^HSI", "_HSI_1970-01-01_to_2010-12-31.csv"),
    "efa": ("EFA", "EFA_1970-01-01_to_2010-12-31.csv"),
    "eem": ("EEM", "EEM_1988-01-01_to_2010-12-31.csv"),
    "reit": ("VNQ", "VNQ_1970-01-01_to_2010-12-31.csv"),
    "bonds": ("AGG", "AGG_1976-01-01_to_2010-12-31.csv"),
}

DATA_DIR = Path(__file__).parent.parent / "data"


def get_ticker_info(ticker_code: str) -> TickerInfo:
    """Get ticker information from the mapping."""
    if ticker_code not in TICKER_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker_code}' not found. Available: {list(TICKER_MAP.keys())}",
        )

    symbol, filename = TICKER_MAP[ticker_code]
    filepath = DATA_DIR / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found: {filepath}",
        )

    # Parse dates from filename
    parts = filename.replace(".csv", "").split("_")
    start_date = parts[-3]
    end_date = parts[-1]

    return TickerInfo(
        ticker_code=ticker_code,
        ticker_symbol=symbol,
        data_file=str(filepath),
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/api/tickers", response_model=TickersResponse)
async def list_tickers():
    """List all available tickers with their data files."""
    tickers = []
    for code in TICKER_MAP.keys():
        try:
            info = get_ticker_info(code)
            tickers.append(info)
        except HTTPException:
            # Skip tickers with missing data files
            continue

    return TickersResponse(tickers=tickers)


@app.get("/api/analysis/{ticker}", response_model=AnalysisResponse)
async def run_analysis(
    ticker: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    ma_window: int = Query(200, ge=10, le=500, description="Moving average window"),
    quantiles: Optional[str] = Query("0.99,0.999", description="Comma-separated quantiles"),
):
    """Run outlier analysis for a ticker."""
    try:
        # Get ticker info and data file
        ticker_info = get_ticker_info(ticker)
        csv_path = ticker_info.data_file
        symbol = ticker_info.ticker_symbol

        # Use file's date range if not provided
        if start is None:
            start = ticker_info.start_date
        if end is None:
            end = ticker_info.end_date

        # Parse quantiles
        quantile_list = [float(q.strip()) for q in quantiles.split(",")]

        logger.info(f"Loading data for {ticker} ({symbol}): {start} to {end}")
        prices_df = fetch_price_data(symbol, start, end, csv_path=csv_path)
        prices = prices_df["Close"]
        returns = compute_daily_returns(prices)

        # Calculate outlier stats for each quantile
        outlier_stats = []
        for q in quantile_list:
            stats = calculate_outlier_stats(returns, q)
            outlier_stats.append(OutlierStatsResponse(
                quantile=stats.quantile,
                threshold_low=stats.threshold_low,
                threshold_high=stats.threshold_high,
                count_low=stats.count_low,
                count_high=stats.count_high,
                mean_low=stats.mean_low,
                mean_high=stats.mean_high,
                median_low=stats.median_low,
                median_high=stats.median_high,
                std_low=stats.std_low,
                std_high=stats.std_high,
                min_low=stats.min_low,
                max_high=stats.max_high,
            ))

        # Scenario analysis (missing best/worst 10 days)
        full_ret, miss_best, miss_worst, miss_both = scenario_returns(returns, 10, 10)
        scenarios = [
            ScenarioResult(scenario="all_days", annualized_return=annualised_return(full_ret)),
            ScenarioResult(scenario="miss_best_10", annualized_return=annualised_return(miss_best)),
            ScenarioResult(scenario="miss_worst_10", annualized_return=annualised_return(miss_worst)),
            ScenarioResult(scenario="miss_both_10", annualized_return=annualised_return(miss_both)),
        ]

        # Regime analysis
        regimes = moving_average_regime(prices, ma_window)
        regime_df = regime_performance(returns, regimes)
        regime_list = [
            RegimePerformance(
                regime=row["regime"],
                trading_days=int(row["count"]),
                mean_return=float(row["mean"]),
                std_return=float(row["std"]),
                annualized_return=float(row["annualised_return"]),
                sharpe_ratio=float(row["mean"] / row["std"] * np.sqrt(252) if row["std"] > 0 else 0.0),
            )
            for _, row in regime_df.iterrows()
        ]

        return AnalysisResponse(
            ticker=ticker,
            start_date=start,
            end_date=end,
            n_trading_days=len(returns),
            outlier_stats=outlier_stats,
            scenarios=scenarios,
            regime_performance=regime_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/validation/{ticker}", response_model=ValidationResponse)
async def run_validation(
    ticker: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Run full validation of Faber's 4 claims for a ticker."""
    try:
        # Get ticker info and data file
        ticker_info = get_ticker_info(ticker)
        csv_path = ticker_info.data_file
        symbol = ticker_info.ticker_symbol

        # Use file's date range if not provided
        if start is None:
            start = ticker_info.start_date
        if end is None:
            end = ticker_info.end_date

        logger.info(f"Running validation for {ticker} ({symbol}): {start} to {end}")

        # Run full validation (creates output directory but we ignore it)
        summary = run_full_validation(
            csv_path=csv_path,
            ticker=symbol,
            start=start,
            end=end,
            output_dir=f"output/api_validation_{ticker}",
        )

        # Format claim details
        claim_details = []
        for claim_num in range(1, 5):
            claim_key = f"claim{claim_num}"
            claim_data = summary["details"].get(claim_key, {})

            # Extract p-value if available
            p_value = None
            if "jb_p_value" in claim_data:
                p_value = claim_data["jb_p_value"]
            elif "main_case_p_value" in claim_data:
                p_value = claim_data["main_case_p_value"]

            claim_details.append(ClaimVerdict(
                claim_name=claim_data.get("claim", f"Claim {claim_num}"),
                verdict=claim_data.get("verdict", "UNKNOWN"),
                p_value=p_value,
                details=claim_data,
            ))

        return ValidationResponse(
            ticker=ticker,
            period=summary["period"],
            n_trading_days=summary["n_trading_days"],
            claims=summary["claims"],
            claim_details=claim_details,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chart-data/{ticker}", response_model=ChartDataResponse)
async def get_chart_data(
    ticker: str,
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    ma_window: int = Query(200, ge=10, le=500, description="Moving average window"),
    quantile: float = Query(0.99, ge=0.9, le=0.9999, description="Outlier quantile threshold"),
):
    """Return chart-ready data: daily returns with outlier flags and regime labels."""
    try:
        ticker_info = get_ticker_info(ticker)
        csv_path = ticker_info.data_file
        symbol = ticker_info.ticker_symbol

        if start is None:
            start = ticker_info.start_date
        if end is None:
            end = ticker_info.end_date

        prices_df = fetch_price_data(symbol, start, end, csv_path=csv_path)
        prices = prices_df["Close"]
        returns = compute_daily_returns(prices)

        # Outlier thresholds
        threshold_low = float(returns.quantile(1 - quantile))
        threshold_high = float(returns.quantile(quantile))

        # Regime classification
        regimes = moving_average_regime(prices, ma_window)

        # Build per-day data, downsampled for performance.
        # Always include outlier days so they're visible in charts.
        outlier_mask = (returns <= threshold_low) | (returns >= threshold_high)
        outlier_indices = returns.index[outlier_mask]
        regular_indices = returns.index[~outlier_mask]
        step = max(1, len(regular_indices) // 4500)
        sampled_regular = regular_indices[::step]
        sampled_idx = outlier_indices.union(sampled_regular).sort_values()

        data_points = []
        for dt in sampled_idx:
            r = float(returns.loc[dt])
            is_outlier = r <= threshold_low or r >= threshold_high
            regime_val = None
            if dt in regimes.index and not pd.isna(regimes.loc[dt]):
                regime_val = int(regimes.loc[dt])
            data_points.append(ReturnDataPoint(
                date=dt.strftime("%Y-%m-%d"),
                ret=r,
                is_outlier=is_outlier,
                regime=regime_val,
            ))

        # Histogram data
        clean = returns.dropna()
        counts, bin_edges = np.histogram(clean * 100, bins=80)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        mu = float(clean.mean() * 100)
        sigma = float(clean.std() * 100)
        bin_width = float(bin_edges[1] - bin_edges[0])
        normal_expected = [
            float(len(clean) * bin_width * np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi)))
            for x in bin_centers
        ]

        histogram = [
            HistogramBin(bin_center=float(bc), count=int(c), normal_expected=float(ne))
            for bc, c, ne in zip(bin_centers, counts, normal_expected)
        ]

        # Scenario impacts for multiple N values
        baseline_cagr = annualised_return(returns)
        scenario_impacts = {}
        for n_days in [5, 10, 20, 50]:
            _, miss_best, _, _ = scenario_returns(returns, n_days, n_days)
            impact = baseline_cagr - annualised_return(miss_best)
            scenario_impacts[str(n_days)] = float(impact * 100)  # as percentage points

        return ChartDataResponse(
            ticker=ticker,
            start_date=start,
            end_date=end,
            n_trading_days=len(returns),
            returns=data_points,
            histogram=histogram,
            scenario_impacts=scenario_impacts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chart data failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
