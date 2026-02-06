"""Outlier identification and statistics."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class OutlierStats:
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


def calculate_outlier_stats(returns: pd.Series, quantile: float) -> OutlierStats:
    """Identify and compute statistics for extreme quantile return days."""
    low = returns.quantile(1 - quantile)
    high = returns.quantile(quantile)
    lows = returns[returns <= low]
    highs = returns[returns >= high]
    return OutlierStats(
        quantile, low, high,
        len(lows), len(highs),
        lows.mean(), highs.mean(),
        lows.median(), highs.median(),
        lows.std(ddof=0), highs.std(ddof=0),
        lows.min(), highs.max(),
    )
