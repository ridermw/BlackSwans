"""Split-period analysis for comparing pre/post Faber publication.

Wraps existing validate_claims functions to run analysis on time-sliced data,
enabling direct comparison of Faber's thesis across different market eras.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .scenarios import annualised_return, scenario_returns
from .outliers import calculate_outlier_stats
from .regimes import moving_average_regime, outlier_regime_counts, regime_performance
from .statistics import (
    normality_tests,
    excess_kurtosis,
    skewness,
    chi_square_regime_clustering,
    max_drawdown,
    sharpe_ratio,
    trend_following_backtest,
)
from ..data.loaders import load_price_csv
from ..data.transforms import compute_daily_returns
from ..data.tickers import get_periods_ticker_map

logger = logging.getLogger(__name__)

PERIOD_LABELS = {
    "pre": "Pre-Publication (Original Era)",
    "post": "Post-Publication (Modern Era)",
    "full": "Full Period",
}

# Dynamic ticker map built from the shared registry + on-disk CSVs.
# Lazy-initialised on first access via get_periods_ticker_map().
TICKER_MAP = get_periods_ticker_map()


def split_returns_by_date(
    returns: pd.Series, split_date: str = "2011-01-01"
) -> Dict[str, pd.Series]:
    """Split a returns series into pre/post periods and full.

    Parameters
    ----------
    returns : pd.Series
        Daily returns with DatetimeIndex.
    split_date : str
        ISO date string for the split point.

    Returns
    -------
    dict with keys 'pre', 'post', 'full', each a pd.Series.
    """
    ts = pd.Timestamp(split_date)
    return {
        "pre": returns[returns.index < ts],
        "post": returns[returns.index >= ts],
        "full": returns,
    }


def period_cagr_matrix(
    returns: pd.Series,
    split_date: str = "2011-01-01",
    n_days: int = 10,
) -> pd.DataFrame:
    """CAGR scenario analysis across pre/post/full periods.

    For each period, computes CAGR for: all days, miss best N, miss worst N.

    Returns DataFrame with columns:
        period, n_trading_days, cagr_all, cagr_miss_best, cagr_miss_worst,
        cagr_miss_both, impact_miss_best, impact_miss_worst, impact_miss_both
    """
    periods = split_returns_by_date(returns, split_date)
    rows = []
    for key in ["pre", "post", "full"]:
        r = periods[key]
        if len(r) < n_days * 2:
            continue
        cagr_all = annualised_return(r)
        _, miss_best, miss_worst, miss_both = scenario_returns(r, n_days, n_days)
        cagr_mb = annualised_return(miss_best)
        cagr_mw = annualised_return(miss_worst)
        cagr_mboth = annualised_return(miss_both)
        rows.append({
            "period": key,
            "period_label": PERIOD_LABELS[key],
            "n_trading_days": len(r),
            "start_date": str(r.index.min().date()),
            "end_date": str(r.index.max().date()),
            "n_days_removed": n_days,
            "cagr_all": cagr_all,
            "cagr_miss_best": cagr_mb,
            "cagr_miss_worst": cagr_mw,
            "cagr_miss_both": cagr_mboth,
            "impact_miss_best": cagr_all - cagr_mb,
            "impact_miss_worst": cagr_mw - cagr_all,
            "impact_miss_both": cagr_all - cagr_mboth,
        })
    return pd.DataFrame(rows)


def _claim_summary_for_period(
    returns: pd.Series, prices: pd.Series
) -> dict:
    """Run lightweight claim checks on a single period's data.

    Returns dict with fat_tails, outsized_influence, clustering,
    trend_following sub-dicts plus metadata.
    """
    n = len(returns)
    result = {
        "n_trading_days": n,
        "start_date": str(returns.index.min().date()),
        "end_date": str(returns.index.max().date()),
    }

    # Claim 1: Fat tails
    kurt = excess_kurtosis(returns)
    skew_val = skewness(returns)
    norm = normality_tests(returns)
    result["fat_tails"] = {
        "excess_kurtosis": float(kurt),
        "skewness": float(skew_val),
        "jb_p_value": float(norm["jb"].p_value),
        "verdict": "CONFIRMED" if kurt > 0 and norm["jb"].p_value < 0.05 else "NOT CONFIRMED",
    }

    # Claim 2: Outsized influence (use N=10)
    if n >= 20:
        cagr_all = annualised_return(returns)
        _, mb, mw, mboth = scenario_returns(returns, 10, 10)
        cagr_mb = annualised_return(mb)
        cagr_mw = annualised_return(mw)
        cagr_mboth = annualised_return(mboth)
        impact = cagr_all - cagr_mb
        result["outsized_influence"] = {
            "cagr_all": float(cagr_all),
            "cagr_miss_best_10": float(cagr_mb),
            "cagr_miss_worst_10": float(cagr_mw),
            "cagr_miss_both_10": float(cagr_mboth),
            "impact_miss_best_10": float(impact),
            "impact_miss_both_10": float(cagr_all - cagr_mboth),
            "verdict": "CONFIRMED" if abs(impact) > 0.005 else "NOT CONFIRMED",
        }
    else:
        result["outsized_influence"] = {"verdict": "INSUFFICIENT DATA"}

    # Claim 3: Clustering
    if n >= 200:
        regimes = moving_average_regime(prices, 200)
        valid = regimes.dropna()
        total_down = int((valid == 0).sum())
        total_up = int((valid == 1).sum())
        down, up = outlier_regime_counts(returns, regimes, 0.99)
        total_outliers = down + up
        pct_down = down / total_outliers * 100 if total_outliers > 0 else 0
        chi2 = chi_square_regime_clustering(down, up, total_down, total_up)
        result["clustering"] = {
            "outliers_in_downtrend": down,
            "outliers_in_uptrend": up,
            "pct_in_downtrend": float(pct_down),
            "chi2_p_value": float(chi2.p_value),
            "verdict": "CONFIRMED" if chi2.p_value < 0.05 else "NOT CONFIRMED",
        }
    else:
        result["clustering"] = {"verdict": "INSUFFICIENT DATA"}

    # Claim 4: Trend following
    if n >= 200:
        bt = trend_following_backtest(prices, returns, 200)
        bh = bt["buy_hold_return"]
        st = bt["strategy_return"]
        bh_dd = max_drawdown(bh)
        st_dd = max_drawdown(st)
        result["trend_following"] = {
            "buy_hold_cagr": float(annualised_return(bh)),
            "strategy_cagr": float(annualised_return(st)),
            "buy_hold_max_drawdown": float(bh_dd),
            "strategy_max_drawdown": float(st_dd),
            "buy_hold_sharpe": float(sharpe_ratio(bh)),
            "strategy_sharpe": float(sharpe_ratio(st)),
            "verdict": "CONFIRMED" if st_dd > bh_dd else "NOT CONFIRMED",
        }
    else:
        result["trend_following"] = {"verdict": "INSUFFICIENT DATA"}

    return result


def period_claim_summary(
    prices: pd.Series,
    returns: pd.Series,
    split_date: str = "2011-01-01",
) -> Dict[str, dict]:
    """Run claim validation for pre/post/full periods.

    Parameters
    ----------
    prices : pd.Series
        Price series with DatetimeIndex.
    returns : pd.Series
        Daily returns with DatetimeIndex.
    split_date : str
        ISO date string for the split point.

    Returns
    -------
    dict with keys 'pre', 'post', 'full', each containing claim results.
    """
    ts = pd.Timestamp(split_date)
    periods_r = split_returns_by_date(returns, split_date)

    # Split prices to match
    periods_p = {
        "pre": prices[prices.index < ts],
        "post": prices[prices.index >= ts],
        "full": prices,
    }

    result = {}
    for key in ["pre", "post", "full"]:
        logger.info(f"Analyzing {PERIOD_LABELS[key]}...")
        result[key] = _claim_summary_for_period(periods_r[key], periods_p[key])
    return result


def multi_index_summary(
    data_dir: str,
    ticker_map: Optional[Dict] = None,
    split_date: str = "2011-01-01",
) -> List[dict]:
    """Run split-period CAGR and claim analysis across multiple indices.

    Parameters
    ----------
    data_dir : str
        Directory containing CSV files.
    ticker_map : dict, optional
        Mapping of ticker keys to {file, start, end}. Defaults to TICKER_MAP.
    split_date : str
        ISO date string for the split point.

    Returns
    -------
    list of dicts, one per ticker, with CAGR and claim verdicts per period.
    """
    if ticker_map is None:
        ticker_map = TICKER_MAP

    data_path = Path(data_dir)
    results = []

    for ticker_key, info in ticker_map.items():
        csv_path = data_path / info["file"]
        if not csv_path.exists():
            logger.warning(f"CSV not found for {ticker_key}: {csv_path}")
            continue

        try:
            start = info.get("start", "1900-01-01")
            end = info.get("end", "2099-12-31")
            prices_df = load_price_csv(csv_path, start, end)
            prices = prices_df["Close"]
            returns = compute_daily_returns(prices)

            # CAGR by period
            ts = pd.Timestamp(split_date)
            r_pre = returns[returns.index < ts]
            r_post = returns[returns.index >= ts]

            cagr_full = float(annualised_return(returns))
            cagr_pre = float(annualised_return(r_pre)) if len(r_pre) > 0 else None
            cagr_post = float(annualised_return(r_post)) if len(r_post) > 0 else None

            # Key metrics
            kurt_full = float(excess_kurtosis(returns))

            # Clustering for full period (need 200+ days)
            clustering_pct = None
            if len(returns) >= 200:
                regimes = moving_average_regime(prices, 200)
                down, up = outlier_regime_counts(returns, regimes, 0.99)
                total = down + up
                clustering_pct = float(down / total * 100) if total > 0 else None

            # Trend-following drawdown for full period
            tf_drawdown = None
            bh_drawdown = None
            if len(returns) >= 200:
                bt = trend_following_backtest(prices, returns, 200)
                tf_drawdown = float(max_drawdown(bt["strategy_return"]))
                bh_drawdown = float(max_drawdown(bt["buy_hold_return"]))

            name = info.get("name", ticker_key)

            results.append({
                "ticker": ticker_key,
                "name": name,
                "n_trading_days": len(returns),
                "start_date": str(returns.index.min().date()),
                "end_date": str(returns.index.max().date()),
                "cagr_full": cagr_full,
                "cagr_pre": cagr_pre,
                "cagr_post": cagr_post,
                "kurtosis_full": kurt_full,
                "clustering_pct_full": clustering_pct,
                "tf_max_drawdown": tf_drawdown,
                "bh_max_drawdown": bh_drawdown,
            })
        except Exception as e:
            logger.error(f"Error processing {ticker_key}: {e}")
            continue

    return results
