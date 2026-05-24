#!/usr/bin/env python3
"""Pre-compute static JSON files for all tickers.

Generates the same response shapes as the FastAPI backend so the frontend
can read them directly via fetch() on GitHub Pages.

Usage:
    python scripts/precompute.py
"""

import json
import logging
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from blackswans.data.loaders import load_price_csv
from blackswans.data.transforms import compute_daily_returns
from blackswans.data.tickers import TICKER_REGISTRY, get_all_csvs
from blackswans.analysis.outliers import calculate_outlier_stats
from blackswans.analysis.scenarios import scenario_returns, annualised_return
from blackswans.analysis.regimes import moving_average_regime, regime_performance
from blackswans.analysis.periods import (
    PERIOD_LABELS,
    multi_index_summary,
    period_cagr_matrix,
    period_claim_summary,
)
from blackswans.validate_claims import run_full_validation

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "frontend" / "public" / "data"
SPLIT_DATE = "2011-01-01"

class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types and NaN/Infinity in JSON serialisation."""

    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _safe_float(v):
    """Convert to float, returning None for NaN/Inf."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _parse_dates_from_filename(filename: str):
    """Extract start and end dates from a data filename."""
    parts = filename.replace(".csv", "").split("_")
    return parts[-3], parts[-1]


def _required_ticker_map():
    """Return all expected tickers or fail before generating partial artifacts."""
    all_csvs = get_all_csvs(DATA_DIR)
    missing = sorted(set(TICKER_REGISTRY) - set(all_csvs))
    if missing:
        raise RuntimeError(f"Missing CSV data for expected tickers: {', '.join(missing)}")
    return {
        code: (sym, csv_path.name)
        for code, (sym, csv_path, _start, _end) in all_csvs.items()
    }


def generate_analysis(ticker_code, prices_df, prices, returns, start, end):
    """Generate analysis.json matching AnalysisResponse."""
    quantile_list = [0.99, 0.999]
    ma_window = 200

    outlier_stats = []
    for q in quantile_list:
        stats = calculate_outlier_stats(returns, q)
        outlier_stats.append({
            "quantile": stats.quantile,
            "threshold_low": _safe_float(stats.threshold_low),
            "threshold_high": _safe_float(stats.threshold_high),
            "count_low": int(stats.count_low),
            "count_high": int(stats.count_high),
            "mean_low": _safe_float(stats.mean_low),
            "mean_high": _safe_float(stats.mean_high),
            "median_low": _safe_float(stats.median_low),
            "median_high": _safe_float(stats.median_high),
            "std_low": _safe_float(stats.std_low),
            "std_high": _safe_float(stats.std_high),
            "min_low": _safe_float(stats.min_low),
            "max_high": _safe_float(stats.max_high),
        })

    full_ret, miss_best, miss_worst, miss_both = scenario_returns(returns, 10, 10)
    scenarios = [
        {"scenario": "all_days", "annualized_return": _safe_float(annualised_return(full_ret))},
        {"scenario": "miss_best_10", "annualized_return": _safe_float(annualised_return(miss_best))},
        {"scenario": "miss_worst_10", "annualized_return": _safe_float(annualised_return(miss_worst))},
        {"scenario": "miss_both_10", "annualized_return": _safe_float(annualised_return(miss_both))},
    ]

    regimes = moving_average_regime(prices, ma_window)
    regime_df = regime_performance(returns, regimes)
    regime_list = []
    for _, row in regime_df.iterrows():
        std_val = float(row["std"])
        sharpe = float(row["mean"] / row["std"] * np.sqrt(252)) if std_val > 0 else 0.0
        regime_list.append({
            "regime": row["regime"],
            "trading_days": int(row["count"]),
            "mean_return": _safe_float(row["mean"]),
            "std_return": _safe_float(row["std"]),
            "annualized_return": _safe_float(row["annualised_return"]),
            "sharpe_ratio": _safe_float(sharpe),
        })

    return {
        "ticker": ticker_code,
        "start_date": start,
        "end_date": end,
        "n_trading_days": len(returns),
        "outlier_stats": outlier_stats,
        "scenarios": scenarios,
        "regime_performance": regime_list,
    }


