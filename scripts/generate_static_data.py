"""Generate static JSON data for GitHub Pages frontend.

Pre-computes all API responses as JSON files so the frontend works
without a live FastAPI server. Used during `vite build` for deployment.

Usage:
    python scripts/generate_static_data.py [--output-dir frontend/public/data]
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from blackswans.data.loaders import load_price_csv
from blackswans.data.transforms import compute_daily_returns
from blackswans.analysis.periods import (
    period_claim_summary,
    period_cagr_matrix,
    multi_index_summary,
    TICKER_MAP,
    PERIOD_LABELS,
)
from blackswans.analysis.outliers import calculate_outlier_stats
from blackswans.analysis.scenarios import scenario_returns, annualised_return
from blackswans.analysis.regimes import moving_average_regime, regime_performance
from blackswans.validate_claims import run_full_validation

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# API ticker codes matching api/main.py
API_TICKER_MAP = {
    "sp500": ("^GSPC", "_GSPC_1928-09-04_to_2025-01-31.csv"),
    "nikkei": ("^N225", "_N225_1970-01-05_to_2025-01-31.csv"),
    "ftse": ("^FTSE", "_FTSE_1984-01-03_to_2025-01-31.csv"),
    "dax": ("^GDAXI", "_GDAXI_1987-12-30_to_2025-01-31.csv"),
    "cac": ("^FCHI", "_FCHI_1990-03-01_to_2025-01-31.csv"),
    "asx": ("^AXJO", "_AXJO_1992-11-23_to_2025-01-31.csv"),
    "tsx": ("^GSPTSE", "_GSPTSE_1979-06-29_to_2025-01-31.csv"),
    "hsi": ("^HSI", "_HSI_1986-12-31_to_2025-01-28.csv"),
    "efa": ("EFA", "EFA_2001-08-27_to_2025-01-31.csv"),
    "eem": ("EEM", "EEM_2003-04-14_to_2025-01-31.csv"),
    "reit": ("VNQ", "VNQ_2004-09-29_to_2025-01-31.csv"),
    "bonds": ("AGG", "AGG_2003-09-29_to_2025-01-31.csv"),
}

SPLIT_DATE = "2011-01-01"


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp,)):
            return str(obj)
        return super().default(obj)


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=NumpyEncoder)
    logger.info(f"  → {path}")


def generate_tickers(output_dir):
    """Generate tickers.json."""
    tickers = []
    for code, (symbol, filename) in API_TICKER_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue
        parts = filename.replace(".csv", "").split("_")
        start_date = parts[-3] if len(parts) >= 4 else "unknown"
        end_date = parts[-1] if len(parts) >= 4 else "unknown"
        tickers.append({
            "ticker_code": code,
            "ticker_symbol": symbol,
            "data_file": str(filepath),
            "start_date": start_date,
            "end_date": end_date,
        })
    save_json({"tickers": tickers}, output_dir / "tickers.json")


def generate_period_comparison(ticker_code, prices, returns, output_dir):
    """Generate period-comparison JSON."""
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
            d = dict(data[claim])
            verdict = d.pop("verdict")
            period[claim] = {"verdict": verdict, "metrics": d}
        periods.append(period)

    save_json({
        "ticker": ticker_code,
        "split_date": SPLIT_DATE,
        "periods": periods,
    }, output_dir / ticker_code / "period-comparison.json")


def generate_cagr_matrix(ticker_code, returns, output_dir):
    """Generate cagr-matrix JSON for n_days=10."""
    df = period_cagr_matrix(returns, SPLIT_DATE, n_days=10)
    rows = df.to_dict(orient="records")
    save_json({
        "ticker": ticker_code,
        "split_date": SPLIT_DATE,
        "n_days": 10,
        "rows": rows,
    }, output_dir / ticker_code / "cagr-matrix.json")


def generate_multi_index(output_dir):
    """Generate multi-index.json."""
    results = multi_index_summary(str(DATA_DIR), split_date=SPLIT_DATE)
    save_json({
        "split_date": SPLIT_DATE,
        "indices": results,
    }, output_dir / "multi-index.json")


def main():
    parser = argparse.ArgumentParser(description="Generate static JSON for frontend")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="frontend/public/data",
        help="Output directory for JSON files",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    logger.info("Generating static data for GitHub Pages frontend...")

    # Tickers list
    logger.info("Generating tickers.json...")
    generate_tickers(output_dir)

    # Per-ticker data
    for ticker_code, (symbol, filename) in API_TICKER_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            logger.warning(f"Skipping {ticker_code}: {filepath} not found")
            continue

        logger.info(f"Processing {ticker_code} ({symbol})...")
        parts = filename.replace(".csv", "").split("_")
        start = parts[-3] if len(parts) >= 4 else "1900-01-01"
        end = parts[-1] if len(parts) >= 4 else "2099-12-31"

        prices_df = load_price_csv(filepath, start, end)
        prices = prices_df["Close"]
        returns = compute_daily_returns(prices)

        generate_period_comparison(ticker_code, prices, returns, output_dir)
        generate_cagr_matrix(ticker_code, returns, output_dir)

    # Multi-index
    logger.info("Generating multi-index.json...")
    generate_multi_index(output_dir)

    logger.info("Done! Static data generated.")


if __name__ == "__main__":
    main()
