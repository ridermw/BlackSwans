"""Scenario analysis: missing best/worst days."""

from typing import Tuple

import numpy as np
import pandas as pd

CASH = 0.0


def annualised_return(returns: pd.Series) -> float:
    """Compute compound annual growth rate (CAGR) from daily returns."""
    if returns.empty:
        return float("nan")
    cumulative = (1 + returns).prod()
    years = len(returns) / 252
    return cumulative ** (1 / years) - 1 if years > 0 else float("nan")


def scenario_returns(
    returns: pd.Series,
    best_n: int,
    worst_n: int,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Simulate missing best/worst return days."""
    r = returns.copy()
    sorted_idx = r.sort_values()
    worst_idx = sorted_idx.index[:worst_n]
    best_idx = sorted_idx.index[-best_n:]
    miss_best = r.copy(); miss_best.loc[best_idx] = CASH
    miss_worst = r.copy(); miss_worst.loc[worst_idx] = CASH
    miss_both = r.copy(); miss_both.loc[best_idx.union(worst_idx)] = CASH
    return r, miss_best, miss_worst, miss_both