def generate_validation(ticker_code, symbol, prices_df, start, end):
    """Generate validation.json matching ValidationResponse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        summary = run_full_validation(
            csv_path="unused",
            ticker=symbol,
            start=start,
            end=end,
            output_dir=tmpdir,
            prices_df=prices_df,
        )

    claim_details = []
    for claim_num in range(1, 5):
        claim_key = f"claim{claim_num}"
        claim_data = summary["details"].get(claim_key, {})

        p_value = None
        if "jb_p_value" in claim_data:
            p_value = _safe_float(claim_data["jb_p_value"])
        elif "main_case_p_value" in claim_data:
            p_value = _safe_float(claim_data["main_case_p_value"])

        claim_details.append({
            "claim_name": claim_data.get("claim", f"Claim {claim_num}"),
            "verdict": claim_data.get("verdict", "UNKNOWN"),
            "p_value": p_value,
            "details": claim_data,
        })

    return {
        "ticker": ticker_code,
        "period": summary["period"],
        "n_trading_days": summary["n_trading_days"],
        "claims": summary["claims"],
        "claim_details": claim_details,
    }


def generate_chart_data(ticker_code, prices_df, prices, returns, start, end):
    """Generate chart-data.json matching ChartDataResponse."""
    ma_window = 200
    quantile = 0.99

    threshold_low = float(returns.quantile(1 - quantile))
    threshold_high = float(returns.quantile(quantile))

    regimes = moving_average_regime(prices, ma_window)

    # Downsample but preserve outliers
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
        data_points.append({
            "date": dt.strftime("%Y-%m-%d"),
            "ret": _safe_float(r),
            "is_outlier": is_outlier,
            "regime": regime_val,
        })

    # Histogram
    clean = returns.dropna()
    histogram = []
    if len(clean) > 1:
        mu = float(clean.mean() * 100)
        sigma = float(clean.std() * 100)
        if sigma > 0:
            counts, bin_edges = np.histogram(clean * 100, bins=80)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            bin_width = float(bin_edges[1] - bin_edges[0])
            normal_expected = [
                float(
                    len(clean) * bin_width
                    * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
                    / (sigma * np.sqrt(2 * np.pi))
                )
                for x in bin_centers
            ]
            histogram = [
                {
                    "bin_center": float(bc),
                    "count": int(c),
                    "normal_expected": float(ne),
                }
                for bc, c, ne in zip(bin_centers, counts, normal_expected)
            ]

    # Scenario impacts
    baseline_cagr = annualised_return(returns)
    scenario_impacts = {}
    for n_days in [5, 10, 20, 50]:
        _, miss_best, _, _ = scenario_returns(returns, n_days, n_days)
        impact = baseline_cagr - annualised_return(miss_best)
        scenario_impacts[str(n_days)] = _safe_float(impact * 100)

    return {
        "ticker": ticker_code,
        "start_date": start,
        "end_date": end,
        "n_trading_days": len(returns),
        "returns": data_points,
        "histogram": histogram,
        "scenario_impacts": scenario_impacts,
    }


def generate_period_comparison(ticker_code, prices, returns):
    """Generate period-comparison.json matching PeriodComparisonResponse."""
    raw = period_claim_summary(prices, returns, SPLIT_DATE)
    periods = []
    for key in ["pre", "post", "full"]:
        data = raw[key]
        period = {
            "period": key,
            "period_label": PERIOD_LABELS[key],
            "n_trading_days": data["n_trading_days"],
            "start_date": data["start_date"],
            "end_date": data["end_date"],
        }
        for claim in ["fat_tails", "outsized_influence", "clustering", "trend_following"]:
            claim_data = dict(data[claim])
            verdict = claim_data.pop("verdict")
            period[claim] = {"verdict": verdict, "metrics": claim_data}
        periods.append(period)
    return {
        "ticker": ticker_code,
        "split_date": SPLIT_DATE,
        "periods": periods,
    }


def generate_cagr_matrix(ticker_code, returns):
    """Generate cagr-matrix.json matching CagrMatrixResponse."""
    df = period_cagr_matrix(returns, SPLIT_DATE, n_days=10)
    return {
        "ticker": ticker_code,
        "split_date": SPLIT_DATE,
        "n_days": 10,
        "rows": df.to_dict(orient="records"),
    }


def main():
    """Generate all static JSON files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ticker_map = _required_ticker_map()
    tickers_list = []

    for ticker_code, (symbol, filename) in ticker_map.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing CSV for {ticker_code}: {csv_path}")

        start, end = _parse_dates_from_filename(filename)
        logger.info(f"Processing {ticker_code} ({symbol}): {start} to {end}")

        try:
            prices_df = load_price_csv(csv_path, start, end)
        except Exception as exc:
            raise RuntimeError(f"Failed to load CSV for {ticker_code} ({csv_path}): {exc}") from exc

        if prices_df.empty:
            raise ValueError(f"No price data in range for {ticker_code}: {csv_path}")

        prices = prices_df["Close"]
        returns = compute_daily_returns(prices)

        if len(returns.dropna()) < 50:
            raise ValueError(f"Too few returns for {ticker_code}: {len(returns.dropna())}")

        tickers_list.append({
            "ticker_code": ticker_code,
            "ticker_symbol": symbol,
            "start_date": start,
            "end_date": end,
        })

        ticker_dir = OUTPUT_DIR / ticker_code
        ticker_dir.mkdir(parents=True, exist_ok=True)

        # analysis.json
        logger.info(f"  Generating analysis.json for {ticker_code}")
        analysis = generate_analysis(ticker_code, prices_df, prices, returns, start, end)
        with open(ticker_dir / "analysis.json", "w") as f:
            json.dump(analysis, f, cls=NumpyEncoder)

        # validation.json
        logger.info(f"  Generating validation.json for {ticker_code}")
        validation = generate_validation(ticker_code, symbol, prices_df, start, end)
        with open(ticker_dir / "validation.json", "w") as f:
            json.dump(validation, f, cls=NumpyEncoder)

        # chart-data.json
        logger.info(f"  Generating chart-data.json for {ticker_code}")
        chart_data = generate_chart_data(ticker_code, prices_df, prices, returns, start, end)
        with open(ticker_dir / "chart-data.json", "w") as f:
            json.dump(chart_data, f, cls=NumpyEncoder)

        logger.info(f"  Generating period-comparison.json for {ticker_code}")
        period_comparison = generate_period_comparison(ticker_code, prices, returns)
        with open(ticker_dir / "period-comparison.json", "w") as f:
            json.dump(period_comparison, f, cls=NumpyEncoder)

        logger.info(f"  Generating cagr-matrix.json for {ticker_code}")
        cagr_matrix = generate_cagr_matrix(ticker_code, returns)
        with open(ticker_dir / "cagr-matrix.json", "w") as f:
            json.dump(cagr_matrix, f, cls=NumpyEncoder)

    # tickers.json
    with open(OUTPUT_DIR / "tickers.json", "w") as f:
        json.dump({"tickers": tickers_list}, f, cls=NumpyEncoder)

    logger.info("Generating multi-index.json")
    multi_index = {
        "split_date": SPLIT_DATE,
        "indices": multi_index_summary(str(DATA_DIR), split_date=SPLIT_DATE),
    }
    with open(OUTPUT_DIR / "multi-index.json", "w") as f:
        json.dump(multi_index, f, cls=NumpyEncoder)

    # Copy validation_status.json if it exists (generated by refresh_and_validate.py)
    status_src = DATA_DIR / "validation_status.json"
    if status_src.exists():
        import shutil
        shutil.copy2(status_src, OUTPUT_DIR / "validation_status.json")
        logger.info("  Copied validation_status.json to output")

    logger.info(f"Done. Generated data for {len(tickers_list)} tickers in {OUTPUT_DIR}")
    if len(tickers_list) != len(TICKER_REGISTRY):
        raise RuntimeError(
            f"Generated {len(tickers_list)} tickers, expected {len(TICKER_REGISTRY)}"
        )


if __name__ == "__main__":
    main()
