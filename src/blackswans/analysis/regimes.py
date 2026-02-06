"""Market regime classification and analysis."""

from typing import Tuple

import numpy as np
import pandas as pd

from .scenarios import CASH, annualised_return


def moving_average_regime(prices: pd.Series, window: int) -> pd.Series:
    """Classify market regime by rolling moving average.

    Uses a lagged MA (shifted by 1 day) to avoid look-ahead bias:
    today's price is compared to yesterday's MA value.
    """
    if isinstance(prices, pd.DataFrame):
        series = prices['Close'] if 'Close' in prices.columns else prices.iloc[:, 0]
    else:
        series = prices

    series = pd.to_numeric(series, errors='coerce').dropna()
    sma = series.rolling(window).mean().shift(1)
    # Compare today's price to yesterday's MA to avoid look-ahead bias.
    regime = (series > sma).astype(int)
    regime.iloc[:window] = np.nan
    return regime


def outlier_regime_counts(
    returns: pd.Series,
    regimes: pd.Series,
    quantile: float
) -> Tuple[int, int]:
    """Count outliers occurring in each regime."""
    threshold_low = returns.quantile(1 - quantile)
    threshold_high = returns.quantile(quantile)
    outliers = returns[(returns <= threshold_low) | (returns >= threshold_high)]
    regs = regimes.loc[outliers.index]
    return int((regs == 0).sum()), int((regs == 1).sum())


def regime_performance(returns: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Summarize returns by market regime.

    The annualised return for each regime assumes cash (0% return) on
    days spent in the *other* regime, so the result is comparable to a
    buy-and-hold CAGR over the full period.
    """
    stats = []
    valid = regimes.dropna().index
    total_days = len(valid)
    for label, val in [("downtrend", 0), ("uptrend", 1)]:
        mask = regimes.loc[valid] == val
        r = returns.loc[valid][mask]
        # Build a full-length series: actual returns on regime days,
        # zero (cash) on all other days, then annualise over the total period.
        full = pd.Series(CASH, index=valid)
        full.loc[r.index] = r
        stats.append({
            "regime": label,
            "count": len(r),
            "pct_of_total": len(r) / total_days if total_days else np.nan,
            "mean": r.mean(),
            "median": r.median(),
            "std": r.std(ddof=0),
            "annualised_return": annualised_return(full),
        })
    return pd.DataFrame(stats)
